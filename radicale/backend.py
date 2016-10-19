import glob
import nginx
import os
import stat
import sys

from arkos import applications, websites
from arkos.languages import python
from arkos.system import users, groups, services


default_config = (
    '[server]\n'
    '# CalDAV server hostnames separated by a comma\n'
    '# IPv4 syntax: address:port\n'
    '# IPv6 syntax: [address]:port\n'
    '# For example: 0.0.0.0:9999, [::]:9999\n'
    '# IPv6 adresses are configured to only allow IPv6 connections\n'
    'hosts = 0.0.0.0:5232\n'
    '# Daemon flag\n'
    'daemon = False\n'
    '# File storing the PID in daemon mode\n'
    'pid =\n'
    '# SSL flag, enable HTTPS protocol\n'
    'ssl = False\n'
    '# SSL certificate path\n'
    'certificate = /etc/apache2/ssl/server.crt\n'
    '# SSL private key\n'
    'key = /etc/apache2/ssl/server.key\n'
    '# Reverse DNS to resolve client address in logs\n'
    'dns_lookup = True\n'
    '# Root URL of Radicale (starting and ending with a slash)\n'
    'base_prefix = /\n'
    '# Message displayed in the client when a password is needed\n'
    'realm = Radicale - Password Required lol\n'
    '\n'
    '\n'
    '[encoding]\n'
    '# Encoding for responding requests\n'
    'request = utf-8\n'
    '# Encoding for storing local collections\n'
    'stock = utf-8\n'
    '\n'
    '\n'
    '[auth]\n'
    '# Authentication method\n'
    '# Value: None | htpasswd | IMAP | LDAP | PAM | courier | http\n'
    'type = LDAP\n'
    '\n'
    '# Usernames used for public collections, separated by a comma\n'
    'public_users = public\n'
    '# Usernames used for private collections, separated by a comma\n'
    'private_users = private\n'
    '# Htpasswd filename\n'
    'htpasswd_filename = /etc/radicale/users\n'
    '# Htpasswd encryption method\n'
    '# Value: plain | sha1 | crypt\n'
    'htpasswd_encryption = crypt\n'
    '\n'
    '# LDAP server URL, with protocol and port\n'
    'ldap_url = ldap://localhost:389/\n'
    '# LDAP base path\n'
    'ldap_base = ou=users,dc=arkos-servers,dc=org\n'
    '# LDAP login attribute\n'
    'ldap_attribute = uid\n'
    '# LDAP filter string\n'
    '# placed as X in a query of the form (&(...)X)\n'
    '# example: (objectCategory=Person)(objectClass=User)'
    '(memberOf=cn=calenderusers,ou=users,dc=example,dc=org)\n'
    '# leave empty if no additional filter is needed\n'
    'ldap_filter =\n'
    '# LDAP dn for initial login, '
    'used if LDAP server does not allow anonymous searches\n'
    '# Leave empty if searches are anonymous\n'
    'ldap_binddn =\n'
    '# LDAP password for initial login, used with ldap_binddn\n'
    'ldap_password =\n'
    '# LDAP scope of the search\n'
    'ldap_scope = OneLevel\n'
    '\n'
    '# IMAP Configuration\n'
    'imap_hostname = localhost\n'
    'imap_port = 143\n'
    'imap_ssl = False\n'
    '\n'
    '# PAM group user should be member of\n'
    'pam_group_membership =\n'
    '\n'
    '# Path to the Courier Authdaemon socket\n'
    'courier_socket =\n'
    '\n'
    '# HTTP authentication request URL endpoint\n'
    'http_url =\n'
    '# POST parameter to use for username\n'
    'http_user_parameter =\n'
    '# POST parameter to use for password\n'
    'http_password_parameter =\n'
    '\n'
    '\n'
    '[rights]\n'
    '# Rights management method\n'
    '# Value: None | owner_only | owner_write | from_file\n'
    'type = owner_only\n'
    '\n'
    '# File for rights management from_file\n'
    'file = ~/.config/radicale/rights\n'
    '\n'
    '\n'
    '[storage]\n'
    '# Storage backend\n'
    '# Value: filesystem | database\n'
    'type = filesystem\n'
    '\n'
    '# Folder for storing local collections, created if not present\n'
    'filesystem_folder = ~/.config/radicale/collections\n'
    '\n'
    '# Database URL for SQLAlchemy\n'
    '# dialect+driver://user:password@host/dbname[?key=value..]\n'
    '# For example: sqlite:///var/db/radicale.db, '
    'postgresql://user:password@localhost/radicale\n'
    '# See http://docs.sqlalchemy.org/en/rel_0_8/core/'
    'engines.html#sqlalchemy.create_engine\n'
    'database_url =\n'
    '\n'
    '\n'
    '[logging]\n'
    '# Logging configuration file\n'
    '# If no config is given, '
    'simple information is printed on the standard output\n'
    '# For more information about the syntax of the configuration file, see:\n'
    '# http://docs.python.org/library/logging.config.html\n'
    'config = /etc/radicale/logging\n'
    '# Set the default logging level to debug\n'
    'debug = False\n'
    '# Store all environment variables (including those set in the shell)\n'
    'full_environment = False\n'
    '\n'
    '\n'
    '# Additional HTTP headers\n'
    '#[headers]\n'
    '#Access-Control-Allow-Origin = *\n'
    )


