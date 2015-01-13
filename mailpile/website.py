import nginx
import os

from arkos.websites import Site
from arkos.system import users


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
        for r, d, f in os.walk(self.path):
            for x in d:
                os.chmod(os.path.join(root, x), 0755)
            for x in f:
                os.chmod(os.path.join(root, x), 0644)

        cfg = {
                'directory': self.path,
                'user': 'mailpile',
                'command': 'mp --www= --wait',
                'autostart': 'true',
                'autorestart': 'false',
                'stdout_logfile': '/var/log/mailpile.log',
                'stderr_logfile': '/var/log/mailpile.log'
            }
        s = services.Service(self.name, "supervisor", cfg=cfg)
        s.add()
    
    def pre_remove(self):
        pass

    def post_remove(self):
        services.get(self.name).remove()
    
    def ssl_enable(self, cfile, kfile):
        pass
    
    def ssl_disable(self):
        pass
    
    def update(self, pkg, ver):
        pass
