import os
import re
import stat
import sqlite3

from arkos.system import groups
from arkos.utilities import errors, shell
from arkos.databases import Database, DatabaseManager


class SQLite3(Database):
    @property
    def path(self):
        return '/var/lib/sqlite3/{0}.db'.format(self.id)

    def add_db(self):
        if re.search('\.|-|`|\\\\|\/|[ ]', self.id):
            raise errors.InvalidConfigError(
                'Name must not contain spaces, dots, dashes or other '
                'special characters'
            )
        self.manager.chkpath()
        status = shell(
            "sqlite3 {0} \"ATTACH '{1}' AS {2};\"".format(
                self.path, self.path, self.id
            )
        )
        if status["code"] >= 1:
            raise errors.OperationFailedError(status["stderr"])

    def remove_db(self):
        shell('rm {0}'.format(self.path))

    def execute(self, cmd, strf=False):
        cmds = cmd.split(';')
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        out = []
        for x in cmds:
            if x.split():
                c.execute('{0}'.format(x))
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
        return os.path.getsize(self.path)

    def dump(self):
        self.manager.chkpath()
        conn = sqlite3.connect(self.path)
        data = ""
        for x in conn.iterdump():
            data += x
        return data


class SQLite3Mgr(DatabaseManager):
    def connect(self):
        pass

    def validate(self, id_='', user='', passwd=''):
        pass

    def get_dbs(self):
        self.chkpath()
        dblist = []
        for thing in os.listdir('/var/lib/sqlite3'):
            if thing.endswith('.db'):
                dblist.append(
                    SQLite3(
                        id=thing.split('.db')[0], manager=self
                    )
                )
        return dblist

    def add_db(self, id_):
        db = SQLite3(id_=id_, manager=self)
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
        if oct(stat.S_IMODE(os.stat('/var/lib/sqlite3').st_mode)) != 0o775:
            os.chmod('/var/lib/sqlite3', 0o775)
        if int(os.stat('/var/lib/sqlite3').st_gid) != g.gid:
            os.chown('/var/lib/sqlite3', -1, g.gid)
