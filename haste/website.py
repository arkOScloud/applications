import json
import nginx
import os

from arkos.languages import nodejs
from arkos.websites import Site
from arkos.system import users, services
from arkos.tracked_services import get_open_port


class Haste(Site):
    def pre_install(self, vars_):
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

    def post_install(self, vars_, dbpasswd=""):
        with open(os.path.join(self.path, 'config.js'), 'r') as f:
            d = json.loads(f.read())
        d["port"] = self.backend_port
        if d["storage"]["type"] == "redis":
            d["storage"]["type"] = "file"
            d["storage"]["path"] = "./data"
            if "host" in d["storage"]:
                del d["storage"]["host"]
            if "port" in d["storage"]:
                del d["storage"]["port"]
            if "db" in d["storage"]:
                del d["storage"]["db"]
            if "expire" in d["storage"]:
                del d["storage"]["expire"]
        with open(os.path.join(self.path, 'config.js'), 'w') as f:
            f.write(json.dumps(d, sort_keys=True,
                               indent=4, separators=(',', ': ')))

        nodejs.install_from_package(self.path)
        users.SystemUser("haste").add()

        # Finally, make sure that permissions are set so that Haste
        # can save its files properly.
        uid = users.get_system("haste").uid
        if not os.path.exists(os.path.join(self.path, 'data')):
            os.mkdir(os.path.join(self.path, 'data'))
        for r, d, f in os.walk(self.path):
            for x in d:
                os.chown(os.path.join(r, x), uid, -1)
            for x in f:
                os.chown(os.path.join(r, x), uid, -1)
        cfg = {
                'directory': self.path,
                'user': 'haste',
                'command': 'node {0}'
                .format(os.path.join(self.path, 'server.js')),
                'autostart': 'true',
                'autorestart': 'true',
                'environment': 'NODE_ENV="production"',
                'stdout_logfile': '/var/log/haste.log',
                'stderr_logfile': '/var/log/haste.log'
            }
        s = services.Service(self.id, "supervisor", cfg=cfg)
        s.add()

    def pre_remove(self):
        pass

    def post_remove(self):
        services.get(self.id).remove()

    def enable_ssl(self, cfile, kfile):
        n = nginx.loadf('/etc/nginx/sites-available/{0}'.format(self.id))
        for x in n.servers:
            if x.filter('Location', '/'):
                x.remove(x.filter('Location', '/')[0])
                self.addtoblock[0].add(
                    nginx.Key('proxy_set_header',
                              'X-Forwarded-For $proxy_add_x_forwarded_for'),
                    nginx.Key('proxy_set_header', 'X-Forwarded-Proto $scheme'),
                )
                x.add(self.addtoblock[0])
                nginx.dumpf(n, '/etc/nginx/sites-available/{0}'
                            .format(self.id))

    def disable_ssl(self):
        n = nginx.loadf('/etc/nginx/sites-available/{0}'.format(self.id))
        for x in n.servers:
            if x.filter('Location', '/'):
                x.remove(x.filter('Location', '/')[0])
                x.add(self.addtoblock[0])
                nginx.dumpf(n, '/etc/nginx/sites-available/{0}'
                            .format(self.id))

    def update(self, pkg, ver):
        # TODO: pull from Git at appropriate intervals
        pass
