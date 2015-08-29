from flask.views import MethodView
from flask import current_app

'''
Created on May 17, 2015

@author: Folatt RPG
'''

class UcoinServerAPI(MethodView):
    
    def get(self):
        print("get ucoin")

    def post(self):
        print("post ucoin")

    def put(self, id=None):
        print("put ucoin")
    
    def delete(self, id=None):
        print("delete ucoin")

ucoinservers = UcoinServerAPI.as_view('ucoinserver_api')