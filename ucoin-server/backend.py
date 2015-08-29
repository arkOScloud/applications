from arkos import signals, logger
from arkos.languages import nodejs
from arkos.utilities import shell
from arkos.system import users, services

'''
Created on May 24, 2015

@author: Folatt RPG
'''

def on_load(app):
    if app.id != "ucoin-server":
        pass

    if users.get_system("ucoin-server") == None:
        users.SystemUser("ucoin-server").add()
    if not nodejs.is_installed('ucoin'):
        logger.info("Installing ucoin, this can take a long time..")
        nodejs.install('ucoin', as_global=True, opts={"python": "=python2.7"})
    runUCoin(app)

def runUCoin(app):
    cfg = {
        'directory': '/home/ucoin-server',
        'user': 'ucoin-server',
        'command': 'ucoind start',
        'autostart': 'true',
        'autorestart': 'true',
        'stdout_logfile': '/var/log/ucoin.log',
        'stderr_logfile': '/var/log/ucoin.log'
    }

    s = services.Service(app.id, "supervisor", cfg=cfg)
    s.add()

def setup(sync_node, sync_port, ipv4, port, salt, passwd):
    # Runs uCoin.
    logger.info("Look mom! I pressed Finish!")
    s = shell("sudo -u ucoin-server ucoind sync %s %s" % (sync_node, sync_port))
    opts = "--salt %s --passwd %s --noupnp --ipv4 %s --port %s --remotep %s" % (salt, passwd, ipv4, port, port)
    s = shell("sudo -u ucoin-server ucoind config %s" % opts)
    if s["stderr"] != '' or '[ERROR]' in s["stdout"]:
        logger.error("uCoin config of %s failed; log output follows:\n%s"%(" ".join(x for x in mods),s["stderr"]))
        raise Exception("uCoin config failed, check logs for info")

signals.add("ucoin-server", "apps", "post_load", on_load)
