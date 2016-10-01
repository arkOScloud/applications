import nginx
import os

from arkos.websites import Site
from arkos.system import users, services
from arkos.tracked_services import get_open_port


class Mailpile(Site):
    def pre_install(self, extra_vars):
        self.backend_port = str(get_open_port())
        self.addtoblock = [
            nginx.Location(
                '/',
                nginx.Key('proxy_pass', 'http://127.0.0.1:{0}'
                          .format(self.backend_port)),
                nginx.Key('proxy_set_header', 'X-Real-IP $remote_addr'),
                nginx.Key('proxy_set_header', 'Host $host'),
                nginx.Key('proxy_buffering', 'off')
            )]

    def post_install(self, extra_vars, dbpasswd=""):
        users.SystemUser("mailpile").add()

        st = os.stat(os.path.join(self.path, 'scripts/mailpile'))
        os.chmod(
            os.path.join(self.path, 'scripts/mailpile'), st.st_mode | 0o111
        )
        cfg = {
            'directory': self.path,
            'user': 'mailpile',
            'command': '{0} --www=0.0.0.0:{1} --wait'
            .format(os.path.join(self.path, 'mp'), self.backend_port),
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
