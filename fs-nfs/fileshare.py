import ctypes
import ctypes.util
import os
import shlex

from arkos.sharers import Share, Mount, Sharer
from arkos.utilities import b, errors, shell

libc = ctypes.CDLL(ctypes.util.find_library("libc"), use_errno=True)


class NFS(Sharer):
    """Share manager for NFS shares."""
    name = "Linux (NFS)"

    def add_share(
            self, name, path, comment="", valid_users=[],
            read_only=False):
        s = NFSShare(
            id=name, path=path, public=not valid_users,
            valid_users=valid_users, readonly=read_only, manager=self
        )
        s.add()
        return s

    def add_mount(self, path, network_path, read_only=False):
        s = NFSMount(
            path=path, network_path=network_path, readonly=read_only,
            manager=self
        )
        s.add()
        return s

    def get_shares(self):
        """Return a list of NFS shares on the system."""
        shares = []
        with open("/etc/exports", "r") as f:
            data = f.readlines()
        for x in data:
            if x.startswith('#'):
                continue
            x = shlex.split(x)
            valid_users = []
            if not x[1].startswith('*'):
                valid_users = [y.split('(')[0] for y in x[1:]]
            share = NFSShare(
                id=os.path.basename(x[0]), path=x[0],
                public=x[1].startswith('*'), valid_users=valid_users,
                readonly="ro" in x[1], manager=self
            )
            shares.append(share)
        return shares

    def get_mounts(self):
        """Return a list of NFS shares currently mounted on the system."""
        mtab, mounts = [], []
        with open("/etc/mtab", "r") as f:
            for x in f.read():
                mtab.append(shlex.split(x))
        for x in mtab:
            if x[2] != "nfs":
                continue
            mount = NFSMount(id=os.path.basename(x[1]), path=x[1],
                             network_path=x[0], readonly=x[3].startswith("ro"),
                             is_mounted=True, manager=self)
            mounts.append(mount)
        return mounts


class NFSShare(Share):
    """Class representing an NFS share."""

    def add_share(self):
        """Add a share."""
        with open("/etc/exports", "r") as f:
            data = f.readlines()
        if any([shlex.split(x)[0] == self.path for x in data]):
            raise errors.InvalidConfigError(
                "Share already present with this path"
            )
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        sstr = '"' + self.path + '" '
        sstr += '*(' + ("ro" if self.readonly else "rw") + ',sync)'
        with open("/etc/exports", "w") as f:
            f.writelines(data)
            f.write(sstr + '\n')
        shell("exportfs -arv")

    def remove_share(self):
        """Remove a share."""
        with open("/etc/exports", "r") as f:
            data = f.readlines()
        for i, x in enumerate(data):
            if x.startswith('#'):
                continue
            if shlex.split(x)[0] == self.path:
                data.pop(i)
        with open("/etc/exports", "w") as f:
            f.writelines(data)
        shell("exportfs -arv")


class NFSMount(Mount):
    """Class representing an NFS share mount."""

    @property
    def id(self):
        """Return mount ID."""
        endpath = self.network_path.split("/")[-1]
        if endpath:
            return self.network_path.split(":")[0]
        return endpath

    def mount(self, extra_opts={}):
        """Mount the NFS share."""
        if not extra_opts:
            extra_opts = {"vers": "4"}
        opts = ",".join(
            ["{0}={1}".format(x, extra_opts[x]) for x in extra_opts]
        )
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        s = libc.mount(ctypes.c_char_p(b(self.network_path)),
                       ctypes.c_char_p(b(self.path)),
                       ctypes.c_char_p(b"nfs"), 0,
                       ctypes.c_char_p(b(opts)))
        if s == -1:
            excmsg = "Failed to mount {0}: {1}"
            raise Exception(excmsg.format(self.id,
                                          os.strerror(ctypes.get_errno())))
        else:
            self.is_mounted = True

    def umount(self):
        """Unmount the NFS share."""
        if not self.is_mounted:
            return
        s = libc.umount2(ctypes.c_char_p(b(self.path)), 0)
        if s == -1:
            excmsg = "Failed to unmount {0}: {1}"
            raise Exception(excmsg.format(self.id,
                                          os.strerror(ctypes.get_errno())))
        else:
            self.is_mounted = False
