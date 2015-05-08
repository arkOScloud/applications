import lxml.etree as ET
import os
import shutil
import time

from arkos import signals
from arkos.system import users, services
from arkos.utilities import api


def on_load(app):
    if app.id != "syncthing":
        pass
    global api_key
    api_key = get_api_key()
    global my_id
    my_id = get_myid()

def get_api_key():
    if not os.path.exists("/home/syncthing/.config/syncthing/config.xml"):
        s = services.get("syncthing@syncthing")
        s.start()
        time.sleep(5)
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

def add_repo(name, dir, ro, perms, vers, rsc, nids=[]):
    config = pull_config()
    folder = {"id": name, "path": dir,
        "readOnly": ro, "ignorePerms": perms, "order": "random",
        "hashers": 0, "lenientMTimes": False, "copiers": 1, "autoNormalize": False,
        "rescanIntervalS": rsc or 60, "devices": [],
        "versioning": {"params": {}, "type": ""}}
    for x in nids:
        folder["devices"].append({"deviceID": x})
    if vers:
        folder["versioning"]["type"] = "simple"
        folder["versioning"]["params"] = {"key": "keep", "val": vers}
    config["folders"].append(folder)
    if dir.startswith('~'):
        dir = os.path.join(os.path.expanduser("~syncthing"), dir.lstrip("~/"))
    if not os.path.exists(dir):
        os.makedirs(dir)
    uid = users.get_system('syncthing').uid
    for r, d, f in os.walk(dir):
        for x in d:
            os.chown(os.path.join(r, x), uid, -1)
        for x in f:
            os.chown(os.path.join(r, x), uid, -1)
    save_config(config)
    return folder

def edit_repo(name, dir, ro, perms, vers, rsc, nids=[]):
    config = pull_config()
    folder = next((fdr for fdr in config["folders"] if fdr["id"] == name), None)
    config["folders"].remove(folder)
    folder["path"] = dir
    folder["ro"] = ro
    folder["ignorePerms"] = perms
    folder["rescanIntervalS"] = rsc or 60
    folder["devices"] = []
    folder["versioning"] = {"params": {}, "type": ""}
    for x in nids:
        folder["devices"].append({"deviceID": x})
    v = e.find("versioning")
    if vers:
        folder["versioning"]["type"] = "simple"
        folder["versioning"]["params"] = {"key": "keep", "val": vers}
    config["folders"].append(folder)
    save_config(config)
    return folder

def del_repo(name, rmfol=False):
    config = pull_config()
    folder = next((fdr for fdr in config["folders"] if fdr["id"] == name), None)
    config["folders"].remove(folder)
    save_config(config)
    if rmfol:
        shutil.rmtree(folder["path"])

def get_repos(id=None):
    config = pull_config()
    if id:
        return next((fdr for fdr in config["folders"] if fdr["id"] == id), None)
    return config["folders"]

def add_node(name, id, addr):
    config = pull_config()
    device = {"deviceID": id, "name": name, "addresses": addr, "introducer": False,
        "certName": "", "compression": "metadata"}
    config["devices"].append(device)
    save_config(config)
    device["id"] = device["name"]
    return device

def edit_node(name, newname, addr):
    config = pull_config()
    device = next((dev for dev in config["devices"] if dev["name"] == name), None)
    config["devices"].remove(device)
    device["name"] = newname
    device["addressing"] = addr
    config["devices"].append(device)
    save_config(config)
    device["id"] = device["name"]
    return device

def del_node(name):
    config = pull_config()
    device = next((dev for dev in config["devices"] if dev["name"] == name), None)
    config["devices"].remove(device)
    save_config(config)

def get_nodes(id=None):
    config = pull_config()
    for x in config["devices"]:
        x["id"] = x["name"]
    if id:
        return next((dev for dev in config["devices"] if dev["id"] == id), None)
    return config["devices"]


signals.add("syncthing", "apps", "post_load", on_load)
