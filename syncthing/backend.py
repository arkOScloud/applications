import lxml.etree as ET
import os
import shutil
import time

from arkos import signals
from arkos.system import users, services
from arkos.utilities import api


def on_load(app):
    if app.id != "syncthing":
        return
    if not users.get_system("syncthing"):
        u = users.SystemUser('syncthing')
        u.add()
    u = users.get_system('syncthing')
    if not os.path.exists("/home/syncthing"):
        os.makedirs("/home/syncthing")
        os.chown("/home/syncthing", u.uid, 0o100)
    config_path = "/home/syncthing/.config/syncthing/config.xml"
    s = services.get("syncthing@syncthing")
    if not os.path.exists(config_path):
        s.restart()
        count = 0
        while count < 5:
            if not os.path.exists(config_path):
                time.sleep(5)
                count += 1
            else:
                break
        if not os.path.exists(config_path):
            raise Exception("Syncthing taking too long to generate config,"
                            " try again later")


def get_api_key():
    with open("/home/syncthing/.config/syncthing/config.xml", "r") as f:
        data = f.read()
    parser = ET.XMLParser(remove_blank_text=True)
    xml = ET.fromstring(data, parser) if data else None
    apikey = xml.find("./gui/apikey").text
    return apikey


def pull_config():
    api_key = get_api_key()
    config = api("http://localhost:8384/rest/system/config",
                 headers=[("X-API-Key", api_key)], crit=True)
    return config


def save_config(config):
    api_key = get_api_key()
    api("http://localhost:8384/rest/system/config", config, "POST",
        returns="raw", headers=[("X-API-Key", api_key)], crit=True)
    s = services.get("syncthing@syncthing")
    s.restart()
    return config


def get_myid():
    api_key = get_api_key()
    config = api("http://localhost:8384/rest/system/status",
                 headers=[("X-API-Key", api_key)], crit=True)
    return config.get("myID", None)


def add_repo(name, dirname, ro, perms, vers, rsc, nids=[]):
    config = pull_config()
    folder = {"id": name, "path": dir,
              "readOnly": ro, "ignorePerms": perms, "order": "random",
              "hashers": 0, "lenientMTimes": False,
              "copiers": 1, "autoNormalize": False,
              "rescanIntervalS": rsc or 60, "devices": [],
              "versioning": {"params": {}, "type": ""}}
    for x in nids:
        folder["devices"].append({"deviceID": x})
    if vers:
        folder["versioning"]["type"] = "simple"
        folder["versioning"]["params"] = {"key": "keep", "val": vers}
    config["folders"].append(folder)
    if dirname.startswith('~'):
        dirname = os.path.join(os.path.expanduser("~syncthing"),
                               dirname.lstrip("~/"))
    if not os.path.exists(dir):
        os.makedirs(dir)
    uid = users.get_system('syncthing').uid
    for r, d, f in os.walk(dir):
        for x in d:
            os.chown(os.path.join(r, x), uid, -1)
        for x in f:
            os.chown(os.path.join(r, x), uid, -1)
    save_config(config)
    folder["is_ready"] = True
    return folder


def edit_repo(name, dirname, ro, perms, vers, rsc, nids=[]):
    config = pull_config()
    folder = next((fdr for fdr in config["folders"]
                   if fdr["id"] == name), None)
    config["folders"].remove(folder)
    folder["path"] = dirname
    folder["ro"] = ro
    folder["ignorePerms"] = perms
    folder["rescanIntervalS"] = rsc or 60
    folder["devices"] = []
    folder["versioning"] = {"params": {}, "type": ""}
    for x in nids:
        folder["devices"].append({"deviceID": x})
        x.find("versioning")
    if vers:
        folder["versioning"]["type"] = "simple"
        folder["versioning"]["params"] = {"key": "keep", "val": vers}
    config["folders"].append(folder)
    save_config(config)
    folder["is_ready"] = True
    return folder


def del_repo(name, rmfol=False):
    config = pull_config()
    folder = next((fdr for fdr in config["folders"]
                   if fdr["id"] == name), None)
    config["folders"].remove(folder)
    save_config(config)
    if rmfol:
        shutil.rmtree(folder["path"])


def get_repos(id=None):
    config = pull_config()
    for x in config["folders"]:
        x["is_ready"] = True
    if id:
        return next((fdr for fdr in config["folders"]
                     if fdr["id"] == id), None)
    return config["folders"]


def add_node(name, id, addr):
    config = pull_config()
    device = {"deviceID": id, "name": name,
              "addresses": addr, "introducer": False,
              "certName": "", "compression": "metadata"}
    config["devices"].append(device)
    save_config(config)
    device["id"] = device["name"]
    device["is_ready"] = True
    return device


def edit_node(name, newname, addr):
    config = pull_config()
    device = next((dev for dev in config["devices"]
                   if dev["name"] == name), None)
    config["devices"].remove(device)
    device["name"] = newname
    device["addressing"] = addr
    config["devices"].append(device)
    save_config(config)
    device["id"] = device["name"]
    device["is_ready"] = True
    return device


def del_node(name):
    config = pull_config()
    device = next((dev for dev in config["devices"]
                   if dev["name"] == name), None)
    config["devices"].remove(device)
    save_config(config)


def get_nodes(id=None):
    config = pull_config()
    for x in config["devices"]:
        x["id"] = x["deviceID"]
        x["is_main_device"] = x["deviceID"] == get_myid()
        x["is_ready"] = True
    if id:
        return next((dev for dev in config["devices"]
                     if dev["deviceID"] == id), None)
    return config["devices"]


signals.add("syncthing", "apps", "post_load", on_load)
