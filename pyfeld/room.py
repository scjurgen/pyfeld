from __future__ import unicode_literals

import urllib3

from pyfeld.upnpService import UpnpService

class Room:
    def __init__(self, udn, renderer_list, name, location):
        self.name = name
        self.udn = udn
        self.renderer_list = renderer_list
        self.volume = 0
        self.mute = 0
        self.upnp_service = None
        self.location = location
        base_url_parsed = urllib3.util.parse_url(location)
        base_url = base_url_parsed.scheme + "://" + base_url_parsed.netloc
        #we need to parse these out of the xml to make it robust
        self.scpdurl = base_url+"/rendercontrol.xml"
        self.controlURL = base_url+"/RenderingControl/ctrl"
        self.eventSubURL = base_url+"/RenderingControl/evt"

    def set_volume(self, volume):
        self.volume = volume

    def set_name(self, name):
        self.name = name

    def get_name(self):
        return self.name

    def get_location(self):
        return self.location

    def get_udn(self):
        return self.udn

    def get_renderer_list(self):
        return self.renderer_list

    def get_volume(self):
        return self.volume

    def set_upnp_service(self, location):
        self.upnp_service = UpnpService()
        if location is not None:
            self.upnp_service.set_location(location)

    def set_event_update(self, udn, items_dict):
        assert(udn == self.udn)
        if 'Volume' in items_dict:
            self.volume = items_dict['Volume']
        if 'Mute' in items_dict:
            self.mute = items_dict['Mute']
