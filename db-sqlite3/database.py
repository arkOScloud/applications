import os
import re
import stat
import sqlite3

from arkos.system import groups
from arkos.utilities import str_fsize, shell
from arkos.databases import Database, DatabaseManager


class SQLite3(Database):
    def add_db(self):
        if re.search('\.|-|`|\\\\|\/|[ ]', self.name):
            raise Exception('Name must not contain spaces, dots, dashes or other special characters')
        self.manager.chkpath()
        path = '/var/lib/sqlite3/%s.db' % self.name
        status = shell('sqlite3 %s "ATTACH \'%s\' AS %s;"' % (path,path,self.name))
        if status["code"] >= 1:
            raise Exception(status["stderr"])

    def remove_db(self):
        shell('rm /var/lib/sqlite3/%s.db' % self.name)

    def execute(self, cmd, strf=False):
        cmds = cmd.split(';')
        conn = sqlite3.connect('/var/lib/sqlite3/%s.db' % self.name)
        c = conn.cursor()
        out = []
        for x in cmds:
            if x.split():
                c.execute('%s' % x)
                out += c.fetchall()
        conn.commit()
        if not strf:
            return out
        else:
            status = ''
            for line in out:
                status += line + '\n'
            return status

    def get_size(self):
        return str_fsize(os.path.getsize(os.path.join('/var/lib/sqlite3', self.name+'.db')))

    def dump(self):
        self.manager.chkpath()
        conn = sqlite3.connect('/var/lib/sqlite3/%s.db' % self.name)
        data = ""
        for x in conn.iterdump():
            data += x
        return data


class SQLite3Mgr(DatabaseManager):
    def connect(self):
        pass
    
    def validate(self, name='', user='', passwd=''):
        pass

    def get_dbs(self):
        self.chkpath()
        dblist = []
        for thing in os.listdir('/var/lib/sqlite3'):
            if thing.endswith('.db'):
                dblist.append(SQLite3(name=thing.split('.db')[0], manager=self))
        return dblist
    
    def add_db(self, name):
        db = SQLite3(name=name, manager=self)
        db.add()
        return db
    
    def add_user(self, passwd):
        pass
    
    def chkpath(self):
        # Make sure the db dir exists and that it has the right perms
        g = groups.get_system("sqlite3")
        if not g:
            g = groups.SystemGroup("sqlite3", users=["http"])
            g.add()
        if not os.path.isdir('/var/lib/sqlite3'):
            os.makedirs('/var/lib/sqlite3')
        if oct(stat.S_IMODE(os.stat('/var/lib/sqlite3').st_mode)) != 0775:
            os.chmod('/var/lib/sqlite3', 0775)
        if int(os.stat('/var/lib/sqlite3').st_gid) != g.gid:
            os.chown('/var/lib/sqlite3', -1, g.gid)