class Calendar:
    def __init__(self, id, user):
        self.id = id
        self.user = user

    def add(self):
        add(self.id, self.user, ".ics")

    def remove(self):
        os.unlink(os.path.join('/home/radicale/.config/radicale/collections',
                               self.user, self.id+'.ics'))

    @property
    def serialized(self):
        return {
          "id": self.user+"_"+self.id,
          "name": self.id,
          "user": self.user,
          "filename": self.id+".ics",
          "url": "{0}/{1}/{2}/".format(my_url(), self.user, self.id+".ics"),
          "is_ready": True
        }


class AddressBook:
    def __init__(self, id, user):
        self.id = id
        self.user = user

    def add(self):
        add(self.id, self.user, ".vcf")

    def remove(self):
        os.unlink(os.path.join('/home/radicale/.config/radicale/collections',
                               self.user, self.id+'.vcf'))

    @property
    def serialized(self):
        return {
          "id": self.user+"_"+self.id,
          "name": self.id,
          "user": self.user,
          "filename": self.id+".vcf",
          "url": "{0}/{1}/{2}/".format(my_url(), self.user, self.id+".vcf"),
          "is_ready": True
        }


def add(id, user, file_type):
    uid, gid = users.get_system("radicale").uid,\
        groups.get_system("radicale").gid
    try:
        os.makedirs('/home/radicale/.config/radicale/collections/{0}'
                    .format(user))
        os.chown('/home/radicale/.config/radicale/collections', uid, gid)
    except os.error:
        pass
    with open(os.path.join('/home/radicale/.config/radicale/collections',
                           user, id+file_type), 'w') as f:
        f.write("")
    os.chown(os.path.join('/home/radicale/.config/radicale/collections',
                          user, id+file_type), uid, gid)


def get_cal(id=None, name=None, user=None):
    cals = []
    for x in glob.glob('/home/radicale/.config/radicale/collections/*/*.ics'):
        n = os.path.basename(x).split(".ics")[0]
        u = x.split("/")[-2]
        cal = Calendar(id=n, user=u)
        if id and id == (cal.user+"_"+cal.id):
            return cal
        elif name and name == cal.id:
            return cal
        elif (user and user == cal.user) or not user:
            cals.append(cal)
    return cals if not any([id, name, user]) else None


def get_book(id=None, name=None, user=None):
    bks = []
    for x in glob.glob('/home/radicale/.config/radicale/collections/*/*.vcf'):
        n = os.path.basename(x).split(".vcf")[0]
        u = x.split("/")[-2]
        bk = AddressBook(id=n, user=u)
        if id and id == (bk.user+"_"+bk.id):
            return bk
        elif name and name == bk.name:
            return bk
        elif (user and user == bk.user) or not user:
            bks.append(bk)
    return bks if not any([id, name, user]) else None


def my_url():
    url = "http"
    w = websites.get('radicale')
    if not w:
        return ""
    url += "s://" if w.cert else "://"
    url += w.domain
    url += (":"+str(w.port)) if w.port not in [80, 443] else ""
    return url


def is_installed():
    """ Verify the different components of the server setup """
    if not os.path.exists('/etc/radicale/config') \
            or not os.path.isdir('/usr/lib/radicale') \
            or not os.path.exists('/etc/radicale/radicale.wsgi') \
            or not websites.get('radicale'):
        return False
    else:
        return True


def is_running():
    s = services.get("radicale")
    if s:
        return s.state == "running"
    return False


def setup(addr, port):
    # Make sure Radicale is installed and ready
    if not python.is_installed('Radicale'):
        python.install('radicale')
    # due to packaging bugs, make extra sure perms are readable
    pver = "{0}.{1}".format(sys.version_info.major, sys.version_info.minor)
    raddir = '/usr/lib/python{0}/site-packages/radicale'.format(pver)
    st = os.stat(raddir)
    for r, d, f in os.walk(raddir):
        for x in d:
            os.chmod(os.path.join(r, x),
                     st.st_mode | stat.S_IROTH | stat.S_IRGRP)
        for x in f:
            os.chmod(os.path.join(r, x),
                     st.st_mode | stat.S_IROTH | stat.S_IRGRP)
    if not os.path.exists('/etc/radicale/config'):
        if not os.path.isdir('/etc/radicale'):
            os.mkdir('/etc/radicale')
        with open('/etc/radicale/config', 'w') as f:
            f.write(default_config)
    if not os.path.isdir('/usr/lib/radicale'):
        os.mkdir('/usr/lib/radicale')
    # Add the site process
    u = users.SystemUser("radicale")
    u.add()
    g = groups.SystemGroup("radicale", users=["radicale"])
    g.add()
    wsgi_file = 'import radicale\n'
    wsgi_file += 'radicale.log.start()\n'
    wsgi_file += 'application = radicale.Application()\n'
    with open('/etc/radicale/radicale.wsgi', 'w') as f:
        f.write(wsgi_file)
    os.chmod('/etc/radicale/radicale.wsgi', 0o766)
    cfg = {
        'directory': '/etc/radicale',
        'user': 'radicale',
        'command': 'uwsgi -s /tmp/radicale.sock -C '
                   '--plugin python2 --wsgi-file radicale.wsgi',
        'stdout_logfile': '/var/log/radicale.log',
        'stderr_logfile': '/var/log/radicale.log'
    }
    s = services.Service("radicale", "supervisor", cfg=cfg)
    s.add()
    block = [
        nginx.Location(
            '/',
            nginx.Key('include', 'uwsgi_params'),
            nginx.Key('uwsgi_pass', 'unix:///tmp/radicale.sock'),
        )
    ]
    s = websites.get("radicale")
    if s:
        s.remove()
    a = applications.get('radicale')
    s = websites.ReverseProxy(
            app=a, id="radicale", domain=addr, port=port,
            base_path="/usr/lib/radicale", block=block)
    s.install()
