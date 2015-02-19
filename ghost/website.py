import json
import nginx
import os

from arkos.utilities import shell
from arkos.languages import nodejs
from arkos.websites import Site
from arkos.system import users, services
from arkos.tracked_services import get_open_port


class Ghost(Site):
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
        with open(os.path.join(self.path, 'package.json'), 'r') as f:
            d = json.loads(f.read())
        del d['dependencies']['bcryptjs']
        d['dependencies']['bcrypt'] = '0.8.1'
        with open(os.path.join(self.path, 'package.json'), 'w') as f:
            f.write(json.dumps(d))
        with open(os.path.join(self.path, 'core/server/models/user.js'), 'r') as f:
            d = f.read()
        d = d.replace('bcryptjs', 'bcrypt')
        with open(os.path.join(self.path, 'core/server/models/user.js'), 'w') as f:
            f.write(d)

        nodejs.install_from_package(self.path, 'production', {'sqlite': '/usr/bin/sqlite3', 'python': '/usr/bin/python2'})
        users.SystemUser("ghost").add()

        # Get Mail settings
        mail_settings = {
            'transport' : vars.get('ghost-transport') or "",
            'service' : vars.get('ghost-service') or "",
            'mail_user' : vars.get('ghost-mail-user') or "",
            'mail_pass' : vars.get('ghost-mail-pass') or "",
            'from_address' : vars.get('ghost-from-address') or ""
        }

        # Create/Edit the Ghost config file
        with open(os.path.join(self.path, 'config.example.js'), 'r') as f:
            data = f.read()
        data = data.replace("port: '2368'", "port: '%s'" % self.backend_port)
        data = data.replace('http://my-ghost-blog.com', 'http://'+self.addr+(':'+str(self.port) if str(self.port) != '80' else''))
        if len(set(mail_settings.values())) != 1 and\
           mail_settings['transport'] != '':
            # If the mail settings exist, add them
            data = data.replace(
                "mail: {},",\
                'mail: {\n'
                "\tfromaddress: '" + mail_settings['from_address'] + "',\n"
                "\ttransport: '" + mail_settings['transport'] + "',\n"
                "\t\toptions: {\n"
                "\t\t\tservice: '" + mail_settings['service'] + "',\n"
                "\t\t\tauth: {\n"
                "\t\t\t\tuser: '" + mail_settings['mail_user'] + "',\n"
                "\t\t\t\tpass: '" + mail_settings['mail_pass'] + "'\n"
                "\t\t\t}\n"
                "\t\t}\n"
                "},\n"
            )
        with open(os.path.join(self.path, 'config.js'), 'w') as f:
            f.write(data)

        # Finally, make sure that permissions are set so that Ghost
        # can make adjustments and save plugins when need be.
        uid = users.get_system("ghost").uid
        for r, d, f in os.walk(self.path):
            for x in d:
                os.chown(os.path.join(r, x), uid, -1)
            for x in f:
                os.chown(os.path.join(r, x), uid, -1)
        
        cfg = {
                'directory': self.path,
                'user': 'ghost',
                'command': 'node %s'%os.path.join(self.path, 'index.js'),
                'autostart': 'true',
                'autorestart': 'true',
                'environment': 'NODE_ENV="production"',
                'stdout_logfile': '/var/log/ghost.log',
                'stderr_logfile': '/var/log/ghost.log'
            }
        s = services.Service(self.id, "supervisor", cfg=cfg)
        s.add()

    def pre_remove(self):
        pass

    def post_remove(self):
        services.get(self.id).remove()

    def ssl_enable(self, cfile, kfile):
        n = nginx.loadf('/etc/nginx/sites-available/%s'%self.id)
        for x in n.servers:
            if x.filter('Location', '/'):
                x.remove(x.filter('Location', '/')[0])
                self.addtoblock[0].add(
                    nginx.Key('proxy_set_header', 'X-Forwarded-For $proxy_add_x_forwarded_for'),
                    nginx.Key('proxy_set_header', 'X-Forwarded-Proto $scheme'),
                )
                x.add(self.addtoblock[0])
                nginx.dumpf(n, '/etc/nginx/sites-available/%s'%self.id)
        with open(os.path.join(self.path, 'config.js'), 'r') as f:
            data = f.read()
        data = data.replace('production: {\n        url: \'http://', 
            'production: {\n        url: \'https://')
        with open(os.path.join(self.path, 'config.js'), 'w') as f:
            f.write(data)
        services.get(self.id).restart()

    def ssl_disable(self):
        n = nginx.loadf('/etc/nginx/sites-available/%s'%self.id)
        for x in n.servers:
            if x.filter('Location', '/'):
                x.remove(x.filter('Location', '/')[0])
                x.add(self.addtoblock[0])
                nginx.dumpf(n, '/etc/nginx/sites-available/%s'%self.id)
        with open(os.path.join(self.path, 'config.js'), 'r') as f:
            data = f.read()
        data = data.replace('production: {\n        url: \'https://', 
            'production: {\n        url: \'http://')
        with open(os.path.join(self.path, 'config.js'), 'w') as f:
            f.write(data)
        services.get(self.id).restart()

    def update(self, pkg, ver):
        # General update procedure
        shell('unzip -o -d %s %s' % (self.path, pkg))
        uid = users.get_system("ghost").uid
        for r, d, f in os.walk(self.path):
            for x in d:
                os.chown(os.path.join(r, x), uid, -1)
            for x in f:
                os.chown(os.path.join(r, x), uid, -1)
        nodejs.install_from_package(self.path, 'production', {'sqlite': '/usr/bin/sqlite3', 'python': '/usr/bin/python2'})
        services.get(self.id).restart()
