import os

from arkos.backup import BackupController


class PaperworkBackup(BackupController):
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
        dbstr = "mysql, localhost, 3389, {0}, {1}, {0}"\
            .format(site.id, dbpasswd)
        with open(os.path.join(site.path,
                               'app/storage/db_settings'), 'w') as f:
            f.write(dbstr)
