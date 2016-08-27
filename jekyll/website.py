import nginx
import os

from arkos.languages import ruby
from arkos.websites import Site
from arkos.utilities import shell
from arkos.system import users, groups


class Jekyll(Site):
    addtoblock = []

    def pre_install(self, vars_):
        ruby.install_gem('jekyll', 'rdiscount')

    def post_install(self, vars_, dbpasswd=""):

        # Make sure the webapps config points to
        # the _site directory and generate it.
        c = nginx.loadf(os.path.join('/etc/nginx/sites-available', self.id))
        for x in c.servers:
            if x.filter('Key', 'root'):
                x.filter('Key', 'root')[0].value = \
                    os.path.join(self.path, '_site')
        nginx.dumpf(c, os.path.join('/etc/nginx/sites-available', self.id))
        s = shell('jekyll build --source {0} --destination {1}'
                  .format(self.path, os.path.join(self.path, '_site')))
        if s["code"] != 0:
            raise Exception('Jekyll failed to build: {0}'
                            .format(str(s["stderr"])))
        uid, gid = users.get_system("http").uid, groups.get_system("http").gid
        for r, d, f in os.walk(self.path):
            for x in d:
                os.chmod(os.path.join(r, x), 0o755)
                os.chown(os.path.join(r, x), uid, gid)
            for x in f:
                os.chmod(os.path.join(r, x), 0o644)
                os.chown(os.path.join(r, x), uid, gid)

        # Return an explicatory message.
        return 'Jekyll has been setup, with a sample site at {0}. '\
            'Modify these files as you like. To learn how to use Jekyll, '\
            'visit http://jekyllrb.com/docs/usage. After making changes, '\
            'click the Edit button for the site, then "Regenerate Site" '\
            'to bring your changes live.'.format(self.path)

    def pre_remove(self):
        pass

    def post_remove(self):
        pass

    def enable_ssl(self, cfile, kfile):
        pass

    def disable_ssl(self):
        pass

    def update(self, pkg, ver):
        ruby.update_gem('jekyll', 'rdiscount')

    def regenerate(self):
        path = self.path
        if not path.endswith("_site"):
            path = os.path.join(self.path, "_site")
        s = shell('jekyll build --source {0} --destination {1}'
                  .format(self.path.split('/_site')[0], path))
        if s["code"] != 0:
            raise Exception('Jekyll failed to build: {0}'
                            .format(str(s["stderr"])))
        uid, gid = users.get_system("http").uid, groups.get_system("http").gid
        for r, d, f in os.walk(self.path):
            for x in d:
                os.chmod(os.path.join(r, x), 0o755)
                os.chown(os.path.join(r, x), uid, gid)
            for x in f:
                os.chmod(os.path.join(r, x), 0o644)
                os.chown(os.path.join(r, x), uid, gid)
