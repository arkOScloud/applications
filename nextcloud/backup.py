import os

from arkos.backup import BackupController


class NextcloudBackup(BackupController):
    def get_config(self, site):
        return []

    def get_data(self, site):
        datadir = None
        config_file = os.path.join(site.path, 'config', 'config.php')
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
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

    def pre_restore(self):
        pass

    def post_restore(self, site, dbpasswd):
        config_file = os.path.join(site.path, 'config', 'config.php')
        with open(config_file, 'r') as f:
            data = f.readlines()
        for x in enumerate(data):
            if "dbpass" in x[1]:
                data[0] = '   "dbpass" => "{0}",'.format(dbpasswd)
        with open(config_file, 'w') as f:
            f.writelines(data)
