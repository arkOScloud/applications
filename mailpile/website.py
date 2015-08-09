import nginx
import os
import stat

from arkos.websites import Site
from arkos.system import users, services
from arkos.tracked_services import get_open_port


class Mailpile(Site):
    def pre_install(self, vars):
        self.backend_port = str(get_open_port())
        self.addtoblock = [
            nginx.Location('/',
                nginx.Key('proxy_pass', 'http://127.0.0.1:%s' % self.backend_port),
                nginx.Key('proxy_set_header', 'X-Real-IP $remote_addr'),
                nginx.Key('proxy_set_header', 'Host $host'),
                nginx.Key('proxy_buffering', 'off')
                )
            ]

    def post_install(self, vars, dbpasswd=""):
        users.SystemUser("mailpile").add()

        st = os.stat(os.path.join(self.path, 'mp'))
        os.chmod(os.path.join(self.path, 'mp'), st.st_mode | stat.S_IEXEC)
        cfg = {
            'directory': self.path,
            'user': 'mailpile',
            'command': '%s --www=0.0.0.0:%s --wait' % (os.path.join(self.path, 'mp'), self.backend_port),
            'autostart': 'true',
            'autorestart': 'false',
            'stdout_logfile': '/var/log/mailpile.log',
            'stderr_logfile': '/var/log/mailpile.log'
        }
        s = services.Service(self.id, "supervisor", cfg=cfg)
        s.add()

    def pre_remove(self):
        pass

    def post_remove(self):
        services.get(self.id).remove()

    def enable_ssl(self, cfile, kfile):
        pass

    def disable_ssl(self):
        pass

    def update(self, pkg, ver):
        pass
