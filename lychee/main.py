import grp
import nginx
import os

from arkos.core.languages import php
from arkos.core.sites import SiteEngine


class Lychee(SiteEngine):
    addtoblock = [
        nginx.Location('= /favicon.ico',
            nginx.Key('log_not_found', 'off'),
            nginx.Key('access_log', 'off')
            ),
        nginx.Location('= /robots.txt',
            nginx.Key('allow', 'all'),
            nginx.Key('log_not_found', 'off'),
            nginx.Key('access_log', 'off')
            ),
        nginx.Location('~ \.php$',
            nginx.Key('fastcgi_pass', 'unix:/run/php-fpm/php-fpm.sock'),
            nginx.Key('fastcgi_index', 'index.php'),
            nginx.Key('include', 'fastcgi.conf')
            )
        ]

    def pre_install(self, name, vars):
        pass

    def post_install(self, name, path, vars, dbinfo={}):
        # Create Lychee automatic configuration file
        with open(os.path.join(path, 'data', 'config.php'), 'w') as f:
            f.write(
                '<?php\n'
                '   if(!defined(\'LYCHEE\')) exit(\'Error: Direct access is allowed!\');\n'
                '   $dbHost = \'localhost\';\n'
                '   $dbUser = \'' + dbinfo['user'] + '\';\n'
                '   $dbPassword = \'' + dbinfo['passwd'] + '\';\n'
                '   $dbName = \'' + dbinfo['name'] + '\';\n'
                '   $dbTablePrefix = \'\';\n'
                '?>\n'
            )

        # Make sure that the correct PHP settings are enabled
        php.enable_mod('mysql', 'mysqli', 'gd', 'zip', 'exif', 'json', 'mbstring')

        # Rename lychee index.html to index.php to make it work with our default nginx config
        os.rename(os.path.join(path, "index.html"), os.path.join(path, "index.php"))

        # Finally, make sure that permissions are set so that Lychee
        # can make adjustments and save plugins when need be.
        uid, gid = self.System.Users.get("http")["uid"], self.System.Users.get_group("http")["gid"]
        for r, d, f in os.walk(path):
            for x in d:
                os.chown(os.path.join(root, x), uid, gid)
            for x in f:
                os.chown(os.path.join(root, x), uid, gid)

        return "Lychee has been installed. Login with a blank username and password the first time to set your credentials."

    def pre_remove(self, site):
        pass

    def post_remove(self, site):
        pass

    def ssl_enable(self, path, cfile, kfile):
        pass

    def ssl_disable(self, path):
        pass

