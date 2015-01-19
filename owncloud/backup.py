import os

from arkos.backup import BackupController


class ownCloudBackup(BackupController):
    def get_config(self, site):
        return []
    
    def get_data(self, site):
        datadir = None
        if os.path.exists(os.path.join(site.path, 'config', 'config.php')):
            with open(os.path.join(site.path, 'config', 'config.php'), 'r') as f:
                for line in f.readlines():
                    if 'datadirectory' in line:
                        data = line.split("'")[1::2]
                        datadir = data[1]
        if datadir:
            return [datadir]
    
    def pre_backup(self, site):
        pass
    
    def post_backup(self, site):
        pass
    
    def pre_restore(self, site):
        pass
    
    def post_restore(self, site, dbpasswd):
        with open(os.path.join(site.path, 'config', 'config.php'), 'r') as f:
            data = f.readlines()
        for x in enumerate(data):
            if "dbpass" in x[1]:
                data[0] = '   "dbpass" => "'+dbpasswd+'",'
        with open(os.path.join(site.path, 'config', 'config.php'), 'w') as f:
            f.writelines(data)
