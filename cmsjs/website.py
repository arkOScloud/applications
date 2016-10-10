import nginx
import os

from arkos.system import users, groups
from arkos.websites import Site


class cmsjs(Site):
    addtoblock = [
        nginx.Location(
            '/',
            nginx.Key('try_files', '$uri $uri/ /index.html'),
            nginx.Key('autoindex', 'on'),
        ),
    ]

    def pre_install(self, extra_vars):
        pass

    def post_install(self, extra_vars, dbpasswd=""):
        # Write a standard CMS.js config file
        with open(os.path.join(self.path, 'js/config.js'), 'r') as f:
            d = f.read()
        d = d.replace("siteName: 'My Site'", "siteName: 'CMS.js on arkOS'")
        d = d.replace("siteTagline: 'Your site tagline'",
                      "siteTagline: 'Configure js/config.js to your liking'")
        d = d.replace("mode: 'Github'", "mode: 'Server'")

        with open(os.path.join(self.path, 'js/config.js'), 'w') as f:
            f.write(d)

        # Give access to httpd
        uid, gid = users.get_system("http").uid, groups.get_system("http").gid
        for r, d, f in os.walk(self.path):
            for x in d:
                os.chown(os.path.join(r, x), uid, gid)
            for x in f:
                os.chown(os.path.join(r, x), uid, gid)

    def pre_remove(self):
        pass

    def post_remove(self):
        pass

    def enable_ssl(self, cfile, kfile):
        pass

    def disable_ssl(self):
        pass

    def update(self, pkg, ver):
        # TODO: pull from Git at appropriate intervals
        pass
