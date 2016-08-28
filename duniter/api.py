from flask.views import MethodView

'''
Created on May 17, 2015

@author: Folatt RPG
'''


class DuniterAPI(MethodView):

    def get(self):
        print("get duniter")

    def post(self):
        print("post duniter")

    def put(self, id_=None):
        print("put duniter")

    def delete(self, id_=None):
        print("delete duniter")

duniterservers = DuniterAPI.as_view('duniter_api')
