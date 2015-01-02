import json
import nginx
import os

from arkos.core.utilities import shell
from arkos.core.languages import nodejs
from arkos.core.sites import SiteEngine


class Ghost(SiteEngine):
    addtoblock = [
        nginx.Location('/',
            nginx.Key('proxy_pass', 'http://127.0.0.1:2368'),
            nginx.Key('proxy_set_header', 'X-Real-IP $remote_addr'),
            nginx.Key('proxy_set_header', 'Host $host'),
            nginx.Key('proxy_buffering', 'off')
            )
        ]

    def pre_install(self, name, vars):
        pass

    def post_install(self, name, path, vars, dbinfo={}):
        d = json.loads(open(os.path.join(path, 'package.json'), 'r').read())
        del d['dependencies']['bcryptjs']
        d['dependencies']['bcrypt'] = '0.8'
        with open(os.path.join(path, 'package.json'), 'w') as f:
            f.write(json.dumps(d))
        with open(os.path.join(path, 'core/server/models/user.js'), 'r') as f:
            d = f.read()
        d = d.replace('bcryptjs', 'bcrypt')
        with open(os.path.join(path, 'core/server/models/user.js'), 'w') as f:
            f.write(d)

        nodejs.install_from_package(path, 'production', {'sqlite': '/usr/bin', 'python': '/usr/bin/python2'})
        self.System.Users.add('ghost')
        self.System.Services.edit(name,
            {
                'stype': 'program',
                'directory': path,
                'user': 'ghost',
                'command': 'node %s'%os.path.join(path, 'index.js'),
                'autostart': 'true',
                'autorestart': 'true',
                'environment': 'NODE_ENV="production"',
                'stdout_logfile': '/var/log/ghost.log',
                'stderr_logfile': '/var/log/ghost.log'
            }
        )
        self.System.Services.enable(name, 'supervisor')

        addr = vars.getvalue('addr', 'localhost')
        port = vars.getvalue('port', '80')

        # Get Mail settings
        mail_settings = {
            'transport' : vars.getvalue('ghost-transport', ''),
            'service' : vars.getvalue('ghost-service', ''),
            'mail_user' : vars.getvalue('ghost-mail-user', ''),
            'mail_pass' : vars.getvalue('ghost-mail-pass', ''),
            'from_address' : vars.getvalue('ghost-from-address', '')
        }

        # Create/Edit the Ghost config file
        with open(os.path.join(path, 'config.example.js'), 'r') as f:
            data = f.read()
        data = data.replace('http://my-ghost-blog.com', 'http://'+addr+(':'+port if port != '80' else''))
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
        with open(os.path.join(path, 'config.js'), 'w') as f:
            f.write(data)

        # Finally, make sure that permissions are set so that Ghost
        # can make adjustments and save plugins when need be.
        uid = self.System.Users.get("ghost")["uid"]
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
        with open(os.path.join(path, 'config.js'), 'r') as f:
            data = f.read()
        data = data.replace('production: {\n        url: \'http://', 
            'production: {\n        url: \'https://')
        with open(os.path.join(path, 'config.js'), 'w') as f:
            f.write(data)
        self.System.Services.restart(name, 'supervisor')

    def ssl_disable(self, path):
        name = os.path.basename(path)
        n = nginx.loadf('/etc/nginx/sites-available/%s'%name)
        for x in n.servers:
            if x.filter('Location', '/'):
                x.remove(x.filter('Location', '/')[0])
                x.add(self.addtoblock[0])
                nginx.dumpf(n, '/etc/nginx/sites-available/%s'%name)
        with open(os.path.join(path, 'config.js'), 'r') as f:
            data = f.read()
        data = data.replace('production: {\n        url: \'https://', 
            'production: {\n        url: \'http://')
        with open(os.path.join(path, 'config.js'), 'w') as f:
            f.write(data)
        self.System.Services.restart(name, 'supervisor')

    def update(self, path, pkg, ver):
        # General update procedure
        name = os.path.basename(path)
        shell('unzip -o -d %s %s' % (path, pkg))
        uid = self.System.Users.get("ghost")["uid"]
        for r, d, f in os.walk(path):
            for x in d:
                os.chown(os.path.join(root, x), uid, -1)
            for x in f:
                os.chown(os.path.join(root, x), uid, -1)
        nodejs.install_from_package(path, 'production', {'sqlite': '/usr/bin', 'python': '/usr/bin/python2'})
        self.System.Services.restart(name, 'supervisor')
