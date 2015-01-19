import os

from arkos.languages import nodejs
from arkos.system import services, users
from arkos.backup import BackupController


class HasteBackup(BackupController):
    def get_config(self, site):
        return ["/etc/supervisor.d/%s.ini" % site.name]
    
    def get_data(self, site):
        return []
    
    def pre_backup(self, site):
        pass
    
    def post_backup(self, site):
        pass
    
    def pre_restore(self, site):
        pass
    
    def post_restore(self, site, dbpasswd):
        nodejs.install_from_package(site.path)
        users.SystemUser("haste").add()
        uid = users.get_system("haste").uid
        for r, d, f in os.walk(site.path):
            for x in d:
                os.chown(os.path.join(root, x), uid, -1)
            for x in f:
                os.chown(os.path.join(root, x), uid, -1)
        services.get(site.name).enable()
