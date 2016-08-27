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

    def put(self, app_id=None):
        print("put duniter")

    def delete(self, app_id=None):
        print("delete duniter")

duniterservers = DuniterAPI.as_view('duniter_api')
