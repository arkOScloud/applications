import configparser
import ctypes
import ctypes.util
import os
import shutil

from arkos.system import services
from arkos.sharers import Share, Mount, Sharer

libc = ctypes.CDLL(ctypes.util.find_library("libc"), use_errno=True)


class Samba(Sharer):
    """Share manager for Samba (SMB) shares."""

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
            if x == "global" or config.get(x, "printable", "no") == "yes":
                continue
            share = SambaShare(id=x, path=config.get(x, "path"),
                               comment=config.get(x, "comment", ""),
                               public=config.get(x, "public", "yes") == "yes",
                               valid_users=config.get(x, "valid users", "").split(" "),
                               readonly=config.get(x, "read only") == "yes",
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
            mount = SambaMount(id=os.path.basename(x[1]), path=x[1],
                               network_path=x[0], readonly=x[3].startswith("ro"),
                               is_mounted=True, manager=self)
            mounts.append(mount)
        return mounts


class SambaShare(Share):
    """Class representing a Samba share."""

    def add_share(self):
        """Add a share."""
        config = configparser.ConfigParser()
        config.read(["/etc/samba/smb.conf"])
        if config.has_section(self.id):
            raise Exception("Share already present with this name")
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        config.add_section(self.id)
        config.set(self.id, "comment", self.comment)
        config.set(self.id, "path", self.path)
        config.set(self.id, "public", "yes" if not self.valid_users else "no")
        config.set(self.id, "read only", "yes" if self.readonly else "no")
        if self.valid_users:
            config.set(self.id, "valid users", self.valid_users)
        with open("/etc/samba/smb.conf", "w") as f:
            config.write(f)
        svc = services.get("smbd")
        if svc and svc.state:
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
        if svc and svc.state:
            svc.restart()


class SambaMount(Mount):
    """Class representing a Samba share mount."""

    def mount(self, extra_opts={}):
        """Mount the Samba share."""
        opts = ",".join(["{0}={1}" for x, y in extra_opts])
        mount_point = self.mountpoint or os.path.join("/media", self.id)
        if not os.path.exists(mount_point):
            os.makedirs(mount_point)
        s = libc.mount(ctypes.c_char_p(self.network_path),
                       ctypes.c_char_p(mount_point),
                       ctypes.c_char_p("cifs"), 0,
                       ctypes.c_char_p(opts))
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
        s = libc.umount2(ctypes.c_char_p(self.mountpoint), 0)
        if s == -1:
            excmsg = "Failed to unmount {0}: {1}"
            raise Exception(excmsg.format(self.id,
                                          os.strerror(ctypes.get_errno())))
        else:
            self.is_mounted = False
