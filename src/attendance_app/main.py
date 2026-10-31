"""Windows desktop entry point: python -m attendance_app.main."""
import sys


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("این برنامه فقط در ویندوز اجرا می‌شود.")
    from attendance_app.bootstrap import create_application

    from attendance_app.domain.errors import AppError
    try:
        app, window = create_application(sys.argv)
    except AppError as error:
        from PySide6.QtWidgets import QApplication, QMessageBox
        error_app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "خطای راه‌اندازی", str(error))
        return 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
