import git
import json
import nginx
import os

from arkos.core.languages import nodejs
from arkos.core.sites import SiteEngine
from arkos.core.utilities import random_string


class Etherpad(SiteEngine):
    addtoblock = [
        nginx.Location('/',
            nginx.Key('proxy_pass', 'http://127.0.0.1:2369'),
            nginx.Key('proxy_set_header', 'X-Real-IP $remote_addr'),
            nginx.Key('proxy_set_header', 'Host $host'),
            nginx.Key('proxy_buffering', 'off')
        )
    ]

    def pre_install(self, name, vars):
        eth_name = vars.getvalue('ether_admin', '')
        eth_pass = vars.getvalue('ether_pass', '')
        if not (eth_name and eth_pass):
            raise Exception('You must enter an admin name AND password'
                            'in the App Settings tab!')

    def post_install(self, name, path, vars, dbinfo={}):
        # Create/Edit the config file
        cfg = {
            "title": "Etherpad",
            "favicon": "favicon.ico",
            "ip": "127.0.0.1",
            "port": "2369",
            "sessionKey": random_string(),
            "dbType": "mysql",
            "dbSettings": {
                "user": dbinfo['user'],
                "host": "localhost",
                "password": dbinfo['passwd'],
                "database": dbinfo['name']
            },
            "defaultPadText": (
                "Welcome to Etherpad on arkOS!\n\nThis pad text is "
                "synchronized as you type, so that everyone viewing this page "
                "sees the same text. This allows you to collaborate seamlessly "
                "on documents!\n\nGet involved with Etherpad at "
                "http://etherpad.org, or with arkOS at http://arkos.io\n"
            ),
            "requireSession": False,
            "editOnly": False,
            "minify": True,
            "maxAge": 60 * 60 * 6,
            "abiword": None,
            "requireAuthentication": False,
            "requireAuthorization": False,
            "trustProxy": True,
            "disableIPlogging": False,
            "socketTransportProtocols": [
                "xhr-polling", "jsonp-polling", "htmlfile"
            ],
            "loglevel": "INFO",
            "logconfig": {
                "appenders": [
                    {"type": "console"}
                ]
            },
            "users": {
                vars.getvalue('ether_admin'): {
                    "password": vars.getvalue('ether_pass'),
                    "is_admin": True
                },
            },

        }
        with open(os.path.join(path, 'settings.json'), 'w') as f:
            json.dump(cfg, f, indent=4)

        self.System.Users.add("etherpad")

        # Install selected plugins
        mods = list(                            # e.g. "ep_plugin/ep_adminpads"
            str(var).split("/")[1]              #                 ^^^^^^^^^^^^
            for var in vars
            if var.startswith('ep_plugin/') and int(vars.getvalue(var))
        )
        if mods:
            mod_inst_path = os.path.join(path, "node_modules")
            if not os.path.exists(mod_inst_path):
                os.mkdir(mod_inst_path)
            nodejs.install(*mods, install_path=mod_inst_path)

        # node-gyp needs the HOME variable to be set
        with open(os.path.join(path, 'bin/installDeps.sh')) as f:
            run_script = f.readlines()
        # this is a hack. supervisor does not kill node when stopping ep.
        run_script.insert(1, 'killall node\n')
        run_script.insert(1, 'export HOME=%s\n' % path)
        with open(os.path.join(path, 'bin/installDeps.sh'), 'w') as f:
            f.writelines(run_script)

        # Change owner of everything in the etherpad path
        uid = self.System.Users.get("etherpad")["uid"]
        for r, d, f in os.walk(path):
            for x in d:
                os.chown(os.path.join(root, x), uid, -1)
            for x in f:
                os.chown(os.path.join(root, x), uid, -1)

        # Make supervisor entry
        self.System.Services.edit(name,
            {
                'stype': 'program',
                'directory': path,
                'user': 'etherpad',
                'command': 'bash bin/run.sh',
                'autostart': 'true',
                'autorestart': 'false',
                'stdout_logfile': '/var/log/etherpad.log',
                'stderr_logfile': '/var/log/etherpad.log'
            }
        )
        self.System.Services.enable(name, 'supervisor')
        #TODO: user auth with nginx??

    def pre_remove(self, site):
        pass

    def post_remove(self, site):
        self.System.Services.remove(site["name"], 'supervisor')

    def ssl_enable(self, path, cfile, kfile):
        name = os.path.basename(path)
        n = nginx.loadf('/etc/nginx/sites-available/%s' % name)
        for x in n.servers:
            if x.filter('Location', '/'):
                x.remove(x.filter('Location', '/')[0])
                self.addtoblock[0].add(
                    nginx.Key('proxy_set_header',
                              'X-Forwarded-For $proxy_add_x_forwarded_for'),
                    nginx.Key('proxy_set_header',
                              'X-Forwarded-Proto $scheme'),
                )
                x.add(self.addtoblock[0])
                nginx.dumpf(n, '/etc/nginx/sites-available/%s' % name)

    def ssl_disable(self, path):
        name = os.path.basename(path)
        n = nginx.loadf('/etc/nginx/sites-available/%s' % name)
        for x in n.servers:
            if x.filter('Location', '/'):
                x.remove(x.filter('Location', '/')[0])
                x.add(self.addtoblock[0])
                nginx.dumpf(n, '/etc/nginx/sites-available/%s' % name)

    def update(self, path, pkg, ver):
        name = os.path.basename(path)
        repo = git.Repo()
        repo.remotes.origin.pull()
        uid = self.System.Users.get("etherpad")["uid"]
        for r, d, f in os.walk(path):
            for x in d:
                os.chown(os.path.join(root, x), uid, -1)
            for x in f:
                os.chown(os.path.join(root, x), uid, -1)
        self.System.Services.restart(name, 'supervisor')
