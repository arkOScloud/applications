import nginx
import os
import semantic_version as semver
import shutil

from arkos import logger
from arkos.languages import php
from arkos.websites import Site
from arkos.utilities import errors, shell, random_string
from arkos.system import users, groups


class Wallabag(Site):
    addtoblock = [
        nginx.Location(
            "/",
            nginx.Key("try_files", "$uri /app.php$is_args$args")
        ),
        nginx.Location(
            "~ ^/app\.php(/|$)",
            nginx.Key('fastcgi_pass', 'unix:/run/php-fpm/php-fpm.sock'),
            nginx.Key('fastcgi_split_path_info', "^(.+\.php)(/.*)$"),
            nginx.Key('include', 'fastcgi.conf'),
            nginx.Key(
                'fastcgi_param',
                'SCRIPT_FILENAME $realpath_root$fastcgi_script_name'
            ),
            nginx.Key('fastcgi_param', 'DOCUMENT_ROOT $realpath_root')
        )
    ]

    def pre_install(self, extra_vars):
        pass

    def post_install(self, extra_vars, dbpasswd=""):
        secret_key = random_string()
        dbengine = 'mysql' \
            if self.app.selected_dbengine == 'db-mariadb' \
            else 'sqlite'

        # Write a standard Wallabag config file
        config_file = os.path.join(self.path, 'app/config/parameters.yml')
        with open(config_file + ".dist", 'r') as f:
            ic = f.readlines()
        with open(config_file, 'w') as f:
            for l in ic:
                if "database_driver: " in l:
                    pdo = "pdo_mysql" if dbengine == "mysql" else "pdo_sqlite"
                    l = "    database_driver: {0}\n".format(pdo)
                elif "database_path: " in l and dbengine == 'sqlite':
                    l = "    database_path: {0}\n".format(self.db.path)
                elif "database_name: " in l and dbengine == 'mysql':
                    l = "    database_name: {0}\n".format(self.db.id)
                elif "database_user: " in l and dbengine == 'mysql':
                    l = "    database_user: {0}\n".format(self.db.id)
                elif "database_password: " in l and dbengine == 'mysql':
                    l = '    database_password: "{0}"\n'.format(dbpasswd)
                elif "secret: " in l:
                    l = "    secret: {0}\n".format(secret_key)
                f.write(l)

        # Make sure that the correct PHP settings are enabled
        php.enable_mod('sqlite3', 'bcmath',
                       'pdo_mysql' if dbengine == 'mysql' else 'pdo_sqlite',
                       'zip', 'tidy')
        php.open_basedir('add', '/usr/bin/php')

        uid, gid = users.get_system("http").uid, groups.get_system("http").gid

        # Set up the database then delete the install folder
        if dbengine == 'sqlite3':
            php.open_basedir('add', '/var/lib/sqlite3')

        cwd = os.getcwd()
        os.chdir(self.path)
        s = shell("php bin/console wallabag:install --env=prod -n")
        if s["code"] != 0:
            logger.error("Websites", s["stderr"].decode())
            raise errors.OperationFailedError(
                "Failed to populate database. See logs for more info"
            )
        os.chdir(cwd)

        if dbengine == 'sqlite3':
            os.chown("/var/lib/sqlite3/{0}.db".format(self.db.id), -1, gid)
            os.chmod("/var/lib/sqlite3/{0}.db".format(self.db.id), 0o660)

        # Finally, make sure that permissions are set so that Wallabag
        # can make adjustments and save plugins when need be.
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
        # General update procedure
        if semver.Version.coerce(ver) > semver.Version('2.0.0'):
            raise Exception(
                "Cannot automatically update from 1.x to 2.x. Please see "
                "Wallabag documentation for more information."
            )
        os.rename(
            os.path.join(self.path, 'app/config/parameters.yml'),
            '/tmp/_wb_parameters.yml'
        )
        shell('tar xzf {0} -C {1} --strip 1'.format(pkg, self.path))
        os.rename(
            '/tmp/_wb_parameters.yml',
            os.path.join(self.path, 'app/config/parameters.yml')
        )
        cachepath = os.path.join(self.path, 'var/cache')
        for x in os.listdir(cachepath):
            fpath = os.path.join(cachepath, x)
            if os.path.isdir(fpath):
                shutil.rmtree(fpath)
            else:
                os.unlink(fpath)
        uid, gid = users.get_system("http").uid, groups.get_system("http").gid
        for r, d, f in os.walk(self.path):
            for x in d:
                os.chown(os.path.join(r, x), uid, gid)
            for x in f:
                os.chown(os.path.join(r, x), uid, gid)
