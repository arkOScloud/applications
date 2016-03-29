import os

from arkos.backup import BackupController


class GravBackup(BackupController):
    def get_config(self, site):
        return []

    def get_data(self, site):
        return []

    def pre_backup(self, site):
        pass

    def post_backup(self, site):
        pass

    def pre_restore(self):
        pass

    def post_restore(self, site, dbpasswd):
        pass
