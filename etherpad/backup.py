import os

from arkos.system import services, users
from arkos.backup import BackupController


class EtherpadBackup(BackupController):
    def get_config(self, site):
        return ["/etc/supervisor.d/%s.ini" % site.name]
    
    def get_data(self, site):
        pass
    
    def pre_backup(self, site):
        pass
    
    def post_backup(self, site):
        pass
    
    def pre_restore(self, site):
        pass
    
    def post_restore(self, site):
        users.SystemUser("etherpad").add()
        # node-gyp needs the HOME variable to be set
        with open(os.path.join(site.path, 'bin/installDeps.sh')) as f:
            run_script = f.readlines()
        # this is a hack. supervisor does not kill node when stopping ep.
        run_script.insert(1, 'killall node\n')
        run_script.insert(1, 'export HOME=%s\n' % site.path)
        with open(os.path.join(site.path, 'bin/installDeps.sh'), 'w') as f:
            f.writelines(run_script)
        uid = users.get_system("etherpad").uid
        for r, d, f in os.walk(site.path):
            for x in d:
                os.chown(os.path.join(root, x), uid, -1)
            for x in f:
                os.chown(os.path.join(root, x), uid, -1)
        services.get(site.name).enable()
