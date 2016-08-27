import os

from arkos.system import services, users
from arkos.backup import BackupController


class MailpileBackup(BackupController):
    def get_config(self, site):
        return ["/etc/supervisor.d/{0}.ini".format(site.name)]

    def get_data(self, site):
        return ["/root/.local/share/Mailpile"]

    def pre_backup(self, site):
        pass

    def post_backup(self, site):
        pass

    def pre_restore(self):
        pass

    def post_restore(self, site, dbpasswd):
        users.SystemUser("mailpile").add()
        for _, d, f in os.walk(site.path):
            for x in d:
                os.chmod(os.path.join(root, x), 0o755)
            for x in f:
                os.chmod(os.path.join(root, x), 0o644)
        services.get(site.name).enable()
