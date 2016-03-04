import nginx
import os
import shutil

from arkos.system import users, groups
from arkos.websites import Site
from arkos.languages import php


class wikitten(Site):
    addtoblock = [
        nginx.Location('~* ^/static/(css|js|img|fonts)/.+.(jpg|jpeg|gif|css|png|js|ico|html|xml|txt|swf|pdf|txt|bmp|eot|svg|ttf|woff|woff2)$',
            nginx.Key('access_log', 'off'),
            nginx.Key('expires', 'max')
            ),
        nginx.Location('/',
            nginx.Key('rewrite', '^(.*)$ /index.php last')
            ),
        nginx.Location('~ \.php$',
            nginx.Key('fastcgi_pass', 'unix:/run/php-fpm/php-fpm.sock'),
            nginx.Key('fastcgi_index', 'index.php'),
            nginx.Key('include', 'fastcgi.conf')
            )
        ]

    def pre_install(self, vars):
	pass

    def post_install(self, vars, dbpasswd=""):
        # Write a standard Wikitten config file
        shutil.copy(os.path.join(self.path, 'config.php.example'),
            os.path.join(self.path, 'config.php'))
        with open(os.path.join(self.path, 'config.php'), 'r') as f:
            d = f.read()
        d = d.replace("'My Wiki'", "'%s'" % self.id)

        with open(os.path.join(self.path, 'config.php'), 'w') as f:
            f.write(d)

        # Give access to httpd
        uid, gid = users.get_system("http").uid, groups.get_system("http").gid
        for r, d, f in os.walk(self.path):
            for x in d:
                os.chown(os.path.join(r, x), uid, gid)
            for x in f:
                os.chown(os.path.join(r, x), uid, gid)

    def pre_remove(self):
        pass

    def post_remove(self):
        pass

    def enable_ssl(self, cfile, kfile):
        pass

    def disable_ssl(self):
        pass

    def update(self, pkg, ver):
        pass
 	# TODO: pull from Git at appropriate intervals
