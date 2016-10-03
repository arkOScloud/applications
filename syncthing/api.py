from flask import Response, abort, jsonify, request
from flask.views import MethodView

import backend


class SyncthingFoldersAPI(MethodView):
    def get(self, id_=None):
        folders = backend.get_repos(id_)
        if id_ and not folders:
            abort(404)
        if type(folders) == list:
            return jsonify(folders=folders)
        else:
            return jsonify(folder=folders)

    def post(self):
        data = request.get_json()["folder"]
        folder = backend.add_repo(data["id"], data["path"], data["read_only"],
            data["ignore_perms"], data["keep_versions"] if data["versioning"] else False,
            data["rescan_interval_s"], data["devices"])
        return jsonify(folder=folder)

    def put(self, id_=None):
        if not id_:
            abort(422)
        data = request.get_json()["folder"]
        folder = backend.edit_repo(data["id"], data["path"], data["read_only"],
            data["ignore_perms"], data["keep_versions"] if data["versioning"] else False,
            data["rescan_interval_s"], data["devices"])
        return jsonify(folder=folder)

    def delete(self, id_=None):
        if not id_:
            abort(422)
        backend.del_repo(id_)
        return Response(204)


class SyncthingDevicesAPI(MethodView):
    def get(self, id_=None):
        devices = backend.get_nodes(id_)
        if id_ and not devices:
            abort(404)
        if type(devices) == list:
            return jsonify(devices=devices)
        else:
            return jsonify(device=devices)

    def post(self):
        data = request.get_json()["device"]
        device = backend.add_device(data["name"], data["device_id"],
            list(data["addresses"]) if not type(data["addresses"]) == list else data["addresses"])
        return jsonify(device=device)

    def put(self, id_=None):
        if not id_:
            abort(422)
        data = request.get_json()["device"]
        device = backend.edit_node(data)
        return jsonify(device=device)

    def delete(self, id_):
        if not id_:
            abort(422)
        backend.del_node(id_)
        return Response(204)


def config():
    if request.method == "GET":
        return jsonify(myid=backend.my_id, config=backend.pull_config())
    else:
        config = request.get_json()["config"]
        return jsonify(myid=backend.my_id, config=backend.save_config(config))


folders = SyncthingFoldersAPI.as_view('syncfolders_api')
devices = SyncthingDevicesAPI.as_view('syncdevices_api')
