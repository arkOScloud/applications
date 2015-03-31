import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from kraken import auth

backend = Blueprint("radicale", __name__)


class CalendarsAPI(MethodView):
    @auth.required()
    def get(self, id):
        calendars = radicale.get_cal(id)
        if id and not calendars:
            abort(404)
        if type(calendars) == list:
            return jsonify(calendars=[x.as_dict() for x in calendars])
        else:
            return jsonify(calendar=calendars.as_dict())
    
    @auth.required()
    def post(self):
        data = json.loads(request.data)["calendar"]
        addrbk = radicale.Calendar(id=data["name"], user=data["user"])
        addrbk.add()
        return jsonify(message="Calendar created successfully", address_book=addrbk.as_dict())
    
    @auth.required()
    def delete(self, id):
        calendar = radicale.get_cal(id)
        if not id or not calendar:
            abort(404)
        calendar.remove()
        return Response(status=204)


class AddressBooksAPI(MethodView):
    @auth.required()
    def get(self, id):
        addrbks = radicale.get_book(id)
        if id and not addrbks:
            abort(404)
        if type(addrbks) == list:
            return jsonify(address_books=[x.as_dict() for x in addrbks])
        else:
            return jsonify(address_book=addrbks.as_dict())
    
    @auth.required()
    def post(self):
        data = json.loads(request.data)["address_book"]
        addrbk = radicale.AddressBook(id=data["name"], user=data["user"])
        addrbk.add()
        return jsonify(message="Address book created successfully", address_book=addrbk.as_dict())
    
    @auth.required()
    def delete(self, id):
        addrbk = radicale.get_book(id)
        if not id or not addrbk:
            abort(404)
        addrbk.remove()
        return Response(status=204)


@backend.route('/calendars_contacts/setup', methods=['GET', 'POST'])
@auth.required()
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


calendars_view = CalendarsAPI.as_view('calendars_api')
backend.add_url_rule('/calendars', defaults={'id': None}, 
    view_func=calendars_view, methods=['GET',])
backend.add_url_rule('/calendars', view_func=calendars_view, methods=['POST',])
backend.add_url_rule('/calendars/<string:id>', view_func=calendars_view, 
    methods=['GET', 'DELETE'])

addrbk_view = AddressBooksAPI.as_view('addrbk_api')
backend.add_url_rule('/address_books', defaults={'id': None}, 
    view_func=addrbk_view, methods=['GET',])
backend.add_url_rule('/address_books', view_func=addrbk_view, methods=['POST',])
backend.add_url_rule('/address_books/<string:id>', view_func=addrbk_view, 
    methods=['GET', 'DELETE'])
