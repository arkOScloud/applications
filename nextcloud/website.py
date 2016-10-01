import nginx
import os
import re
import shutil

from arkos.languages import php
from arkos.websites import Site
from arkos.utilities import shell, random_string
from arkos.system import users, groups


class Nextcloud(Site):
    addtoblock = [
        nginx.Key('error_page', '403 /core/templates/403.php'),
        nginx.Key('error_page', '404 /core/templates/404.php'),
        nginx.Key('client_max_body_size', '10G'),
        nginx.Key('fastcgi_buffers', '64 4K'),
        nginx.Key('fastcgi_buffer_size', '64K'),
        nginx.Location(
            '= /robots.txt',
            nginx.Key('allow', 'all'),
            nginx.Key('log_not_found', 'off'),
            nginx.Key('access_log', 'off')
            ),
        nginx.Location(
            '= /.well-known/carddav',
            nginx.Key('return', '301 $scheme://$host/remote.php/dav')
        ),
        nginx.Location(
            '= /.well-known/caldav',
            nginx.Key('return', '301 $scheme://$host/remote.php/dav')
        ),
        nginx.Location(
            '/',
            nginx.Key(
                'rewrite',
                '^ /index.php$uri'),
            ),
        nginx.Location(
            '~ ^/(?:build|tests|config|lib|3rdparty|templates|data)/',
            nginx.Key('deny', 'all')
            ),
        nginx.Location(
            '~ ^/(?:\.|autotest|occ|issue|indie|db_|console)',
            nginx.Key('deny', 'all')
            ),
        nginx.Location(
            '~ ^/(?:index|remote|public|cron|core/ajax/update|status|ocs/v[12]'
            '|updater/.+|ocs-provider/.+|core/templates/40[34])\.php(?:$|/)',
            nginx.Key('include', 'fastcgi_params'),
            nginx.Key('fastcgi_split_path_info', '^(.+\.php)(/.+)$'),
            nginx.Key('fastcgi_param', 'SCRIPT_FILENAME '
                      '$document_root$fastcgi_script_name'),
            nginx.Key('fastcgi_param', 'PATH_INFO $fastcgi_path_info'),
            nginx.Key('fastcgi_param', 'modHeadersAvailable true'),
            nginx.Key('fastcgi_param', 'front_controller_active true'),
            nginx.Key('fastcgi_pass', 'unix:/run/php-fpm/php-fpm.sock'),
            nginx.Key('fastcgi_intercept_errors', 'on'),
            nginx.Key('fastcgi_read_timeout', '900s')
            ),
        nginx.Location(
            '~ ^/(?:updater|ocs-provider)(?:$|/)',
            nginx.Key('try_files', '$uri/ =404'),
            nginx.Key('index', 'index.php')
        ),
        nginx.Location(
            '~* \.(?:css|js)$',
            nginx.Key('try_files', '$uri /index.php$uri$is_args$args'),
            nginx.Key('add_header', 'Cache-Control "public, max-age=7200"'),
            nginx.Key('add_header', 'X-Content-Type-Options nosniff'),
            nginx.Key('add_header', 'X-XSS-Protection "1; mode=block"'),
            nginx.Key('add_header', 'X-Frame-Options "SAMEORIGIN"'),
            nginx.Key('add_header', 'X-Robots-Tag none'),
            nginx.Key('add_header', 'X-Download-Options noopen'),
            nginx.Key('add_header', 'X-Permitted-Cross-Domain-Policies none'),
            nginx.Key('access_log', 'off')
            ),
        nginx.Location(
            '~* \.(?:svg|gif|png|html|ttf|woff|ico|jpg|jpeg)$',
            nginx.Key('try_files', '$uri /index.php$uri$is_args$args'),
            nginx.Key('access_log', 'off')
            )
        ]

    def pre_install(self, vars_):
        pass

    def post_install(self, vars_, dbpasswd=""):
        php.open_basedir('add', '/dev')

        # If there is a custom path for the data directory, add to open_basedir
        uid, gid = users.get_system("http").uid, groups.get_system("http").gid
        os.makedirs(os.path.join(self.path, "data"))
        os.chown(os.path.join(self.path, "data"), uid, gid)
        if self.data_path == self.path:
            self.data_path = os.path.join(self.path, "data")
        else:
            try:
                os.makedirs(os.path.join(self.data_path))
            except OSError as e:
                if e[0] == 17:
                    pass
                else:
                    raise
            os.chown(os.path.join(self.data_path), uid, gid)
            php.open_basedir('add', self.data_path)

        # Make sure that the correct PHP settings are enabled
        php.enable_mod('opcache', 'mysql', 'pdo_mysql', 'zip', 'gd', 'ldap',
                       'iconv', 'openssl', 'posix')
        php.enable_mod('apcu', 'apc', config_file="/etc/php/conf.d/apcu.ini")
        php.change_setting('apc.enable_cli', '1',
                           config_file="/etc/php/conf.d/apcu.ini")

        # Make sure php-fpm has the correct settings,
        # otherwise Nextcloud breaks
        with open("/etc/php/php-fpm.conf", "r") as f:
            lines = f.readlines()
        with open("/etc/php/php-fpm.conf", "w") as f:
            for line in lines:
                if ";clear_env = " in line:
                    line = "clear_env = no\n"
                f.write(line)

        php.change_setting("always_populate_raw_post_data", "-1")
        mydir = os.getcwd()
        os.chdir(self.path)
        s = shell(('php occ maintenance:install '
                   '--database "mysql" --database-name "{}" '
                   '--database-user "{}" --database-pass "{}" '
                   '--admin-pass "{}" --data-dir "{}"'
                   ).format(self.db.id, self.db.id, dbpasswd,
                            dbpasswd, self.data_path))
        if s["code"] != 0:
            raise Exception("Nextcloud database population failed")
        s = shell("php occ app:enable user_ldap")
        if s["code"] != 0:
            raise Exception("Nextcloud LDAP configuration failed")
        os.chdir(mydir)
        os.chown(os.path.join(self.path, "config/config.php"), uid, gid)

        ldap_sql = ("REPLACE INTO oc_appconfig "
                    "(appid, configkey, configvalue) VALUES"
                    "('core', 'backgroundjobs_mode', 'cron'),"
                    "('user_ldap', 'ldap_uuid_attribute', 'auto'),"
                    "('user_ldap', 'ldap_host', 'localhost'),"
                    "('user_ldap', 'ldap_port', '389'),"
                    "('user_ldap', 'ldap_base', 'dc=arkos-servers,dc=org'),"
                    "('user_ldap', 'ldap_base_users', "
                    "'dc=arkos-servers,dc=org'),"
                    "('user_ldap', 'ldap_base_groups', "
                    "'dc=arkos-servers,dc=org'),"
                    "('user_ldap', 'ldap_tls', '0'),"
                    "('user_ldap', 'ldap_display_name', 'cn'),"
                    "('user_ldap', 'ldap_userlist_filter', "
                    "'objectClass=mailAccount'),"
                    "('user_ldap', 'ldap_group_filter', "
                    "'objectClass=posixGroup'),"
                    "('user_ldap', 'ldap_group_display_name', 'cn'),"
                    "('user_ldap', 'ldap_group_member_assoc_attribute', "
                    "'uniqueMember'),"
                    "('user_ldap', 'ldap_login_filter', "
                    "'(&(|(objectclass=posixAccount))(|(uid=%uid)))'),"
                    "('user_ldap', 'ldap_quota_attr', 'mailQuota'),"
                    "('user_ldap', 'ldap_quota_def', ''),"
                    "('user_ldap', 'ldap_email_attr', 'mail'),"
                    "('user_ldap', 'ldap_cache_ttl', '600'),"
                    "('user_ldap', 'ldap_configuration_active', '1'),"
                    "('user_ldap', 'home_folder_naming_rule', ''),"
                    "('user_ldap', 'ldap_backup_host', ''),"
                    "('user_ldap', 'ldap_dn', ''),"
                    "('user_ldap', 'ldap_agent_password', ''),"
                    "('user_ldap', 'ldap_backup_port', ''),"
                    "('user_ldap', 'ldap_nocase', ''),"
                    "('user_ldap', 'ldap_turn_off_cert_check', ''),"
                    "('user_ldap', 'ldap_override_main_server', ''),"
                    "('user_ldap', 'ldap_attributes_for_user_search', ''),"
                    "('user_ldap', 'ldap_attributes_for_group_search', ''),"
                    "('user_ldap', 'ldap_expert_username_attr', 'uid'),"
                    "('user_ldap', 'ldap_expert_uuid_attr', '');"
                    )
        self.db.execute(ldap_sql, commit=True)
        self.db.execute("DELETE FROM oc_group_user;", commit=True)
        self.db.execute("INSERT INTO oc_group_user VALUES ('admin','{0}');"
                        .format(vars.get("nc-admin", "admin")), commit=True)

        if not os.path.exists("/etc/cron.d"):
            os.mkdir("/etc/cron.d")
        with open("/etc/cron.d/nc-{0}".format(self.id), "w") as f:
            f.write("*/15 * * * * http php -f {0} > /dev/null 2>&1"
                    .format(os.path.join(self.path, "cron.php")))

        with open(os.path.join(self.path, "config", "config.php"), "r") as f:
            data = f.read()
        while re.search("\n(\s*('|\")memcache.local.*?\n)", data, re.DOTALL):
            data = data.replace(re.search("\n(\s*('|\")memcache.local.*?\n)",
                                          data, re.DOTALL).group(1), "")
        data = data.split("\n")
        with open(os.path.join(self.path, "config", "config.php"), "w") as f:
            for x in data:
                if not x.endswith("\n"):
                    x += "\n"
                if x.startswith(");"):
                    f.write("  'memcache.local' => '\OC\Memcache\APCu',\n")
                f.write(x)

        if os.path.exists(
            os.path.join(
                self.data_path,
                'data/files_external/rootcerts.crt')):
            os.chown(
                os.path.join(
                    self.data_path,
                    'data/files_external/rootcerts.crt'),
                uid, gid)

        self.site_edited()

    def pre_remove(self):
        datadir = ''
        if os.path.exists(os.path.join(self.path, 'config', 'config.php')):
            with open(
                os.path.join(
                    self.path, 'config', 'config.php'), 'r') as f:
                for line in f.readlines():
                    if 'datadirectory' in line:
                        data = line.split("'")[1::2]
                        datadir = data[1]
        elif os.path.exists(
            os.path.join(
                self.path, 'config', 'autoconfig.php')):
            with open(
                os.path.join(
                    self.path, 'config', 'autoconfig.php'), 'r') as f:
                for line in f.readlines():
                    if 'directory' in line:
                        data = line.split('"')[1::2]
                        datadir = data[1]
        if datadir:
            shutil.rmtree(datadir)
            php.open_basedir('del', datadir)

    def post_remove(self):
        if os.path.exists("/etc/cron.d/nc-%s" % self.id):
            os.unlink("/etc/cron.d/nc-%s" % self.id)

    def enable_ssl(self, cfile, kfile):
        # First, force SSL in Nextcloud's config file
        if os.path.exists(os.path.join(self.path, 'config', 'config.php')):
            px = os.path.join(self.path, 'config', 'config.php')
        else:
            px = os.path.join(self.path, 'config', 'autoconfig.php')
        with open(px, 'r') as f:
            ic = f.readlines()
        oc = []
        found = False
        for l in ic:
            if '"forcessl" =>' in l:
                l = '"forcessl" => true,\n'
                oc.append(l)
                found = True
            else:
                oc.append(l)
        if found is False:
            for x in enumerate(oc):
                if '"dbhost" =>' in x[1]:
                    oc.insert(x[0] + 1, '"forcessl" => true,\n')
        with open(px, 'w') as f:
            f.writelines(oc)

    def disable_ssl(self):
        if os.path.exists(os.path.join(self.path, 'config', 'config.php')):
            px = os.path.join(self.path, 'config', 'config.php')
        else:
            px = os.path.join(self.path, 'config', 'autoconfig.php')
        with open(px, 'r') as f:
            ic = f.readlines()
        oc = []
        found = False
        for l in ic:
            if '"forcessl" =>' in l:
                l = '"forcessl" => false,\n'
                oc.append(l)
                found = True
            else:
                oc.append(l)
        if found is False:
            for x in enumerate(oc):
                if '"dbhost" =>' in x[1]:
                    oc.insert(x[0] + 1, '"forcessl" => false,\n')
        with open(px, 'w') as f:
            f.writelines(oc)

    def site_edited(self):
        # Remove the existing trusted_sites array
        # then add a new one based on the new addr
        if os.path.exists(os.path.join(self.path, 'config', 'config.php')):
            path = os.path.join(self.path, 'config', 'config.php')
        else:
            raise Exception("Nextcloud config file not found")
        with open(path, "r") as f:
            data = f.read()
        while re.search("\n(\s*('|\")trusted_domains.*?\).*?\n)",
                        data, re.DOTALL):
            data = data.replace(
                re.search("\n(\s*('|\")trusted_domains.*?\).*?\n)",
                          data, re.DOTALL).group(1), "")
        data = data.split("\n")
        with open(path, "w") as f:
            for x in data:
                if not x.endswith("\n"):
                    x += "\n"
                if x.startswith(");"):
                    f.write("  'trusted_domains' => "
                            "array('localhost','{0}'),\n"
                            .format(self.domain))
                f.write(x)
