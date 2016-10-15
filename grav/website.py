import nginx
import os

from arkos import logger
from arkos.languages import php
from arkos.websites import Site
from arkos.utilities import shell


class Grav(Site):
    addtoblock = [
        nginx.Location(
            '= /favicon.ico',
            nginx.Key('log_not_found', 'off'),
            nginx.Key('access_log', 'off')
            ),
        nginx.Location(
            '= /robots.txt',
            nginx.Key('allow', 'all'),
            nginx.Key('log_not_found', 'off'),
            nginx.Key('access_log', 'off')
            ),
        nginx.Location(
            '/',
            nginx.Key('try_files', '$uri $uri/ /index.html'),
            nginx.If(
                '(!-e $request_filename)',
                nginx.Key('rewrite', '^(.*)$ /index.php last')
                )
            ),
        nginx.Location(
            '~ \.php$',
            nginx.Key('fastcgi_pass', 'unix:/run/php-fpm/php-fpm.sock'),
            nginx.Key('fastcgi_split_path_info', '^(.+\.php)(/.+)$'),
            nginx.Key('fastcgi_index', 'index.php'),
            nginx.Key('fastcgi_param', 'SCRIPT_FILENAME '
                      '$document_root/$fastcgi_script_name'),
            nginx.Key('include', 'fastcgi_params')
            ),
        nginx.Location(
            '~* /(.git|cache|bin|logs|backups|tests)/.*$',
            nginx.Key('return', '403')
            ),
        nginx.Location(
            '~* /(system|vendor)/.*\.'
            '(txt|xml|md|html|yaml|php|pl|py|cgi|twig|sh|bat)$',
            nginx.Key('return', '403')
            ),
        nginx.Location(
            '~* /user/.*\.(txt|md|yaml|php|pl|py|cgi|twig|sh|bat)$',
            nginx.Key('return', '403')
            ),
        nginx.Location(
            '~ /(LICENSE.txt|composer.lock|composer.json|nginx.conf'
            '|web.config|htaccess.txt|\.htaccess)',
            nginx.Key('return', '403')
            ),
        ]

    def pre_install(self, extra_vars):
        pass

    def post_install(self, extra_vars, dbpasswd=""):
        # Add execution flag to binaries
        st = os.stat(os.path.join(self.path, "bin/gpm"))
        os.chmod(os.path.join(self.path, "bin/gpm"), st.st_mode | 0o111)
        st = os.stat(os.path.join(self.path, "bin/grav"))
        os.chmod(os.path.join(self.path, "bin/grav"), st.st_mode | 0o111)
        st = os.stat(os.path.join(self.path, "bin/plugin"))
        os.chmod(os.path.join(self.path, "bin/plugin"), st.st_mode | 0o111)

        # Make sure that the correct PHP settings are enabled
        php.enable_mod('curl', 'gd', 'opcache', 'zip')
        php.enable_mod('apcu', config_file="/etc/php/conf.d/apcu.ini")

    def pre_remove(self):
        pass

    def post_remove(self):
        pass

    def enable_ssl(self, cfile, kfile):
        pass

    def disable_ssl(self):
        pass

    def site_edited(self):
        pass

    def update_site(self, pkg, ver):
        cwd = os.getcwd()
        os.chdir(self.path)
        s = shell("bin/gpm selfupgrade -f")
        if s["code"] != 0:
            logger.error(
                "Webs", "Grav failed to run selfupgrade. Error: {0}"
                .format(s["stderr"].decode()))
        s = shell("bin/gpm update -f")
        if s["code"] != 0:
            logger.error(
                "Webs", "Grav failed to run plugin update. Error: {0}"
                .format(s["stderr"].decode()))
        os.chdir(cwd)
