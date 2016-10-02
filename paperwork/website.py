import nginx
import os
import shutil

from arkos.languages import php, nodejs
from arkos.system import users, groups
from arkos.websites import Site
from arkos.utilities import shell


class Paperword(Site):
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
        nginx.Key('try_files', '$uri $uri/ @rewrite'),
        nginx.Location(
            '@rewrite',
            nginx.Key('rewrite', '^/(.*)$ /index.php?_url=/$1')
        ),
        nginx.Location(
            '~ \.php$',
            nginx.Key('fastcgi_pass',
                      'unix:/run/php-fpm/php-fpm.sock'),
            nginx.Key('fastcgi_index', 'index.php'),
            nginx.Key('include', 'fastcgi_params'),
            nginx.Key('fastcgi_split_path_info',
                      '^(.+\.php)(/.+)$'),
            nginx.Key('fastcgi_param',
                      'PATH_INFO $fastcgi_path_info'),
            nginx.Key('fastcgi_param',
                      'PATH_TRANSLATED '
                      '$document_root$fastcgi_path_info'),
            nginx.Key('fastcgi_param',
                      'SCRIPT_FILENAME '
                      '$document_root$fastcgi_script_name')
        ),
        nginx.Location(
            '~ /\.ht',
            nginx.Key('deny', 'all')
        )]

    def pre_install(self, extra_vars):
        pass

    def post_install(self, extra_vars, dbpasswd=""):
        # Get around top-level zip restriction (FIXME 0.7.2)
        if "paperwork-master" in os.listdir(self.path):
            tmp_path = os.path.abspath(os.path.join(self.path, "../pwrk-tmp"))
            os.rename(os.path.join(self.path,
                                   "paperwork-master/frontend"), tmp_path)
            os.rename(os.path.join(self.path, ".arkos"),
                      os.path.join(tmp_path, ".arkos"))
            shutil.rmtree(self.path)
            os.rename(tmp_path, self.path)

        # Make sure that the correct PHP settings are enabled
        php.enable_mod('gd', 'opcache', 'mysql', 'pdo_mysql', 'mcrypt')
        php.enable_mod('apcu', config_file="/etc/php/conf.d/apcu.ini")

        dbstr = "mysql, localhost, 3389, {0}, {1}, {0}"\
            .format(self.id, dbpasswd)
        with open(os.path.join(self.path,
                               'app/storage/db_settings'), 'w') as f:
            f.write(dbstr)

        php.composer_install(self.path)
        nodejs.install("gulp", as_global=True)
        nodejs.install_from_package(self.path, stat=None)

        cwd = os.getcwd()
        os.chdir(self.path)
        s = shell("bower install --allow-root", stdin='y\n')
        if s["code"] != 0:
            raise Exception("Failed to run bower: {0}".format(s["stderr"]))
        s = shell("gulp")
        if s["code"] != 0:
            raise Exception("Failed to run gulp: {0}".format(s["stderr"]))
        s = shell("php artisan migrate --force")
        if s["code"] != 0:
            raise Exception("Failed to run artisan: {0}".format(s["stderr"]))
        os.chdir(cwd)

        # Make sure the webapps config points to the public directory.
        c = nginx.loadf(os.path.join('/etc/nginx/sites-available', self.id))
        for x in c.servers:
            if x.filter('Key', 'root'):
                x.filter('Key', 'root')[0].value = \
                    os.path.join(self.path, 'public')
        nginx.dumpf(c, os.path.join('/etc/nginx/sites-available', self.id))
        uid, gid = users.get_system("http").uid, groups.get_system("http").gid
        for r, d, f in os.walk(os.path.join(self.path, 'app')):
            for x in d:
                os.chmod(os.path.join(r, x), 0o755)
                os.chown(os.path.join(r, x), uid, gid)
            for x in f:
                os.chmod(os.path.join(r, x), 0o644)
                os.chown(os.path.join(r, x), uid, gid)
        if os.path.exists(os.path.join(self.path, 'app/storage/setup')):
            os.unlink(os.path.join(self.path, 'app/storage/setup'))

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

    def update(self, pkg, ver):
        pass
