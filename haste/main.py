import json
import nginx
import os

from arkos.core.utilities import shell
from arkos.core.languages import nodejs
from arkos.core.sites import SiteEngine


class Haste(SiteEngine):
    addtoblock = [
        nginx.Location('/',
            nginx.Key('proxy_pass', 'http://127.0.0.1:7777'),
            nginx.Key('proxy_set_header', 'X-Real-IP $remote_addr'),
            nginx.Key('proxy_set_header', 'Host $host'),
            nginx.Key('proxy_buffering', 'off')
            )
        ]

    def pre_install(self, name, vars):
        pass

    def post_install(self, name, path, vars, dbinfo={}):
        with open(os.path.join(path, 'config.js'), 'r') as f:
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
            with open(os.path.join(path, 'config.js'), 'w') as f:
                f.write(json.dumps(d))

        nodejs.install_from_package(path)
        self.System.Users.add("haste")
        self.System.Services.edit(name,
            {
                'stype': 'program',
                'directory': path,
                'user': 'haste',
                'command': 'node %s'%os.path.join(path, 'server.js'),
                'autostart': 'true',
                'autorestart': 'true',
                'environment': 'NODE_ENV="production"',
                'stdout_logfile': '/var/log/%s.log' % name,
                'stderr_logfile': '/var/log/%s.log' % name
            }
        )
        self.System.Services.enable(name, 'supervisor')

        # Finally, make sure that permissions are set so that Haste
        # can save its files properly.
        uid = self.System.Users.get("haste")["uid"]
        for r, d, f in os.walk(path):
            for x in d:
                os.chown(os.path.join(root, x), uid, -1)
            for x in f:
                os.chown(os.path.join(root, x), uid, -1)

    def pre_remove(self, site):
        pass

    def post_remove(self, site):
        self.System.Services.remove(site["name"])

    def ssl_enable(self, path, cfile, kfile):
        name = os.path.basename(path)
        n = nginx.loadf('/etc/nginx/sites-available/%s'%name)
        for x in n.servers:
            if x.filter('Location', '/'):
                x.remove(x.filter('Location', '/')[0])
                self.addtoblock[0].add(
                    nginx.Key('proxy_set_header', 'X-Forwarded-For $proxy_add_x_forwarded_for'),
                    nginx.Key('proxy_set_header', 'X-Forwarded-Proto $scheme'),
                )
                x.add(self.addtoblock[0])
                nginx.dumpf(n, '/etc/nginx/sites-available/%s'%name)

    def ssl_disable(self, path):
        name = os.path.basename(path)
        n = nginx.loadf('/etc/nginx/sites-available/%s'%name)
        for x in n.servers:
            if x.filter('Location', '/'):
                x.remove(x.filter('Location', '/')[0])
                x.add(self.addtoblock[0])
                nginx.dumpf(n, '/etc/nginx/sites-available/%s'%name)

    def update(self, path, pkg, ver):
        # TODO: pull from Git at appropriate intervals
        pass
