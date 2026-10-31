"""Local backup/restore use cases; widgets never access SQLite."""
class StorageService:
    def __init__(self, backup_manager):
        self.backup_manager = backup_manager

    def backup(self, destination, *, overwrite=False):
        self.backup_manager.backup(destination, overwrite=overwrite)

    def restore(self, source, *, confirmed=False):
        return self.backup_manager.restore(source, confirmed=confirmed)
