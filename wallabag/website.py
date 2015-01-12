import hashlib
import nginx
import os
import shutil

from arkos.languages import php
from arkos.sites import Site
from arkos.utilities import shell, random_string
from arkos.system import users, groups


class Wallabag(Site):
    addtoblock = [
        nginx.Location('~ /(db)',
            nginx.Key('deny', 'all'),
            nginx.Key('return', '404')
            ),
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
        if not vars.get('wb-username'):
            raise Exception('Must choose a Wallabag username')
        elif not vars.get('wb-passwd'):
            raise Exception('Must choose a Wallabag password')
        elif '"' in vars.get('wb-passwd') or "'" in vars.get('wb-passwd'):
            raise Exception('Your Wallabag password must not include quotes')

    def post_install(self, vars, dbpasswd=""):
        secret_key = random_string()
        dbengine = 'mysql' if self.db.meta.name == 'MariaDB' else 'sqlite'

        username = vars.get("wb-username")
        passwd = vars.get("wb-passwd") + username + secret_key
        passwd = hashlib.sha1(passwd).hexdigest()

        # Write a standard Wallabag config file
        shutil.copy(os.path.join(self.path, 'inc/poche/config.inc.default.php'),
            os.path.join(self.path, 'inc/poche/config.inc.php'))
        with open(os.path.join(self.path, 'inc/poche/config.inc.php'), 'r') as f:
            ic = f.readlines()
        oc = []
        for l in ic:
            if 'define (\'SALT\'' in l:
                l = '@define (\'SALT\', \''+secret_key+'\');\n'
                oc.append(l)
            elif 'define (\'STORAGE\'' in l:
                l = '@define (\'STORAGE\', \''+dbengine+'\');\n'
                oc.append(l)
            elif 'define (\'STORAGE_SQLITE\'' in l and dbengine == 'sqlite':
                l = '@define (\'STORAGE_SQLITE\', \'/var/lib/sqlite3/'+self.db.name+'.db\');\n'
                oc.append(l)
            elif 'define (\'STORAGE_DB\'' in l and dbengine == 'mysql':
                l = '@define (\'STORAGE_DB\', \''+self.db.name+'\');\n'
                oc.append(l)
            elif 'define (\'STORAGE_USER\'' in l and dbengine == 'mysql':
                l = '@define (\'STORAGE_USER\', \''+self.db.name+'\');\n'
                oc.append(l)
            elif 'define (\'STORAGE_PASSWORD\'' in l and dbengine == 'mysql':
                l = '@define (\'STORAGE_PASSWORD\', \''+dbpasswd+'\');\n'
                oc.append(l)
            else:
                oc.append(l)
        with open(os.path.join(self.path, 'inc/poche/config.inc.php'), 'w') as f:
            f.writelines(oc)

        # Make sure that the correct PHP settings are enabled
        php.enable_mod('mysql' if dbengine == 'mysql' else 'sqlite3', 
            'pdo_mysql' if dbengine == 'mysql' else 'pdo_sqlite', 
            'zip', 'tidy', 'xcache', 'openssl')

        # Set up Composer and install the proper modules
        php.composer_install(self.path)
        
        uid, gid = users.get_system("http").uid, groups.get_system("http").gid

        # Set up the database then delete the install folder
        if dbengine == 'mysql':
            with open(os.path.join(self.path, 'install/mysql.sql')) as f:
                self.db.execute(f.read())
            self.db.execute(
                "INSERT INTO users (username, password, name, email) VALUES ('%s', '%s', '%s', '');" % (username, passwd, username),
                commit=True)
            lid = int(self.db.connection.insert_id())
            self.db.execute(
                "INSERT INTO users_config (user_id, name, value) VALUES (%s, 'pager', '10');" % lid,
                commit=True)
            self.db.execute(
                "INSERT INTO users_config (user_id, name, value) VALUES (%s, 'language', 'en_EN.UTF8');" % lid,
                commit=True)
        else:
            self.db.chkpath()
            shutil.copy(os.path.join(self.path, 'install/poche.sqlite'), '/var/lib/sqlite3/%s.db' % self.db.name)
            php.open_basedir('add', '/var/lib/sqlite3')
            os.chown("/var/lib/sqlite3/%s.db" % self.db.name, -1, gid)
            self.db.execute(
                "INSERT INTO users (username, password, name, email) VALUES ('%s', '%s', '%s', '');" % (username, passwd, username))
            self.db.execute(
                "INSERT INTO users_config (user_id, name, value) VALUES (1, 'pager', '10');")
            self.db.execute(
                "INSERT INTO users_config (user_id, name, value) VALUES (1, 'language', 'en_EN.UTF8');")
        shutil.rmtree(os.path.join(self.path, 'install'))

        # Finally, make sure that permissions are set so that Wallabag
        # can make adjustments and save plugins when need be.
        for r, d, f in os.walk(self.path):
            for x in d:
                if d in ["assets", "cache", "db"]:
                    os.chmod(os.path.join(root, d), 0755)
                os.chown(os.path.join(root, x), uid, gid)
            for x in f:
                os.chown(os.path.join(root, x), uid, gid)

    def pre_remove(self):
        pass

    def post_remove(self):
        pass

    def ssl_enable(self, cfile, kfile):
        pass

    def ssl_disable(self):
        pass

    def update(self, pkg, ver):
        # General update procedure
        shell('tar xzf %s -C %s --strip 1' % (pkg, self.path))
        for x in os.listdir(os.path.join(self.path, 'cache')):
            if os.path.isdir(os.path.join(self.path, 'cache', x)):
                shutil.rmtree(os.path.join(self.path, 'cache', x))
            else:
                os.unlink(os.path.join(self.path, 'cache', x))
        shutil.rmtree(os.path.join(self.path, 'install'))
        shell('chmod -R 755 '+os.path.join(self.path, 'assets/')+' '
            +os.path.join(self.path, 'cache/')+' '
            +os.path.join(self.path, 'db/'))
        shell('chown -R http:http '+self.path)
