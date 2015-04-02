import errno
import nginx
import os
import re
import shutil

from arkos.languages import php
from arkos.websites import Site
from arkos.utilities import shell, random_string
from arkos.system import users, groups


class ownCloud(Site):
    addtoblock = [
        nginx.Key('error_page', '403 = /core/templates/403.php'),
        nginx.Key('error_page', '404 = /core/templates/404.php'),
        nginx.Key('client_max_body_size', '10G'),
        nginx.Key('fastcgi_buffers', '64 4K'),
        nginx.Key('rewrite', '^/caldav(.*)$ /remote.php/caldav$1 redirect'),
        nginx.Key('rewrite', '^/carddav(.*)$ /remote.php/carddav$1 redirect'),
        nginx.Key('rewrite', '^/webdav(.*)$ /remote.php/webdav$1 redirect'),
        nginx.Location('= /robots.txt',
            nginx.Key('allow', 'all'),
            nginx.Key('log_not_found', 'off'),
            nginx.Key('access_log', 'off')
            ),
        nginx.Location('~ ^/(?:\.htaccess|data|config|db_structure\.xml|README)',
            nginx.Key('deny', 'all')
            ),
        nginx.Location('/',
            nginx.Key('rewrite', '^/.well-known/host-meta /public.php?service=host-meta last'),
            nginx.Key('rewrite', '^/.well-known/host-meta.json /public.php?service=host-meta-json last'),
            nginx.Key('rewrite', '^/.well-known/carddav /remote.php/carddav/ redirect'),
            nginx.Key('rewrite', '^/.well-known/caldav /remote.php/caldav/ redirect'),
            nginx.Key('rewrite', '^(/core/doc/[^\/]+/)$ $1/index.html'),
            nginx.Key('try_files', '$uri $uri/ index.php')
            ),
        nginx.Location('~ \.php(?:$|/)',
            nginx.Key('fastcgi_split_path_info', '^(.+\.php)(/.+)$'),
            nginx.Key('include', 'fastcgi_params'),
            nginx.Key('fastcgi_param', 'SCRIPT_FILENAME $document_root$fastcgi_script_name'),
            nginx.Key('fastcgi_param', 'PATH_INFO $fastcgi_path_info'),
            nginx.Key('fastcgi_pass', 'unix:/run/php-fpm/php-fpm.sock'),
            nginx.Key('fastcgi_read_timeout', '900s')
            ),
        nginx.Location('~* \.(?:jpg|jpeg|gif|bmp|ico|png|css|js|swf)$',
            nginx.Key('expires', '30d'),
            nginx.Key('access_log', 'off')
            )
        ]

    def pre_install(self, vars):
        pass

    def post_install(self, vars, dbpasswd=""):
        secret_key = random_string()
        
        # If there is a custom path for the data directory, add to open_basedir
        uid, gid = users.get_system("http").uid, groups.get_system("http").gid
        if not self.data_path.startswith(self.path):
            os.makedirs(os.path.join(self.path, "data"))
            os.chown(os.path.join(self.path, "data"), uid, gid)
            php.open_basedir('add', self.data_path)

        # Create ownCloud automatic configuration file
        with open(os.path.join(self.path, 'config', 'autoconfig.php'), 'w') as f:
            f.write(
                '<?php\n'
                '   $AUTOCONFIG = array(\n'
                '   "adminlogin" => "admin",\n'
                '   "adminpass" => "'+dbpasswd+'",\n'
                '   "dbtype" => "mysql",\n'
                '   "dbname" => "'+self.db.id+'",\n'
                '   "dbuser" => "'+self.db.id+'",\n'
                '   "dbpass" => "'+dbpasswd+'",\n'
                '   "dbhost" => "localhost",\n'
                '   "dbtableprefix" => "",\n'
                '   "directory" => "'+self.data_path+'",\n'
                '   );\n'
                '?>\n'
                )
        os.chown(os.path.join(self.path, 'config', 'autoconfig.php'), uid, gid)

        # Make sure that the correct PHP settings are enabled
        php.enable_mod('mysql', 'pdo_mysql', 'zip', 'gd', 'ldap',
            'iconv', 'openssl', 'xcache', 'posix')
        
        # Make sure xcache has the correct settings, otherwise ownCloud breaks
        with open('/etc/php/conf.d/xcache.ini', 'w') as f:
            f.writelines(['extension=xcache.so\n',
                'xcache.size=64M\n',
                'xcache.var_size=64M\n',
                'xcache.admin.enable_auth = Off\n',
                'xcache.admin.user = "admin"\n',
                'xcache.admin.pass = "'+secret_key[8:24]+'"\n'])
        
        php.change_setting("always_populate_raw_post_data", "-1")
        mydir = os.getcwd()
        os.chdir(self.path)
        s = shell("sudo -u http php index.php")
        if s["code"] != 0:
            raise Exception("ownCloud database population failed")
        s = shell("sudo -u http php occ app:enable user_ldap")
        if s["code"] != 0:
            raise Exception("ownCloud LDAP configuration failed")
        os.chdir(mydir)
        
        ldap_sql = ("REPLACE INTO appconfig (appid, configkey, configvalue) VALUES"
            "('user_ldap', 'ldap_uuid_attribute', 'auto'),"
            "('user_ldap', 'ldap_host', 'localhost'),"
            "('user_ldap', 'ldap_port', '389'),"
            "('user_ldap', 'ldap_base', 'dc=arkos-servers,dc=org'),"
            "('user_ldap', 'ldap_base_users', 'dc=arkos-servers,dc=org'),"
            "('user_ldap', 'ldap_base_groups', 'dc=arkos-servers,dc=org'),"
            "('user_ldap', 'ldap_tls', '0'),"
            "('user_ldap', 'ldap_display_name', 'cn'),"
            "('user_ldap', 'ldap_userlist_filter', 'objectClass=mailAccount'),"
            "('user_ldap', 'ldap_group_filter', 'objectClass=posixGroup'),"
            "('user_ldap', 'ldap_group_display_name', 'cn'),"
            "('user_ldap', 'ldap_group_member_assoc_attribute', 'uniqueMember'),"
            "('user_ldap', 'ldap_login_filter', '(&(|(objectclass=posixAccount))(|(uid=%uid)))'),"
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
        # TODO set authed user name
        self.db.execute("INSERT INTO group_user VALUES ('admin','testuser');", commit=True)

    def pre_remove(self):
        datadir = ''
        if os.path.exists(os.path.join(self.path, 'config', 'config.php')):
            with open(os.path.join(self.path, 'config', 'config.php'), 'r') as f:
                for line in f.readlines():
                    if 'datadirectory' in line:
                        data = line.split("'")[1::2]
                        datadir = data[1]
        elif os.path.exists(os.path.join(self.path, 'config', 'autoconfig.php')):
            with open(os.path.join(self.path, 'config', 'autoconfig.php'), 'r') as f:
                for line in f.readlines():
                    if 'directory' in line:
                        data = line.split('"')[1::2]
                        datadir = data[1]
        if datadir:
            shutil.rmtree(datadir)
            php.open_basedir('del', datadir)

    def post_remove(self):
        pass

    def enable_ssl(self, cfile, kfile):
        # First, force SSL in ownCloud's config file
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
        if found == False:
            for x in enumerate(oc):
                if '"dbhost" =>' in x[1]:
                    oc.insert(x[0] + 1, '"forcessl" => true,\n')
        with open(px, 'w') as f:
            f.writelines(oc)

        # Next, update the ca-certificates thing to include our cert
        # (if necessary)
        if not os.path.exists('/usr/share/ca-certificates'):
            try:
                os.makedirs('/usr/share/ca-certificates')
            except OSError, e:
                if e.errno == errno.EEXIST and os.path.isdir('/usr/share/ca-certificates'):
                    pass
                else:
                    raise
        shutil.copy(cfile, '/usr/share/ca-certificates/')
        fname = cfile.rstrip('/').split('/')[-1]
        with open('/etc/ca-certificates.conf', 'r') as f:
            ic = f.readlines()
        oc = []
        for l in ic:
            if l != fname+'\n':
                oc.append(l)
        oc.append(fname+'\n')
        with open('/etc/ca-certificates.conf', 'w') as f:
            f.writelines(oc)
        shell('update-ca-certificates')

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
        if found == False:
            for x in enumerate(oc):
                if '"dbhost" =>' in x[1]:
                    oc.insert(x[0] + 1, '"forcessl" => false,\n')
        with open(px, 'w') as f:
            f.writelines(oc)
    
    def site_edited(self):
        # Remove the existing trusted_sites array then add a new one based on the new addr
        if not os.path.exists(os.path.join(self.path, 'config', 'config.php')):
            path = os.path.join(self.path, 'config', 'config.php')
        with open(path, "r") as f:
            data = f.read()
        while re.search("\n(\s*('|\")trusted_domains.*?\).*?\n)", data, re.DOTALL):
            data = data.replace(re.search("\n(\s*('|\")trusted_domains.*?\).*?\n)", data, re.DOTALL).group(1), "")
        data = data.split("\n")
        with open(path, "w") as f:
            for x in data:
                if not x.endswith("\n"): 
                    x += "\n"
                if x.startswith(");"):
                    f.write("  'trusted_domains' => array('localhost','%s'),\n"%self.addr)
                f.write(x)
        
