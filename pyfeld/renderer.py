
from __future__ import unicode_literals

from pyfeld.upnpService import UpnpService

class Renderer:
    def __init__(self, udn, name, location):
        self.name = name
        self.udn = udn
        self.upnp_service = None
        self.location = location

    def set_name(self, name):
        self.name = name

    def get_name(self):
        return self.name

    def get_location(self):
        return self.location

    def get_udn(self):
        return self.udn

    def set_upnp_service(self, location):
        self.upnp_service = UpnpService()
        if location is not None:
            self.upnp_service.set_location(location)

