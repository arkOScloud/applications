import os
import re

from xmpp import backend


def get_ssl_able():
    able = []
    for x in os.listdir("/etc/prosody/conf.d"):
        domain = x.rstrip(".cfg.lua")
        able.append({"type": "app", "id": "xmpp_{0}".format(domain),
                     "aid": "xmpp", "sid": domain,
                     "name": "Chat Server ({0})".format(domain)})
    return able


def get_ssl_assigned():
    assigns = []
    for x in os.listdir("/etc/prosody/conf.d"):
        domain = x.rstrip(".cfg.lua")
        with open(os.path.join("/etc/prosody/conf.d", x), "r") as f:
            data = f.read()
            if not re.findall("ssl", data):
                continue
            path = re.search('certificate = "(.*)";', data).group(1)
            cert = os.path.splitext(os.path.basename(path))[0]
            assigns.append((cert,
                            {"type": "app", "id": "xmpp_{0}".format(domain),
                             "aid": "xmpp", "sid": domain,
                             "name": "Chat Server ({0})".format(domain)}))
    return assigns


def ssl_enable(cert, id_):
    return backend.add_ssl(id_, cert.cert_path, cert.key_path)


def ssl_disable(id_):
    backend.remove_ssl(id_)
