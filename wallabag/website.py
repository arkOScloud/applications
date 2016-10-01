import hashlib
import nginx
import os
import shutil

from arkos.languages import php
from arkos.websites import Site
from arkos.utilities import errors, shell, random_string
from arkos.system import users, groups


class Wallabag(Site):
    addtoblock = [
        nginx.Location(
            '~ /(db)',
            nginx.Key('deny', 'all'),
            nginx.Key('return', '404')
        ),
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
            nginx.Key('try_files', '$uri $uri/ /index.php?$args')
        ),
        nginx.Location(
            '~ \.php$',
            nginx.Key('fastcgi_pass', 'unix:/run/php-fpm/php-fpm.sock'),
            nginx.Key('fastcgi_index', 'index.php'),
            nginx.Key('include', 'fastcgi.conf')
        ),
        nginx.Location(
            '~* \.(js|css|png|jpg|jpeg|gif|ico)$',
            nginx.Key('expires', 'max'),
            nginx.Key('log_not_found', 'off')
        )
    ]

    def pre_install(self, extra_vars):
        if not extra_vars.get('wb-username'):
            raise errors.InvalidConfigError(
                'Must choose a Wallabag username'
            )
        elif not extra_vars.get('wb-passwd'):
            raise errors.InvalidConfigError(
                'Must choose a Wallabag password'
            )
        elif '"' in extra_vars.get('wb-passwd')\
                or "'" in extra_vars.get('wb-passwd'):
            raise errors.InvalidConfigError(
                'Your Wallabag password must not include quotes'
            )

    def post_install(self, extra_vars, dbpasswd=""):
        secret_key = random_string()
        dbengine = 'mysql' \
            if self.meta.selected_dbengine == 'db-mariadb' \
            else 'sqlite'

        username = extra_vars.get("wb-username")
        passwd = extra_vars.get("wb-passwd") + username + secret_key
        passwd = hashlib.sha1(passwd).hexdigest()

        # Write a standard Wallabag config file
        shutil.copy(os.path.join(
            self.path,
            'inc/poche/config.inc.default.php'),
            os.path.join(self.path, 'inc/poche/config.inc.php'))
        with open(os.path.join(
                self.path,
                'inc/poche/config.inc.php'), 'r') as f:
            ic = f.readlines()
        oc = []
        for l in ic:
            if 'define (\'SALT\'' in l:
                l = '@define (\'SALT\', \'{0}\');\n'.format(secret_key)
                oc.append(l)
            elif 'define (\'STORAGE\'' in l:
                l = '@define (\'STORAGE\', \'{0}\');\n'.format(dbengine)
                oc.append(l)
            elif 'define (\'STORAGE_SQLITE\'' in l and dbengine == 'sqlite':
                l = '@define (\'STORAGE_SQLITE\', '\
                    '\'/var/lib/sqlite3/{0}.db\');\n'.format(self.db.id)
                oc.append(l)
            elif 'define (\'STORAGE_DB\'' in l and dbengine == 'mysql':
                l = "@define ('STORAGE_DB', '{0}');\n".format(self.db.id)
                oc.append(l)
            elif 'define (\'STORAGE_USER\'' in l and dbengine == 'mysql':
                l = "@define ('STORAGE_USER', '{0}');\n".format(self.db.id)
                oc.append(l)
            elif 'define (\'STORAGE_PASSWORD\'' in l and dbengine == 'mysql':
                l = '@define (\'STORAGE_PASSWORD\', '\
                    '\'{0}\');\n'.format(dbpasswd)
                oc.append(l)
            else:
                oc.append(l)
        with open(os.path.join(
                self.path,
                'inc/poche/config.inc.php'), 'w') as f:
            f.writelines(oc)

        # Make sure that the correct PHP settings are enabled
        php.enable_mod('sqlite3',
                       'pdo_mysql' if dbengine == 'mysql' else 'pdo_sqlite',
                       'zip', 'tidy')

        # Set up Composer and install the proper modules
        php.composer_install(self.path)

        uid, gid = users.get_system("http").uid, groups.get_system("http").gid

        # Set up the database then delete the install folder
        if dbengine == 'mysql':
            with open(os.path.join(self.path, 'install/mysql.sql')) as f:
                self.db.execute(f.read(), commit=True)
            self.db.execute(
                "INSERT INTO users (username, password, name, email) "
                "VALUES ('{0}', '{1}', '{2}', '');"
                .format(username, passwd, username),
                commit=True)
            lid = int(self.db.manager.connection.insert_id())
            self.db.execute(
                "INSERT INTO users_config (user_id, name, value) "
                "VALUES ({0}, 'pager', '10');".format(lid),
                commit=True)
            self.db.execute(
                "INSERT INTO users_config (user_id, name, value) "
                "VALUES ({0}, 'language', 'en_EN.UTF8');".format(lid),
                commit=True)
        else:
            shutil.copy(os.path.join(self.path, 'install/poche.sqlite'),
                        '/var/lib/sqlite3/{0}.db'.format(self.db.id))
            php.open_basedir('add', '/var/lib/sqlite3')
            os.chown("/var/lib/sqlite3/{0}.db".format(self.db.id), -1, gid)
            os.chmod("/var/lib/sqlite3/{0}.db".format(self.db.id), 0o664)
            self.db.execute(
                "INSERT INTO users (username, password, name, email) "
                "VALUES ('{0}', '{1}', '{2}', '');"
                .format(username, passwd, username))
            self.db.execute(
                "INSERT INTO users_config (user_id, name, value) "
                "VALUES (1, 'pager', '10');")
            self.db.execute(
                "INSERT INTO users_config (user_id, name, value) "
                "VALUES (1, 'language', 'en_EN.UTF8');")
        shutil.rmtree(os.path.join(self.path, 'install'))

        # Finally, make sure that permissions are set so that Wallabag
        # can make adjustments and save plugins when need be.
        for r, d, f in os.walk(self.path):
            for x in d:
                if d in ["assets", "cache", "db"]:
                    os.chmod(os.path.join(r, d), 0o755)
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
        shell('tar xzf {0} -C {1} --strip 1'.format(pkg, self.path))
        cachepath = os.path.join(self.path, 'cache')
        for x in os.listdir(cachepath):
            fpath = os.path.join(cachepath, x)
            if os.path.isdir(fpath):
                shutil.rmtree(fpath)
            else:
                os.unlink(fpath)
        shutil.rmtree(os.path.join(self.path, 'install'))
        shell('chmod -R 755 {0} {1} {2}'
              .format(os.path.join(self.path, 'assets/'),
                      os.path.join(self.path, 'cache/'),
                      os.path.join(self.path, 'db/')))
        shell('chown -R http:http '+self.path)
