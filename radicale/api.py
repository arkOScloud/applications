import json

from flask import Response, abort, jsonify, request
from flask.views import MethodView


class CalendarsAPI(MethodView):
    def get(self, id=None):
        calendars = radicale.get_cal(id)
        if id and not calendars:
            abort(404)
        if type(calendars) == list:
            return jsonify(calendars=[x.as_dict() for x in calendars])
        else:
            return jsonify(calendar=calendars.as_dict())
    
    def post(self):
        data = json.loads(request.data)["calendar"]
        addrbk = radicale.Calendar(id=data["name"], user=data["user"])
        addrbk.add()
        return jsonify(message="Calendar created successfully", address_book=addrbk.as_dict())
    
    def delete(self, id):
        calendar = radicale.get_cal(id)
        if not id or not calendar:
            abort(404)
        calendar.remove()
        return Response(status=204)


class AddressBooksAPI(MethodView):
    def get(self, id=None):
        addrbks = radicale.get_book(id)
        if id and not addrbks:
            abort(404)
        if type(addrbks) == list:
            return jsonify(address_books=[x.as_dict() for x in addrbks])
        else:
            return jsonify(address_book=addrbks.as_dict())
    
    def post(self):
        data = json.loads(request.data)["address_book"]
        addrbk = radicale.AddressBook(id=data["name"], user=data["user"])
        addrbk.add()
        return jsonify(message="Address book created successfully", address_book=addrbk.as_dict())
    
    def delete(self, id):
        addrbk = radicale.get_book(id)
        if not id or not addrbk:
            abort(404)
        addrbk.remove()
        return Response(status=204)


def setup():
    if request.method == "GET":
        return jsonify(running=radicale.is_running(), 
            installed=radicale.is_installed(),
            url=radicale.my_url())
    else:
        data = json.loads(request.data)["config"]
        radicale.setup(data["addr"], data["port"])
        return jsonify(running=radicale.is_running(), 
            installed=radicale.is_installed(),
            url=radicale.my_url())


calendars = CalendarsAPI.as_view('calendars_api')
address_books = AddressBooksAPI.as_view('addrbk_api')
