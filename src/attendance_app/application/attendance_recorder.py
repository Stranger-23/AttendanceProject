"""Bounded, coalescing background writer. Frames never wait for SQLite writes."""
import logging
from queue import Queue, Full
from threading import Lock, Thread
from time import monotonic


class AttendanceRecorder:
    def __init__(self, service, notify, *, capacity=256, retry_seconds=3, clock=monotonic):
        self.service, self.notify = service, notify
        self.retry_seconds, self.clock = retry_seconds, clock
        self.queue = Queue(maxsize=capacity)
        self.lock = Lock()
        self.pending, self.completed, self.retry_after = set(), set(), {}
        self.closed = False
        self.last_queue_warning = float('-inf')
        self.thread = Thread(target=self._run, name='attendance-writer')
        self.thread.start()

    def submit(self, results, observed_at):
        day = observed_at.date().isoformat()
        overflow = False
        with self.lock:
            # Retain current-day cache plus any work still pending across midnight.
            self.completed = {key for key in self.completed if key[1] == day}
            self.retry_after = {key: value for key, value in self.retry_after.items() if key[1] == day}
            for result in results:
                if result.state != 'known' or result.person_id is None or self.closed:
                    continue
                key = (result.person_id, day)
                if key in self.pending or key in self.completed or self.clock() < self.retry_after.get(key, 0):
                    continue
                try:
                    self.queue.put_nowait((key, result, observed_at))
                    self.pending.add(key)
                except Full:
                    overflow = True
            warn = overflow and self.clock() - self.last_queue_warning >= self.retry_seconds
            if warn:
                self.last_queue_warning = self.clock()
        if warn:
            logging.getLogger('attendance_app.attendance').warning('Attendance queue is full')
            self.notify('صف ثبت حضور پر است؛ ثبت این چهره‌ها هنوز انجام نشده است. روبه‌روی دوربین بمانید.')

    def _run(self):
        logger = logging.getLogger('attendance_app.attendance')
        while True:
            task = self.queue.get()
            if task is None:
                self.queue.task_done()
                return
            key, result, observed_at = task
            try:
                receipt = self.service.record(result, observed_at)
            except Exception as error:
                # Do not log identities or biometric data, or send tracebacks to UI.
                logger.error('Attendance transaction failed: %s', type(error).__name__)
                with self.lock:
                    self.pending.discard(key)
                    self.retry_after[key] = self.clock() + self.retry_seconds
                self.notify('ثبت حضور انجام نشد؛ دسترسی به پایگاه داده و فعال بودن فرد را بررسی کنید. تشخیص چهره ادامه دارد.')
            else:
                with self.lock:
                    self.pending.discard(key)
                    if receipt is not None:
                        self.completed.add(key)
                        self.retry_after.pop(key, None)
                if receipt is not None:
                    name = result.person_name or 'فرد شناسایی‌شده'
                    if receipt.created:
                        self.notify(f'حضور {name} در ساعت {receipt.attendance_time[:8]} ثبت شد.')
                    else:
                        self.notify(f'حضور {name} برای امروز قبلاً ثبت شده است.')
            finally:
                self.queue.task_done()

    def close(self):
        with self.lock:
            self.closed = True
        # Called by the recognition thread after releasing the camera, never by UI.
        # Drain accepted observations before allowing the dialog/application to close.
        self.queue.put(None)
        self.thread.join()
