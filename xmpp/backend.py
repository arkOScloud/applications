import os

from arkos import signals
from arkos.system import domains, services


DEFAULT_CONFIG = (
    '\tauthentication = "ldap2"\n'
    '\tldap = {\n'
    '\t\thostname = "localhost",\n'
    '\t\tuser = {\n'
    '\t\t\tbasedn = "ou=users,dc=arkos-servers,dc=org",\n'
    '\t\t\tfilter = "(&(objectClass=posixAccount)(mail=*@%s))",\n'
    '\t\t\tusernamefield = "mail",\n'
    '\t\t\tnamefield = "cn",\n'
    '\t\t},\n'
    '\t\tgroups = {\n'
    '\t\t\tbasedn = "ou=groups,dc=arkos-servers,dc=org",\n'
    '\t\t\tmemberfield = "memberUid",\n'
    '\t\t\tnamefield = "cn",\n'
    '\t\t}\n'
    '\t}\n'
)

def on_load(app):
    # Make sure all system domains are registered with XMPP on system start
    if not app.id == "xmpp":
        return
    reload = False
    doms = domains.get()
    for x in doms:
        if not os.path.exists("/etc/prosody/conf.d/%s.cfg.lua" % x.name):
            add_domain(x, False)
            reload = True
    for x in os.listdir("/etc/prosody/conf.d"):
        if x.rstrip(".cfg.lua") not in [y.name for y in doms]:
            os.unlink(os.path.join("/etc/prosody/conf.d", x))
            reload = True
    if reload:
        services.get("prosody").restart()

def add_domain(domain, reload=True):
    # Adds a system domain for use with XMPP
    with open("/etc/prosody/conf.d/%s.cfg.lua" % domain.name, "w") as f:
        data = ['VirtualHost "%s"\n' % domain.name]
        data.append(DEFAULT_CONFIG % domain.name)
        f.writelines(data)
    if reload:
        services.get("prosody").restart()

def remove_domain(domain, reload=True):
    # Removes a system domain from XMPP use
    if os.path.exists("/etc/prosody/conf.d/%s.cfg.lua" % domain.name):
        os.unlink("/etc/prosody/conf.d/%s.cfg.lua" % domain.name)
    if reload:
        services.get("prosody").restart()

def add_ssl(name, cert, key):
    # Add an SSL certificate to an XMPP domain
    domain = domains.get(name)
    with open("/etc/prosody/conf.d/%s.cfg.lua" % name, "w") as f:
        data = [
            'VirtualHost "%s"\n' % name,
            '\tssl = {\n',
            '\t\tkey = "%s";\n' % cert,
            '\t\tcertificate = "%s";\n' % key,
            '\t}\n'
        ]
        data.append(DEFAULT_CONFIG % domain.name)
        f.writelines(data)
    try:
        services.get("prosody").restart()
    except:
        pass
    return {"type": "app", "id": "xmpp_%s" % name, "aid": "xmpp",
        "sid": name, "name": "Chat Server (%s)" % name}

def remove_ssl(name):
    # Removes SSL from an XMPP domain
    dom = domains.get(name)
    add_domain(dom)


signals.add("xmpp", "apps", "post_load", on_load)
signals.add("xmpp", "domains", "post_add", add_domain)
signals.add("xmpp", "domains", "post_remove", remove_domain)
