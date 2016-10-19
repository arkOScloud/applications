import configparser
import ctypes
import ctypes.util
import os
import shutil

from arkos import secrets
from arkos.system import services
from arkos.sharers import Share, Mount, Sharer
from arkos.utilities import b, errors, shell

libc = ctypes.CDLL(ctypes.util.find_library("libc"), use_errno=True)


class Samba(Sharer):
    """Share manager for Samba (SMB) shares."""
    name = "Windows (SMB)"

    def add_share(
            self, name, path, comment="", valid_users=[],
            read_only=False):
        if os.path.exists("/var/lib/samba/private/secrets.tdb"):
            data = shell("tdbtool /var/lib/samba/private/secrets.tdb")
            if "SECRETS/LDAP_BIND_PW/cn=admin,dc=arkos-servers,dc=org"\
                    not in data["stdout"].decode():
                self._init_samba_for_ldap()
        s = SambaShare(
            id=name, path=path, comment=comment, public=not valid_users,
            valid_users=valid_users, readonly=read_only, manager=self
        )
        s.add()
        return s

    def add_mount(
            self, path, network_path, username="", password="",
            read_only=False):
        s = SambaMount(
            path=path, network_path=network_path, readonly=read_only,
            username=username, password=password, manager=self
        )
        s.add()
        return s

    def get_shares(self):
        """Return a list of SMB shares on the system."""
        if not os.path.exists("/etc/samba/smb.conf")\
                and os.path.exists("/etc/samba/smb.conf.default"):
            shutil.copyfile("/etc/samba/smb.conf.default",
                            "/etc/samba/smb.conf")
        elif not os.path.exists("/etc/samba/smb.conf"):
            return []
        shares = []
        config = configparser.ConfigParser()
        config.read(["/etc/samba/smb.conf"])
        for x in config.sections():
            if x == "global" or x == "homes" or\
                    config.get(x, "printable", fallback="no") == "yes":
                continue
            share = SambaShare(
                id=x, path=config.get(x, "path"),
                comment=config.get(x, "comment", fallback=""),
                public=config.get(x, "public", fallback="yes") == "yes",
                valid_users=config.get(x, "valid users", fallback="")
                .split(" "),
                readonly=config.get(x, "read only", fallback="no") == "yes",
                manager=self)
            shares.append(share)
        return shares

    def get_mounts(self):
        """Return a list of SMB shares currently mounted on the system."""
        mtab, mounts = [], []
        with open("/etc/mtab", "r") as f:
            for x in f.read():
                mtab.append(x.split())
        for x in mtab:
            if x[2] != "cifs":
                continue
            mount = SambaMount(
                id=os.path.basename(x[1]), path=x[1], network_path=x[0],
                readonly=x[3].startswith("ro"), is_mounted=True, manager=self)
            mounts.append(mount)
        return mounts

    def _init_samba_for_ldap(self):
        shell("smbpasswd -w {0}".format(secrets.get("ldap")))
        config = configparser.ConfigParser()
        config.read(["/etc/samba/smb.conf"])
        config.set("global", "ldap ssl", "off")
        config.set("global", "ldap passwd sync", "no")
        config.set("global", "ldap suffix", "dc=arkos-servers,dc=org")
        config.set("global", "ldap user suffix", "ou=users")
        config.set("global", "ldap group suffix", "ou=groups")
        config.set(
            "global", "ldap admin dn", "cn=admin,dc=arkos-servers,dc=org"
        )
        with open("/etc/samba/smb.conf", "w") as f:
            config.write(f)


class SambaShare(Share):
    """Class representing a Samba share."""

    def add_share(self):
        """Add a share."""
        config = configparser.ConfigParser()
        config.read(["/etc/samba/smb.conf"])
        if config.has_section(self.id):
            raise errors.InvalidConfigError(
                "Share already present with this name"
            )
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        config.add_section(self.id)
        config.set(self.id, "comment", self.comment)
        config.set(self.id, "path", self.path)
        config.set(self.id, "public", "yes" if not self.valid_users else "no")
        config.set(self.id, "read only", "yes" if self.readonly else "no")
        if self.valid_users:
            config.set(self.id, "valid users", " ".join(self.valid_users))
        with open("/etc/samba/smb.conf", "w") as f:
            config.write(f)
        svc = services.get("smbd")
        if svc:
            svc.restart()

    def remove_share(self):
        """Remove a share."""
        config = configparser.ConfigParser()
        config.read(["/etc/samba/smb.conf"])
        if not config.has_section(self.id):
            return
        config.remove_section(self.id)
        with open("/etc/samba/smb.conf", "w") as f:
            config.write(f)
        svc = services.get("smbd")
        if svc:
            svc.restart()


class SambaMount(Mount):
    """Class representing a Samba share mount."""

    @property
    def id(self):
        """Return mount ID."""
        if "\\" in self.network_path:
            return self.network_path.split("\\")[-1]
        else:
            return self.network_path.split("/")[-1]

    def mount(self, extra_opts={}):
        """Mount the Samba share."""
        if self.username and "user" not in extra_opts:
            extra_opts["user"] = self.username
        if self.password and "password" not in extra_opts:
            extra_opts["password"] = self.password
        opts = ",".join(
            ["{0}={1}".format(x, extra_opts[x]) for x in extra_opts]
        )
        if self.readonly:
            opts = "ro" + ((","+opts) if opts else "")
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        s = libc.mount(ctypes.c_char_p(b(self.network_path)),
                       ctypes.c_char_p(b(self.path)),
                       ctypes.c_char_p(b"cifs"), 0,
                       ctypes.c_char_p(b(opts)))
        if s == -1:
            excmsg = "Failed to mount {0}: {1}"
            raise Exception(excmsg.format(self.id,
                                          os.strerror(ctypes.get_errno())))
        else:
            self.is_mounted = True

    def umount(self):
        """Unmount the Samba share."""
        if not self.is_mounted:
            return
        s = libc.umount2(ctypes.c_char_p(b(self.path)), 0)
        if s == -1:
            excmsg = "Failed to unmount {0}: {1}"
            raise Exception(excmsg.format(self.id,
                                          os.strerror(ctypes.get_errno())))
        else:
            self.is_mounted = False
