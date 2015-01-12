import nginx
import os

from arkos.languages import ruby
from arkos.sites import Site
from arkos.utilities import shell, random_string
from arkos.system import users, groups


class Jekyll(Site):
    addtoblock = []

    def pre_install(self, vars):
        ruby.install_gem('jekyll', 'rdiscount')

    def post_install(self, vars, dbpasswd=""):
        # Make sure the webapps config points to the _site directory and generate it.
        c = nginx.loadf(os.path.join('/etc/nginx/sites-available', self.name))
        for x in c.servers:
            if x.filter('Key', 'root'):
                x.filter('Key', 'root')[0].value = os.path.join(self.path, '_site')
        nginx.dumpf(c, os.path.join('/etc/nginx/sites-available', self.name))
        s = shell('jekyll build --source '+self.path+' --destination '+os.path.join(self.path, '_site'))
        if s["code"] != 0:
            raise Exception('Jekyll failed to build: %s'%str(s["stderr"]))
        uid, gid = users.get_system("http").uid, groups.get_system("http").gid
        for r, d, f in os.walk(self.path):
            for x in d:
                os.chmod(os.path.join(root, x), 0755)
                os.chown(os.path.join(root, x), uid, gid)
            for x in f:
                os.chmod(os.path.join(root, x), 0644)
                os.chown(os.path.join(root, x), uid, gid)

        # Return an explicatory message.
        return 'Jekyll has been setup, with a sample site at '+self.path+'. Modify these files as you like. To learn how to use Jekyll, visit http://jekyllrb.com/docs/usage. After making changes, click the Configure button next to the site, then "Regenerate Site" to bring your changes live.'

    def pre_remove(self):
        pass

    def post_remove(self):
        pass

    def ssl_enable(self, cfile, kfile):
        pass

    def ssl_disable(self):
        pass

    def regenerate_site(self):
        path = os.path.join(self.path)
        if not path.endswith("_site"):
            path = os.path.join(path, "_site")
        s = shell('jekyll build --source '+self.path.rstrip('_site')+' --destination '+path, stderr=True)
        if s["code"] != 0:
            raise Exception('Jekyll failed to build: %s'%str(s["stderr"]))
        uid, gid = users.get_system("http").uid, groups.get_system("http").gid
        for r, d, f in os.walk(self.path):
            for x in d:
                os.chmod(os.path.join(root, x), 0755)
                os.chown(os.path.join(root, x), uid, gid)
            for x in f:
                os.chmod(os.path.join(root, x), 0644)
                os.chown(os.path.join(root, x), uid, gid)
