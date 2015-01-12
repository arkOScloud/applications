import json
import nginx
import os

from arkos.utilities import shell
from arkos.languages import nodejs
from arkos.websites import Site
from arkos.system import users, services
from arkos.tracked_services import get_open_port


class Haste(Site):
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
        with open(os.path.join(self.path, 'config.js'), 'r') as f:
            d = json.loads(f.read())
        if d["storage"]["type"] == "redis":
            d["storage"]["type"] = "file"
            d["storage"]["path"] = "./data"
            if d["storage"].has_key("host"):
                del d["storage"]["host"]
            if d["storage"].has_key("port"):
                del d["storage"]["port"]
            if d["storage"].has_key("db"):
                del d["storage"]["db"]
            if d["storage"].has_key("expire"):
                del d["storage"]["expire"]
            with open(os.path.join(self.path, 'config.js'), 'w') as f:
                f.write(json.dumps(d))

        nodejs.install_from_package(self.path)
        users.SystemUser("haste").add()

        # Finally, make sure that permissions are set so that Haste
        # can save its files properly.
        uid = users.get_system("haste").uid
        for r, d, f in os.walk(self.path):
            for x in d:
                os.chown(os.path.join(root, x), uid, -1)
            for x in f:
                os.chown(os.path.join(root, x), uid, -1)
        
        with open(os.path.join(self.path, "config.js"), "r") as f:
            data = f.read()
        data = data.replace('"port": 7777,', '"port": %s,' % self.backend_port)
        with open(os.path.join(self.path, "config.js"), "w") as f:
            f.write(data)
        
        cfg = {
                'stype': 'program',
                'directory': self.path,
                'user': 'haste',
                'command': 'node %s'%os.path.join(self.path, 'server.js'),
                'autostart': 'true',
                'autorestart': 'true',
                'environment': 'NODE_ENV="production"',
                'stdout_logfile': '/var/log/%s.log' % self.name,
                'stderr_logfile': '/var/log/%s.log' % self.name
            }
        s = services.Service(self.name, cfg=cfg)
        s.add()
        s.enable()

    def pre_remove(self):
        pass

    def post_remove(self):
        services.get(self.name).remove()

    def ssl_enable(self, cfile, kfile):
        n = nginx.loadf('/etc/nginx/sites-available/%s'%self.name)
        for x in n.servers:
            if x.filter('Location', '/'):
                x.remove(x.filter('Location', '/')[0])
                self.addtoblock[0].add(
                    nginx.Key('proxy_set_header', 'X-Forwarded-For $proxy_add_x_forwarded_for'),
                    nginx.Key('proxy_set_header', 'X-Forwarded-Proto $scheme'),
                )
                x.add(self.addtoblock[0])
                nginx.dumpf(n, '/etc/nginx/sites-available/%s'%self.name)

    def ssl_disable(self):
        n = nginx.loadf('/etc/nginx/sites-available/%s'%self.name)
        for x in n.servers:
            if x.filter('Location', '/'):
                x.remove(x.filter('Location', '/')[0])
                x.add(self.addtoblock[0])
                nginx.dumpf(n, '/etc/nginx/sites-available/%s'%self.name)

    def update(self, pkg, ver):
        # TODO: pull from Git at appropriate intervals
        pass
