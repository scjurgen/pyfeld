# -*- coding: utf-8 -*-
from datetime import datetime
import hashlib
import threading
from time import sleep

from pyfeld.stateVariables import StateVariables
from pyfeld.upnpCommand import UpnpCommand
import urllib3
from pyfeld.didlInfo import DidlInfo


class RaumfeldZone:

    def __init__(self, udn):
        self.udn = udn
        self.media = None
        self.soap_host = None
        self.upnpcmd = None
        self.volume = "0"

        self.state_variables = StateVariables(udn)
        self.position = None
        self.terminate_loop = False

        self.rooms = []
        #i think better to use states(fading, looping, magic, intermezzo
        self.is_fading = False
        self.is_looping = False
        self.is_magic = False
        self.is_sleeping = False
        self.is_intermezzo = False

        self.tLast = datetime.now()
        self.last_position = -1
        self.latest_short_info = None

    def get_udn(self):
        return self.udn

    def add_room(self, room):
        self.rooms.append(room)

    def get_control_hash(self):
        room_udns = []
        for room in self.rooms:
            room_udns.append(room.get_udn())
            for renderer in room.get_renderer_list():
                room_udns.append(renderer.get_udn())
        room_udns.sort()
        combined = str(self.soap_host)
        for t in room_udns:
            combined += str(t)
        return hashlib.md5(combined.encode()).hexdigest()

    def get_friendly_name(self):
        friendly_name = ""

        if not self.udn:
            if len(self.rooms) == 0:
                return "unassigned rooms (empty)"
            if len(self.rooms) == 1:
                return "unassigned room"
            return "unassigned rooms"

        room_names = []
        for r in self.rooms:
            room_names.append(r.get_name())

        room_names.sort(key=lambda v: v.upper())

        for r in room_names:
            friendly_name += r
            friendly_name += ", "
        return friendly_name[:-2]  # cut last comma

    def update_volumes(self):
        if self.upnpcmd is None:
            return
        result = self.upnpcmd.get_volume()
        if 'CurrentVolume' in result:
            self.volume = result['CurrentVolume']
        for r in self.rooms:
            result = self.upnpcmd.get_room_volume(r.get_udn())
            if 'CurrentVolume' in result:
                print("Room volume {0} {1}".format(r.get_name(), result['CurrentVolume']))
                r.set_volume(result['CurrentVolume'])

    def set_volume(self, value):
        self.upnpcmd.set_volume(value)

    def set_soap_host(self, host):
        if host is None:
            self.soap_host = None
            self.upnpcmd = None
            return
        urlsplit = urllib3.util.parse_url(host)
        self.soap_host = urlsplit.scheme + "://"+urlsplit.netloc
        self.upnpcmd = UpnpCommand(self.soap_host)

    def play(self):
        self.upnpcmd.play()

    def stop(self):
        self.upnpcmd.stop()

    def previous(self):
        self.upnpcmd.previous()

    def next(self):
        self.upnpcmd.next()

    def seek(self, value):
        self.upnpcmd.seek(value)

    def update_position_info(self):
        self.position = self.upnpcmd.get_position_info()
        if 'TrackDuration' in self.position:
            components = self.position['TrackDuration'].split(':')
            self.position['TrackDurationInfo'] = {
                    'Tsecs': int(components[0]) * 3600 + int(components[1]) * 60 + int(components[2])
                    , 'hour': int(components[0])
                    , 'minute': int(components[1])
                    , 'seconds': int(components[2])}
        else:
            self.position['TrackDurationInfo'] = {'Tsecs': 0, 'hour': 0, 'minute': 0, 'seconds': 0}

        if 'AbsTime' in self.position:
            components = self.position['AbsTime'].split(':')
            self.position['AbsTimeInfo'] = {
                    'Tsecs': int(components[0]) * 3600 + int(components[1]) * 60 + int(components[2])
                    , 'hour': int(components[0])
                    , 'minute': int(components[1])
                    , 'seconds': int(components[2])}
        else:
            self.position['AbsTimeInfo'] = {'Tsecs': 0, 'hour': 0, 'minute': 0, 'seconds': 0}

        if 'RelTime' in self.position:
            components = self.position['RelTime'].split(':')
            self.position['RelTimeInfo'] = {
                'Tsecs': int(components[0]) * 3600 + int(components[1]) * 60 + int(components[2])
                , 'hour': int(components[0])
                , 'minute': int(components[1])
                , 'seconds': int(components[2])}
        else:
            self.position['RelTimeInfo'] = {'Tsecs': 0, 'hour': 0, 'minute': 0, 'seconds': 0}

    def update_media(self):
        self.update_position_info()
        self.media = self.upnpcmd.get_media_info()
        if self.media is None:
            return
        try:
            didlinfo = DidlInfo(self.media['CurrentURIMetaData'])
            self.media['didlextractUri'] = didlinfo.get_items()
        except Exception as e:
            print("didl info no CurrentURIMetaData: {0}".format(e))
        try:
            didlinfo = DidlInfo(self.position['TrackMetaData'])
            self.media['didlextract'] = didlinfo.get_items()
            if self.position['TrackURI']:
                self.media['TrackURI'] = self.position['TrackURI']
        except Exception as e:
            print("didl info no TrackMetaData: {0}".format(e))

    def set_media(self, media):
        if media is None:
            return None
        return self.upnpcmd.set_transport_uri(media)

    def get_zone_stuff(self):
        self.update_volumes()
        self.transport = self.upnpcmd.get_transport_setting()
        self.update_media()

    def get_volume(self):
        return self.volume

    #playing status should be evented
    def is_playing(self):
        t_now = datetime.now()
        if t_now > self.tLast:
            self.tLast = t_now
            new_position = self.get_position_in_seconds()
            if new_position != self.last_position:
                self.last_is_playing_status = True
                self.last_position = new_position
                return True
            else:
                self.last_is_playing_status = False
        return self.last_is_playing_status

    def get_position_in_seconds(self):
        try:
            self.update_position_info()
            return self.position['AbsTimeInfo']['Tsecs']
        except Exception as e:
            print("get_position_in_seconds error {0}".format(e))
            return 0

    def seek_to_position_in_seconds(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        self.seek("%d:%02d:%02d" % (h, m, s))

    def seek_backward(self, seconds):
        position = self.get_position_in_seconds()
        position -= seconds
        if position < 0:
            position = 0
        self.seek_to_position_in_seconds(position)

    def seek_forward(self, seconds):
        position = self.get_position_in_seconds()
        position += seconds
        self.seek_to_position_in_seconds(position)

    def run_fade(self, from_value, to_value, time_in_seconds):
        self.is_fading = True
        start_time = datetime.now()
        last_value_set = int(from_value)
        self.set_volume(from_value)
        if time_in_seconds == 0:
            return
        while True:
            sleep(1)
            if self.terminate_fade:
                print("premature stop of fade")
                break
            delta = datetime.now() - start_time
            if delta.seconds > int(time_in_seconds):
                print("time reached for end of fade")
                break
            new_value = int(from_value) + (int(to_value)-int(from_value))*delta.seconds/int(time_in_seconds)
            if new_value != last_value_set:
                last_value_set = int(new_value)
                self.set_volume(last_value_set)
        print("fade thread ending")

        self.set_volume(to_value)
        if to_value == 0:
            self.stop()
        self.is_fading = False

    def set_fade(self, from_value, to_value, time_in_seconds):
        self.terminate_fade = True
        while self.is_fading:
            sleep(1)
        self.terminate_fade = False
        fade = threading.Thread(target=self.run_fade, args=(from_value, to_value, time_in_seconds))
        fade.start()

    def run_loop(self, from_value, to_value):
        self.is_looping = True
        while True:
            sleep(1)
            if self.terminate_loop:
                print("stop of loop")
                break
        print("loop thread ending")
        self.is_looping = False

    def set_loop(self, from_value, to_value):
        self.terminate_loop = True
        while self.is_looping:
            sleep(1)
        self.terminate_loop = False
        fade = threading.Thread(target=self.run_loop, args=(from_value, to_value))
        fade.start()

    def set_event_update(self, udn, items_dict):
        assert(udn == self.udn)
        self.state_variables.set_states(items_dict)

    def get_current_title(self):
        try:
            return self.state_variables.state_dict['didlextractUri']['title']
        except:
            return "-"

    def get_current_artist(self):
        try:
            return self.state_variables.state_dict['didlextractUri']['artist']
        except:
            return "-"

    def get_current_album(self):
        try:
            return self.state_variables.state_dict['didlextractUri']['album']
        except:
            return "-"
