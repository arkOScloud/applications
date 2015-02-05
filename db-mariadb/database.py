import re
import MySQLdb
import _mysql_exceptions

from arkos import conns
from arkos.utilities import str_fsize
from arkos.databases import Database, DatabaseUser, DatabaseManager
from arkos.utilities.errors import ConnectionError


class MariaDB(Database):
    def add_db(self):
        if not hasattr(conns, "MariaDB") or not conns.MariaDB:
            self.manager.connect()
        if self.manager.validate(self.name):
            conns.MariaDB.query('CREATE DATABASE %s' % self.name)

    def remove_db(self):
        if not hasattr(conns, "MariaDB") or not conns.MariaDB:
            self.manager.connect()
        conns.MariaDB.query('DROP DATABASE %s' % self.name)

    def execute(self, cmd, commit=False, strf=True):
        if not hasattr(conns, "MariaDB") or not conns.MariaDB:
            self.manager.connect()
        conns.MariaDB.query('USE %s' % self.name)
        cur = conns.MariaDB.cursor()
        parse, s = [], ""
        for l in cmd.split('\n'):
            if not l.split() or re.match('--', l):
                continue
            elif not re.search('[^-;]+;', l):
                s = s + l
            elif re.search('^\s*USE', l):
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
        s = self.execute("SELECT sum(data_length+index_length) FROM information_schema.TABLES WHERE table_schema LIKE '%s';" % self.name, strf=False)
        return str_fsize(int(s[0][0]) if s[0][0] else 0)

    def dump(self):
        if not hasattr(conns, "MariaDB") or not conns.MariaDB:
            self.manager.connect()
        conns.MariaDB.query("USE %s" % self.name)
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
        if not hasattr(conns, "MariaDB") or not conns.MariaDB:
            self.manager.connect()
        if self.manager.validate(user=self.name, passwd=passwd):
            conns.MariaDB.query('CREATE USER \'%s\'@\'localhost\' IDENTIFIED BY \'%s\''
                % (self.name,passwd))
    
    def remove_user(self):
        if not hasattr(conns, "MariaDB") or not conns.MariaDB:
            self.manager.connect()
        conns.MariaDB.query('DROP USER \'%s\'@\'localhost\'' % self.name)

    def chperm(self, action, db=None):
        if not hasattr(conns, "MariaDB") or not conns.MariaDB:
            self.manager.connect()
        if action == 'check':
            conns.MariaDB.query('SHOW GRANTS FOR \'%s\'@\'localhost\''
                % self.name)
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
                % (db.name, self.name))
        elif action == 'revoke':
            conns.MariaDB.query('REVOKE ALL ON %s.* FROM \'%s\'@\'localhost\'' 
                % (db.name, self.name))


class MariaDBMgr(DatabaseManager):
    def connect(self, user='root', passwd='', db=None):
        try:
            if passwd:
                conns.MariaDB = MySQLdb.connect('localhost', user, passwd, db)
            else:
                conns.MariaDB = MySQLdb.connect('localhost', user, read_default_file="/root/.my.cnf")
        except:
            raise ConnectionError("MariaDB")

    def validate(self, name='', user='', passwd=''):
        if name and re.search('\.|-|`|\\\\|\/|^test$|[ ]', name):
            raise Exception('Database name must not contain spaces, dots, dashes or other special characters')
        elif name and len(name) > 16:
            raise Exception('Database name must be shorter than 16 characters')
        if user and re.search('\.|-|`|\\\\|\/|^test$|[ ]', user):
            raise Exception('Database username must not contain spaces, dots, dashes or other special characters')
        elif user and len(user) > 16:
            raise Exception('Database username must be shorter than 16 characters')
        if passwd and len(passwd) < 8:
            raise Exception('Database password must be longer than 8 characters')
        if name:
            for x in self.get_dbs():
                if x.name == name:
                    raise Exception('You already have a database named %s - please remove that one or choose a new name!' % name)
        if user:
            for x in self.get_users():
                if x.name == user:
                    raise Exception('You already have a database user named %s - please remove that one or choose a new name!' % user)
        return True

    def get_dbs(self):
        if not hasattr(conns, "MariaDB") or not conns.MariaDB:
            self.connect()
        dblist = []
        excludes = ['Database', 'information_schema', 
            'mysql', 'performance_schema']
        conns.MariaDB.query('SHOW DATABASES')
        r = conns.MariaDB.store_result()
        dbs = r.fetch_row(0)
        for db in dbs:
            if not db[0] in excludes and db[0].split():
                dblist.append(MariaDB(name=db[0], manager=self))
        return dblist
    
    def add_db(self, name):
        db = MariaDB(name=name, manager=self)
        db.add()
        return db

    def get_users(self):
        if not hasattr(conns, "MariaDB") or not conns.MariaDB:
            self.connect()
        userlist = []
        excludes = ['root', ' ', '']
        conns.MariaDB.query('SELECT user FROM mysql.user')
        r = conns.MariaDB.store_result()
        output = r.fetch_row(0)
        for usr in output:
            if not usr[0] in userlist and not usr[0] in excludes:
                userlist.append(MariaDBUser(name=usr[0], manager=self))
        return userlist
    
    def add_user(self, name, passwd):
        user = MariaDBUser(name=name, manager=self)
        user.add(passwd)
        return user
