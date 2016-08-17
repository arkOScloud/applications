import json
import os
import sys
import re
import MySQLdb
import _mysql_exceptions

from arkos import conns, secrets
from arkos.system import services
from arkos.databases import Database, DatabaseUser, DatabaseManager
from arkos.utilities import shell, random_string
from arkos.utilities.errors import ConnectionError, ArkOSConnectionError


class MariaDB(Database):
    def add_db(self):
        self.manager.connect()
        if self.manager.validate(self.id):
            conns.MariaDB.query('CREATE DATABASE %s' % self.id)

    def remove_db(self):
        self.manager.connect()
        conns.MariaDB.query('DROP DATABASE %s' % self.id)

    def execute(self, cmd, commit=False, strf=True):
        self.manager.connect()
        conns.MariaDB.query('USE %s' % self.id)
        cur = conns.MariaDB.cursor()
        parse, s = [], ""
        for l in cmd.split('\n'):
            if not l.split() or re.match('--', l):
                continue
            elif not re.search('[^-;]+;', l):
                s = s + l
            elif re.search('^\s*USE\s*', l, re.IGNORECASE):
                raise Exception('Cannot switch databases during execution')
            else:
                s = s + l
                cur.execute(s)
                for x in cur.fetchall():
                    parse.append(x)
                s = ""
        if commit:
            conns.MariaDB.commit()
        if strf:
            status = ""
            for line in parse:
                line = [str(x) for x in line]
                status += ', '.join(line)+'\n'
            return status
        else:
            return parse

    def get_size(self):
        s = self.execute("SELECT sum(data_length+index_length) FROM information_schema.TABLES WHERE table_schema LIKE '%s';" % self.id, strf=False)
        return int(s[0][0]) if s[0][0] else 0

    def dump(self):
        self.manager.connect()
        conns.MariaDB.query("USE %s" % self.id)
        cur = conns.MariaDB.cursor()
        tables, data = [], ""
        cur.execute("SHOW TABLES")
        for table in cur.fetchall():
            tables.append(table[0])
        for table in tables:
            data += "DROP TABLE IF EXISTS `"+str(table)+"`;"
            cur.execute("SHOW CREATE TABLE `"+str(table)+"`;")
            data += "\n"+str(cur.fetchone()[1])+";\n\n"
            cur.execute("SELECT * FROM `"+str(table)+"`;")
            rows = cur.fetchall()
            if rows:
                data += "INSERT INTO `"+str(table)+"` VALUES ("
                s = True
            for row in rows:
                f = True
                if not s:
                    data += '), ('
                for field in row:
                    if not f:
                        data += ', '
                    if type(field) in [int, long]:
                        data += str(field)
                    elif type(field) == str:
                        data += '"'+str(conns.MariaDB.escape_string(field))+'"'
                    else:
                        data += '"'+str(field)+'"'
                    f = False
                s = False
            if rows:
                data += ");\n"
            data += "\n\n"
        return data


class MariaDBUser(DatabaseUser):
    def add_user(self, passwd):
        self.manager.connect()
        if self.manager.validate(user=self.id, passwd=passwd):
            conns.MariaDB.query('CREATE USER \'%s\'@\'localhost\' IDENTIFIED BY \'%s\''
                % (self.id,passwd))

    def remove_user(self):
        self.manager.connect()
        conns.MariaDB.query('DROP USER \'%s\'@\'localhost\'' % self.id)

    def chperm(self, action, db=None):
        self.manager.connect()
        if action == 'check':
            conns.MariaDB.query('SHOW GRANTS FOR \'%s\'@\'localhost\''
                % self.id)
            r = conns.MariaDB.store_result()
            out = r.fetch_row(0)
            parse = []
            status = ''
            for line in out:
                if line[0].startswith('Grants for'):
                    continue
                elif line[0] is '' or line[0] is ' ':
                    continue
                else:
                    parse.append(line[0].split(' IDENT')[0])
            for line in parse:
                status += line + '\n'
            return status
        elif action == 'grant':
            conns.MariaDB.query('GRANT ALL ON %s.* TO \'%s\'@\'localhost\''
                % (db.id, self.id))
        elif action == 'revoke':
            conns.MariaDB.query('REVOKE ALL ON %s.* FROM \'%s\'@\'localhost\''
                % (db.id, self.id))


class MariaDBMgr(DatabaseManager):
    def connect(self, user='root', passwd='', db=None):
        passwd = passwd or secrets.get("mysql")
        if not os.path.exists("/var/lib/mysql/mysql"):
            shell("mysql_install_db --user=mysql --basedir=/usr --datadir=/var/lib/mysql")
        try:
            conns.MariaDB.ping()
            self.state = True
            return
        except:
            pass
        try:
            if not passwd:
                passwd = self.change_admin_passwd()
            conns.MariaDB = MySQLdb.connect('localhost', user, passwd, db or "")
            self.state = True
            self.connection = conns.MariaDB
        except:
            self.state = False
            raise ArkOSConnectionError("MariaDB")

    def change_admin_passwd(self):
        try:
            s = services.get("mysqld")
            if s.state != "running":
                s.start()
        except:
            return ""
        new_passwd = random_string()[:16]
        secrets.set("mysql", new_passwd)
        secrets.save()
        c = MySQLdb.connect('localhost', 'root', '', 'mysql')
        c.query('UPDATE user SET password=PASSWORD("'+new_passwd+'") WHERE User=\'root\'')
        c.query('FLUSH PRIVILEGES')
        c.commit()
        return new_passwd

    def validate(self, id='', user='', passwd=''):
        if id and re.search('\.|-|`|\\\\|\/|^test$|[ ]', id):
            raise Exception('Database name must not contain spaces, dots, dashes or other special characters')
        elif id and len(id) > 16:
            raise Exception('Database name must be shorter than 16 characters')
        if user and re.search('\.|-|`|\\\\|\/|^test$|[ ]', user):
            raise Exception('Database username must not contain spaces, dots, dashes or other special characters')
        elif user and len(user) > 16:
            raise Exception('Database username must be shorter than 16 characters')
        if passwd and len(passwd) < 8:
            raise Exception('Database password must be longer than 8 characters')
        if id:
            for x in self.get_dbs():
                if x.id == id:
                    raise Exception('You already have a database named %s - please remove that one or choose a new name!' % id)
        if user:
            for x in self.get_users():
                if x.id == user:
                    raise Exception('You already have a database user named %s - please remove that one or choose a new name!' % user)
        return True

    def get_dbs(self):
        self.connect()
        dblist = []
        excludes = ['Database', 'information_schema',
            'mysql', 'performance_schema']
        conns.MariaDB.query('SHOW DATABASES')
        r = conns.MariaDB.store_result()
        dbs = r.fetch_row(0)
        for db in dbs:
            if not db[0] in excludes and db[0].split():
                dblist.append(MariaDB(id=db[0], manager=self))
        return dblist

    def add_db(self, id):
        db = MariaDB(id=id, manager=self)
        db.add()
        return db

    def get_users(self):
        self.connect()
        userlist = []
        excludes = ['root', ' ', '']
        conns.MariaDB.query('SELECT user FROM mysql.user')
        r = conns.MariaDB.store_result()
        output = r.fetch_row(0)
        for usr in output:
            if not usr[0] in userlist and not usr[0] in excludes:
                userlist.append(MariaDBUser(id=usr[0], manager=self))
        return userlist

    def add_user(self, id, passwd):
        user = MariaDBUser(id=id, manager=self)
        user.add(passwd)
        return user
