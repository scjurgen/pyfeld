from __future__ import unicode_literals

from pyfeld.didlInfo import DidlInfo


class StateVariables:

    def __init__(self, udn):
        self.udn = udn
        self.state_dict = dict()

    def set_states(self, items_dict):
        for key, value in items_dict.items():
            self.set_state(key, value)
        try:
            didlinfo = DidlInfo(items_dict['AVTransportURIMetaData'], False)
            self.state_dict['didlextractUri'] = didlinfo.get_items()
        except:
            pass
        try:
            didlinfo = DidlInfo(items_dict['TrackMetaData'], False)
            self.state_dict['didlextract'] = didlinfo.get_items()
        except:
            pass

    def set_state(self, key, value):
        self.state_dict[key] = value

    def get_state(self, key):
        if key in self.state_dict:
            return self.state_dict[key]
        else:
            return None

    def get_states(self, key):
        return self.state_dict

    def get_info(self):
        result = "udn:"+self.udn
        for item in self.state_dict:
            result += "\n" + item.first + ":" + item.second
        return result


