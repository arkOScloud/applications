from arkos import signals, logger
from arkos.languages import nodejs
from arkos.utilities import shell, errors
from arkos.system import users, services

'''
Created on May 24, 2015

@author: Folatt RPG
'''


def on_load(app):
    if app.id != "duniter":
        pass

    if users.get_system("duniter") == None:
        users.SystemUser("duniter").add()
    if not nodejs.is_installed("duniter"):
        logger.info("Installing duniter, this can take a long time..")
        nodejs.install('duniter', as_global=True)

    cfg = {
        "salt": "'test1'",
        "passwd": "'test1'",
        "noupnp": None,
        "ipv4": "127.0.0.1",
        "port": "8999",
        "remotep": "8999"
    }

    configDuniter(cfg)
    # runDuniter(app)


def runDuniter(app):
    """ Starts Duniter """
    cfg = {
        'directory': '/home/duniter',
        'user': 'duniter',
        'command': '/usr/bin/duniter start',
        'environment': 'HOME="/home/duniter",USER="duniter",'
        'PATH="/var/lib/npm/.npm-global/bin:%(ENV_PATH)s"',
        'autostart': 'true',
        'autorestart': 'true',
        'stdout_logfile': '/var/log/supervisor/duniter_out.log',
        'stderr_logfile': '/var/log/supervisor/duniter_err.log'
    }

    s = services.Service(app.id, "supervisor", cfg=cfg)
    s.add()


def configDuniter(config):
    """ Configures Duniter server """
    logger.info("Duniter", "configuring duniter..")

    configString = "".join(" --{0}".format(k+" "+v if v is not None else k)
                           for k, v in config.items())
    s = shell("duniter config {0}".format(configString))
    if s["code"] != 0:
        logger.error("Duniter",
                     "Duniter config failed; log output follows:\n{0}"
                     .format(s["stderr"]))
        raise errors.Error("Duniter config failed, check logs for info")
    s = shell("duniter sync duniter.org 8999")
    if s["code"] != 0:
        logger.error("Duniter",
                     "Duniter sync failed; log output follows:\n{0}"
                     .format(s["stderr"]))
        raise errors.Error("Duniter sync failed, check logs for info")


signals.add("duniter", "apps", "post_load", on_load)
