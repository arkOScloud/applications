import os

from arkos.languages import nodejs
from arkos.system import services, users
from arkos.backup import BackupController


class GhostBackup(BackupController):
    def get_config(self, site):
        return ["/etc/supervisor.d/{0}.ini".format(site.id)]

    def get_data(self, site):
        return []

    def pre_backup(self, site):
        pass

    def post_backup(self, site):
        pass

    def pre_restore(self):
        pass

    def post_restore(self, site, dbpasswd):
        nodejs.install_from_package(site.path,
                                    'production',
                                    {'sqlite': '/usr/bin/sqlite3',
                                     'python': '/usr/bin/python2'})
        users.SystemUser("ghost").add()
        uid = users.get_system("ghost").uid
        for r, d, f in os.walk(site.path):
            for x in d:
                os.chown(os.path.join(r, x), uid, -1)
            for x in f:
                os.chown(os.path.join(r, x), uid, -1)
        s = services.get(site.id)
        if s:
            s.remove()
        cfg = {
                'directory': site.path,
                'user': 'ghost',
                'command': 'node {0}'
                .format(os.path.join(site.path, 'index.js')),
                'autostart': 'true',
                'autorestart': 'true',
                'environment': 'NODE_ENV="production"',
                'stdout_logfile': '/var/log/ghost.log',
                'stderr_logfile': '/var/log/ghost.log'
            }
        s = services.Service(site.id, "supervisor", cfg=cfg)
        s.add()
