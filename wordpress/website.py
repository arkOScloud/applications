import nginx
import os
import urllib

from arkos.languages import php
from arkos.websites import Site
from arkos.utilities import random_string
from arkos.system import users, groups


class WordPress(Site):
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
        nginx.Location('/',
            nginx.Key('try_files', '$uri $uri/ /index.php?$args')
            ),
        nginx.Location('~ \.php$',
            nginx.Key('fastcgi_pass', 'unix:/run/php-fpm/php-fpm.sock'),
            nginx.Key('fastcgi_index', 'index.php'),
            nginx.Key('include', 'fastcgi.conf')
            ),
        nginx.Location('~* \.(js|css|png|jpg|jpeg|gif|ico)$',
            nginx.Key('expires', 'max'),
            nginx.Key('log_not_found', 'off')
            )
        ]

    def pre_install(self, vars):
        pass

    def post_install(self, vars, dbpasswd=""):
        secret_key = random_string()

        # Use the WordPress key generators as first option
        # If connection fails, use the secret_key as fallback
        try:
            keysection = urllib.urlopen('https://api.wordpress.org/secret-key/1.1/salt/').read()
        except:
            keysection = ''
        if not 'define(\'AUTH_KEY' in keysection:
            keysection = (
                'define(\'AUTH_KEY\', \''+secret_key+'\');\n'
                'define(\'SECURE_AUTH_KEY\', \''+secret_key+'\');\n'
                'define(\'LOGGED_IN_KEY\', \''+secret_key+'\');\n'
                'define(\'NONCE_KEY\', \''+secret_key+'\');\n'
                )

        # Write a standard WordPress config file
        with open(os.path.join(self.path, 'wp-config.php'), 'w') as f:
            f.write('<?php\n'
                'define(\'DB_NAME\', \''+self.db.id+'\');\n'
                'define(\'DB_USER\', \''+self.db.id+'\');\n'
                'define(\'DB_PASSWORD\', \''+dbpasswd+'\');\n'
                'define(\'DB_HOST\', \'localhost\');\n'
                'define(\'DB_CHARSET\', \'utf8\');\n'
                'define(\'SECRET_KEY\', \''+secret_key+'\');\n'
                '\n'
                'define(\'WP_CACHE\', true);\n'
                'define(\'FORCE_SSL_ADMIN\', false);\n'
                '\n'
                +keysection+
                '\n'
                '$table_prefix = \'wp_\';\n'
                '\n'
                '/** Absolute path to the WordPress directory. */\n'
                'if ( !defined(\'ABSPATH\') )\n'
                '   define(\'ABSPATH\', dirname(__FILE__) . \'/\');\n'
                '\n'
                '/** Sets up WordPress vars and included files. */\n'
                'require_once(ABSPATH . \'wp-settings.php\');\n'
            )

        # Make sure that the correct PHP settings are enabled
        php.enable_mod('mysql', 'opcache')

        # Finally, make sure that permissions are set so that Wordpress
        # can make adjustments and save plugins when need be.
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
        with open(os.path.join(self.path, 'wp-config.php'), 'r') as f:
            ic = f.readlines()
        oc = []
        found = False
        for l in ic:
            if 'define(\'FORCE_SSL_ADMIN\'' in l:
                l = 'define(\'FORCE_SSL_ADMIN\', false);\n'
                oc.append(l)
                found = True
            else:
                oc.append(l)
        if found == False:
            oc.append('define(\'FORCE_SSL_ADMIN\', true);\n')
        with open(os.path.join(self.path, 'wp-config.php'), 'w') as f:
            f.writelines(oc)

    def disable_ssl(self):
        with open(os.path.join(self.path, 'wp-config.php'), 'r') as f:
            ic = f.readlines()
        oc = []
        found = False
        for l in ic:
            if 'define(\'FORCE_SSL_ADMIN\'' in l:
                l = 'define(\'FORCE_SSL_ADMIN\', false);\n'
                oc.append(l)
                found = True
            else:
                oc.append(l)
        if found == False:
            oc.append('define(\'FORCE_SSL_ADMIN\', false);\n')
        with open(os.path.join(self.path, 'wp-config.php'), 'w') as f:
            f.writelines(oc)

    def site_edited(self):
        if not self.db:
            return
        url = "http"
        url += ("s://" if self.cert else "://")
        url += self.addr
        url += ((":"+str(self.port)) if self.port not in [80, 443] else "")
        self.db.execute("UPDATE wp_options SET option_value = '%s' WHERE option_name = 'siteurl';" % url, commit=True)
        self.db.execute("UPDATE wp_options SET option_value = '%s' WHERE option_name = 'home';" % url, commit=True)
