import grp
import nginx
import os
import pwd

from arkos.core.languages import ruby
from arkos.core.sites import SiteEngine
from arkos.core.utilities import shell, random_string


class Jekyll(SiteEngine):
    addtoblock = []

    def pre_install(self, name, vars):
        ruby.install_gem('jekyll', 'rdiscount')

    def post_install(self, name, path, vars, dbinfo={}):
        # Make sure the webapps config points to the _site directory and generate it.
        c = nginx.loadf(os.path.join('/etc/nginx/sites-available', name))
        for x in c.servers:
            if x.filter('Key', 'root'):
                x.filter('Key', 'root')[0].value = os.path.join(path, '_site')
        nginx.dumpf(c, os.path.join('/etc/nginx/sites-available', name))
        s = shell('jekyll build --source '+path+' --destination '+os.path.join(path, '_site'))
        if s["code"] != 0:
            raise Exception('Jekyll failed to build: %s'%str(s["stderr"]))
        uid, gid = pwd.getpwnam("http").pw_uid, grp.getgrnam("http").gr_gid
        for r, d, f in os.walk(path):
            for x in d:
                os.chmod(os.path.join(root, x), 0755)
                os.chown(os.path.join(root, x), uid, gid)
            for x in f:
                os.chmod(os.path.join(root, x), 0644)
                os.chown(os.path.join(root, x), uid, gid)

        # Return an explicatory message.
        return 'Jekyll has been setup, with a sample site at '+path+'. Modify these files as you like. To learn how to use Jekyll, visit http://jekyllrb.com/docs/usage. After making changes, click the Configure button next to the site, then "Regenerate Site" to bring your changes live.'

    def pre_remove(self, site):
        pass

    def post_remove(self, site):
        pass

    def ssl_enable(self, path, cfile, kfile):
        pass

    def ssl_disable(self, path):
        pass

    def regenerate_site(self, site):
        s = shell('jekyll build --source '+site.path.rstrip('_site')+' --destination '+os.path.join(site.path), stderr=True)
        if s["code"] != 0:
            raise Exception('Jekyll failed to build: %s'%str(s["stderr"]))
        uid, gid = pwd.getpwnam("http").pw_uid, grp.getgrnam("http").gr_gid
        for r, d, f in os.walk(path):
            for x in d:
                os.chmod(os.path.join(root, x), 0755)
                os.chown(os.path.join(root, x), uid, gid)
            for x in f:
                os.chmod(os.path.join(root, x), 0644)
                os.chown(os.path.join(root, x), uid, gid)
