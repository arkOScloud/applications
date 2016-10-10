import configparser
import os

from arkos.system import services
from arkos.sharers import Share, Sharer
from arkos.utilities import errors


class Netatalk(Sharer):
    """Share manager for Apple (AFP) shares."""
    name = "Apple (AFP)"

    def add_share(
            self, name, path, comment="", valid_users=[],
            read_only=False):
        s = NetatalkShare(
            id=name, path=path, comment=comment, public=not valid_users,
            valid_users=valid_users, readonly=read_only, manager=self
        )
        s.add()
        return s

    def get_shares(self):
        """Return a list of AFP shares on the system."""
        shares = []
        config = configparser.ConfigParser()
        config.read(["/etc/afp.conf"])
        for x in config.sections():
            if x == "Global":
                continue
            share = NetatalkShare(
                id=x, path=config.get(x, "path"), comment="",
                public=not config.get(x, "valid users", fallback=""),
                valid_users=config.get(x, "valid users", fallback="").split(" "),
                readonly=config.get(x, "read only", fallback="no") == "yes",
                manager=self)
            shares.append(share)
        return shares

    def get_mounts(self):
        """Return an empty list -- we cannot mount AFP shares."""
        return []


class NetatalkShare(Share):
    """Class representing an AFP share."""

    def add_share(self):
        """Add a share."""
        config = configparser.ConfigParser()
        config.read(["/etc/afp.conf"])
        if config.has_section(self.id):
            raise errors.InvalidConfigError(
                "Share already present with this name"
            )
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        config.add_section(self.id)
        config.set(self.id, "path", self.path)
        config.set(self.id, "read only", "yes" if self.readonly else "no")
        if self.valid_users:
            config.set(self.id, "valid users", " ".join(self.valid_users))
        config.set("Global", "ldap_server", "localhost")
        config.set("Global", "ldap_auth_method", "none")
        config.set("Global", "ldap_userbase", "ou=users,dc=arkos-servers,dc=org")
        with open("/etc/afp.conf", "w") as f:
            config.write(f)
        svc = services.get("netatalk")
        if svc and svc.state:
            svc.restart()

    def remove_share(self):
        """Remove a share."""
        config = configparser.ConfigParser()
        config.read(["/etc/afp.conf"])
        if not config.has_section(self.id):
            return
        config.remove_section(self.id)
        with open("/etc/afp.conf", "w") as f:
            config.write(f)
        svc = services.get("netatalk")
        if svc and svc.state:
            svc.restart()
