'''
Created on Jul 19, 2016

@author: folatt
'''

from arkos.websites import Site


class KeeWeb(Site):
    addtoblock = []

    def pre_install(self):
        pass

    def post_install(self):
        pass

    def pre_remove(self):
        pass

    def post_remove(self):
        pass

    def enable_ssl(self, cfile, kfile):
        pass

    def disable_ssl(self):
        pass
