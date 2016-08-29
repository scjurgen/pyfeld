from __future__ import unicode_literals

import json
import re
import subprocess
import sys
import syslog
from pprint import pprint
from xml.dom import minidom
import hashlib

from pyfeld.renderer import Renderer

from pyfeld.discoverByHttp import DiscoverByHttp
from pyfeld.errorPrint import err_print
from pyfeld.getRaumfeld import RaumfeldDeviceSettings, HostDevice
from pyfeld.raumfeldZone import RaumfeldZone
from pyfeld.room import Room
from pyfeld.upnpCommand import UpnpCommand
from pyfeld.upnpService import UpnpService
from pyfeld.upnpsoap import UpnpSoap

from pyfeld.xmlHelper import XmlHelper

from pyfeld.settings import Settings


class MediaDevice:
    def __init__(self, udn, location, server_type, name=''):
        self.udn = udn
        self.location = location
        self.type = server_type
        self.name = name


class ZonesHandler:
    active_zones = []
    new_zones = []
    media_servers = set()
    config_device = set()
    raumfeld_device = set()
    media_renderers = set()

    def __init__(self):
        self.events_count = 0
        self.verbose = False
        self.zone_hash = ""
        self.found_protocol_ip = None

    def set_active_zones(self, zones, zone_hash):
        self.active_zones = zones
        self.zone_hash = zone_hash
        self.save_quick_access()

    def find_zone_for_room(self, room_name):
        index = 0
        try:
            for index in range(0, len(self.active_zones)):
                for room in self.active_zones[index].rooms:
                    if room.name == room_name:
                        return index
        except Exception as e:
            err_print("find_zone_for_room error: {0}".format(e))
        return index

    def get_request_zone(self, param_dictionary):
        if 'hasroom' in param_dictionary:
            return self.find_zone_for_room(param_dictionary['hasroom'][0])
        elif 'room' in param_dictionary:
            return self.find_zone_for_room(param_dictionary['room'][0])
        elif 'zoneindex' in param_dictionary:
            return int(param_dictionary['zoneindex'][0])
        else:
            err_print("error request zone")

    def set(self, cmd, param_dictionary):
        result = dict()
        try:
            index = self.get_request_zone(param_dictionary)
            print("set " + cmd)
            print("zone index:" + str(index))
            result['set'] = cmd
            result['zoneindex'] = str(index)

            if cmd == "volume":
                self.active_zones[index].set_volume(param_dictionary['value'][0])
        except Exception as e:
            result['error'] = "set error {0}".format(e)
            err_print("set  error {0}".format(e))
        return result

    def get_last_media(self, param_dictionary):
        index = self.get_request_zone(param_dictionary)
        return self.active_zones[index].media

    def set_media(self, media, param_dictionary):
        index = self.get_request_zone(param_dictionary)
        self.active_zones[index].set_media(media)

    def get(self, cmd, param_dictionary):
        result = dict()
        try:
            index = self.get_request_zone(param_dictionary)
            result['get'] = cmd
            result['zoneindex'] = str(index)
            zone = self.active_zones[index]
            result['isplaying'] = zone.is_playing()
            if cmd == "volume":
                zone.update_volumes()
                result['volume'] = str(zone.volume)
            if cmd == "position":
                zone.update_position_info()
                result.update(zone.position)
            if cmd == "media":
                zone.update_media()
                result.update(zone.media)
            if cmd == 'runstate':
                pass

        except Exception as e:
            result['error'] = "get error cmd={0} {1}".format(cmd, e)
            err_print("get error cmd={0} {1}".format(cmd, e))
        return result

    def do(self, cmd, param_dictionary):
        result = dict()
        try:
            index = self.get_request_zone(param_dictionary)
            print("do " + cmd)
            print("zone index:" + str(index))
            result['do'] = cmd
            result['zoneindex'] = str(index)

            if cmd == "pause":
                self.active_zones[index].pause()
            elif cmd == "stop":
                self.active_zones[index].stop()
            elif cmd == "play":
                self.active_zones[index].play()
            elif cmd in ["prev", "previous"]:
                self.active_zones[index].previous()
            elif cmd == "next":
                self.active_zones[index].next()
            elif cmd == "seek":
                self.active_zones[index].seek(param_dictionary['value'][0])
            elif cmd == "seekback":
                self.active_zones[index].seek_backward(10)
            elif cmd == "seekfwd":
                self.active_zones[index].seek_forward(10)
            elif cmd == "fade":
                self.active_zones[index].set_fade(param_dictionary['vs'][0]
                                                  , param_dictionary['ve'][0]
                                                  , param_dictionary['t'][0]
                                                  )
            elif cmd == "loop":
                self.active_zones[index].set_loop(param_dictionary['cuein'][0]
                                                  , param_dictionary['cueout'][0]
                                                  )
            elif cmd == 'stoploop':
                self.active_zones[index].terminate_loop = True

        except Exception as e:
            err_print("set action error {0}".format(e))
        return result

    def get_network_location_by_udn(self, udn, xmlListDevices):
        if udn is None:
            return None
        devices = xmlListDevices.getElementsByTagName("device")
        try:
            for device in devices:
                if device.getAttribute('udn') == udn:
                    location = device.getAttribute('location')
                    return location
                #                    host_path = re.match("http://(.*)/", location)
                #                    return host_path.group(1)
        except Exception as e:
            err_print("Error in regex find:{0}".format(e))
        #err_print("WARNING: could not find location by udn in listDevices {0}".format(udn))
        return None

    def parse_other_devices_in_zone_raumfeld(self, xmlListDevices, zone_udn, zone):
        zone_obj = RaumfeldZone(zone_udn)
        rooms = zone.getElementsByTagName('room')
        for room in rooms:
            room_udn = room.getAttribute('udn')
            # print(room_udn)
            element = room.getElementsByTagName('renderer')
            for el in element:
                room_renderer_udn = el.getAttribute('udn')
                location = self.get_network_location_by_udn(room_renderer_udn, xmlListDevices)
                room_obj = Room(room_udn, room_renderer_udn, room.attributes['name'].value, location)
                room_obj.set_upnp_service(location)
                zone_obj.add_room(room_obj)
        zone_obj.set_soap_host(self.get_network_location_by_udn(zone_udn, xmlListDevices))
        return zone_obj

    def parse_rooms_in_zone_raumfeld(self, xmlListDevices, zone_udn, zone):
        zone_obj = RaumfeldZone(zone_udn)
        rooms = zone.getElementsByTagName('room')
        for room in rooms:
            room_udn = room.getAttribute('udn')
            #print(room_udn)
            element = room.getElementsByTagName('renderer')
            renderers = []
            for el in element:
                room_renderer_udn = el.getAttribute('udn')
                location = self.get_network_location_by_udn(room_renderer_udn, xmlListDevices)
                renderer = Renderer(room_renderer_udn, el.getAttribute('name'), location)
                ZonesHandler.renderers.append(renderer)
                renderers.append(renderer)

            room_obj = Room(room_udn, renderers, room.attributes["name"].value, location)
            room_obj.set_upnp_service(location)
            zone_obj.add_room(room_obj)
        zone_obj.set_soap_host(self.get_network_location_by_udn(zone_udn, xmlListDevices))
        return zone_obj

    def parse_devices_in_zone_raumfeld(self, xmlListDevices):
        ZonesHandler.media_servers = set()
        ZonesHandler.config_device = set()
        ZonesHandler.raumfeld_device = set()
        ZonesHandler.media_renderers = set()
        devices = xmlListDevices.getElementsByTagName("device")
        for device in devices:
            if device.getAttribute('type') == "urn:schemas-upnp-org:device:MediaServer:1":
                if device.childNodes[0].nodeValue == 'Raumfeld MediaServer':
                    location = device.getAttribute('location')
                    udn = device.getAttribute('udn')
                    type = device.getAttribute('type')
                    host_path = re.match("(http://.*)/", location)
                    name = device.firstChild.nodeValue
                    if self.verbose:
                        print("Media server: ", host_path.group(1))
                    found_device = MediaDevice(udn, host_path.group(1), type, name)
                    found_device.upnp_service = self.get_zone_services(xmlListDevices, udn)
                    ZonesHandler.media_servers.add(found_device)

            if device.getAttribute('type') == "urn:schemas-raumfeld-com:device:ConfigDevice:1":
                if device.childNodes[0].nodeValue == 'Raumfeld ConfigDevice':
                    location = device.getAttribute('location')
                    udn = device.getAttribute('udn')
                    type = device.getAttribute('type')
                    host_path = re.match("(http://.*)/", location)
                    if self.verbose:
                        print("Raumfeld ConfigDevice: ", host_path.group(1))
                    name = device.firstChild.nodeValue
                    found_device = MediaDevice(udn, host_path.group(1), type, name)
                    found_device.upnp_service = self.get_zone_services(xmlListDevices, udn)
                    ZonesHandler.config_device.add(found_device)

            if device.getAttribute('type') == "urn:schemas-upnp-org:device:MediaRenderer:1":
                location = device.getAttribute('location')
                udn = device.getAttribute('udn')
                type = device.getAttribute('type')
                name = device.firstChild.nodeValue
                host_path = re.match("(http://.*)/", location)
                if self.verbose:
                    print("Media renderer: ", host_path.group(1))
                found_device = MediaDevice(udn, host_path.group(1), type, name)
                found_device.upnp_service = self.get_zone_services(xmlListDevices, udn)
                ZonesHandler.media_renderers.add(found_device)

            if device.getAttribute('type') == "urn:schemas-raumfeld-com:device:RaumfeldDevice:1":
                if device.childNodes[0].nodeValue == 'Raumfeld Device':
                    location = device.getAttribute('location')
                    udn = device.getAttribute('udn')
                    type = device.getAttribute('type')
                    name = device.firstChild.nodeValue
                    host_path = re.match("(http://.*)/", location)
                    if self.verbose:
                        print("Raumfeld Device: ", host_path.group(1))
                    found_device = MediaDevice(udn, host_path.group(1), type, name)
                    found_device.upnp_service = self.get_zone_services(xmlListDevices, udn)
                    ZonesHandler.raumfeld_device.add(found_device)

    def get_zone_services(self, xmlListDevices, udn):
        devices = xmlListDevices.getElementsByTagName("device")
        try:
            for device in devices:
                if device.getAttribute('udn') == udn:
                    location = device.getAttribute('location')
                    upnp_service = UpnpService()
                    upnp_service.set_location(location)
                    return upnp_service

        except Exception as e:
            err_print("Error in regex find:{0}".format(e))
        return None

    def check_for_zone(self, ip):
        try:
            (xml_headers, xml_data) = UpnpSoap.get(ip + ":47365/getZones")
            (xml_headers_devices, xml_data_devices) = UpnpSoap.get(ip + ":47365/listDevices")

            # print(xml_data)
            if xml_data is not False:
                active_zones = []
                xml_root = minidom.parseString(xml_data)
                xml_root_devices = minidom.parseString(xml_data_devices)
                self.parse_devices_in_zone_raumfeld(xml_root_devices)
                zones = xml_root.getElementsByTagName("zone")
                ZonesHandler.renderers = list()
                for zone in zones:
                    try:
                        udn_id = zone.attributes["udn"].value
                        zone_obj = self.parse_rooms_in_zone_raumfeld(xml_root_devices, udn_id, zone)
                        zone_obj.services = self.get_zone_services(xml_root_devices, udn_id)
                        active_zones.append(zone_obj)
                    except Exception as e:
                        err_print("Warning: error on reading zone:{0}".format(e))
                try:
                    elements = xml_root.getElementsByTagName("unassignedRooms")
                    if len(elements) > 0:
                        unassigned = elements[0]
                        zone_obj = self.parse_rooms_in_zone_raumfeld(xml_root_devices, None, unassigned)
                        zone_obj.services = None
                        active_zones.append(zone_obj)
                except Exception as e:
                    err_print("Info: parsing unassignedRooms:{0}".format(e))
                    pass
                return active_zones
            else:
                return None
        except Exception as e:
            err_print("error on reading zones skipping:{0}".format(e))
        return None

    @staticmethod
    def hash_zone(zones):
        zone_hash = []
        for zone in zones:
            zone_hash.append(zone.get_control_hash())
        zone_hash.sort()
        return hashlib.md5(str(zone_hash).encode()).hexdigest()

    def reprocess(self):
        global raumfeldHostDevice
        try:
            if self.found_protocol_ip is None:
                self.found_protocol_ip = self.__get_host_ip_from_local()
            HostDevice.set(self.found_protocol_ip)
            zones = self.check_for_zone("http://" + self.found_protocol_ip)
            current_zone_hash = ZonesHandler.hash_zone(zones)
            if current_zone_hash != self.zone_hash:
                HostDevice.set(self.found_protocol_ip)
                self.set_active_zones(zones, current_zone_hash)
            return True
        except Exception as e:
            err_print("reprocess: " + str(e))
            return False

    def process_batch(self, lines, with_protocol):
        try:
            if with_protocol:
                manyips = re.findall("(https?://.*):", lines.decode('UTF-8'))
            else:
                manyips = re.findall("([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)", lines.decode('UTF-8'))
            new_zones = []
            ips = set(manyips)
            for ip in ips:

                protocol_ip = ip
                if not with_protocol:
                    protocol_ip = "http://" + ip
                zones = self.check_for_zone(protocol_ip)
                if zones is not None:
                    self.found_protocol_ip = ip
                    new_zones.extend(zones)
            zone_hash = ZonesHandler.hash_zone(self.active_zones)
            self.set_active_zones(new_zones, zone_hash)

        except Exception as e:
            err_print("process_batch: command failed:" + str(e))

    # this does not work on some macs
    def search_gssdp_service(self, service):
        if self.verbose:
            print("searching")
        command = 'gssdp-discover -n 3 | grep -A 1 ' + service
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except Exception as e:
            print("search_gssdp_service: command failed:" + str(e))
            syslog.syslog("command failed:" + str(e))
        lines = b""
        while True:
            nextline = process.stdout.readline()
            if len(nextline) == 0 and process.poll() != None:
                break
            lines += nextline
        self.process_batch(lines, True)
        exitCode = process.returncode
        if self.verbose:
            print("searching done")
        return exitCode


    def nmap_fallback(self):
        db = DiscoverByHttp()
        self.found_protocol_ip = db.found_IP()
        self.reprocess()
        return 0

    # this works on most, we could implement our own port 47365 search (very specific to raumfeld!)
    def search_nmap_range(self, iprange):
        lines = self.nmap_fallback()
        self.process_batch(lines, False)
        return 0
        """
        command = 'nmap --open -p 47365 ' + iprange
        if self.verbose:
            print("searching with command: " + command)
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except Exception as e:
            err_print("nmap: command failed:" + str(e))
            syslog.syslog("command failed:" + str(e))
            # should run a fallback now
            lines = self.nmap_fallback()
            self.process_batch(lines, False)
            return 0
        lines = b""
        while True:
            nextline = process.stdout.readline()
            if len(nextline) == 0 and process.poll() != None:
                break
            lines += nextline
        self.process_batch(lines, False)
        exitCode = process.returncode
        if self.verbose:
            err_print("searching done")
        return exitCode
        """

    def play_zone(self, name):
        for zone in self.active_zones:
            try:
                if zone.udn:
                    if zone.udn == name:
                        zone.play()
                        return
            except Exception as e:
                err_print("Error: command failed:" + str(e))

    def publish_state(self):
        string_state = self.get_state()
        print(str(string_state))

    def get_active_zones(self):
        return self.active_zones

    def get_zones_as_dict(self, verbosity=1):
        values = []
        index = 0
        for zone in self.active_zones:
            zone_dict = dict()
            try:
                if zone.udn:
                    zone.get_zone_stuff()
                if verbosity == 1:
                    zone_dict['index'] = str(index)
                zone_dict['media'] = zone.media
                zone_dict['host'] = str(zone.soap_host)
                zone_dict['name'] = zone.get_friendly_name()
                room_list = []
                for room in zone.rooms:
                    room_list.append([room.get_name(), room.get_udn()])
                room_list.sort()
                zone_dict['rooms'] = room_list
                zone_dict['udn'] = str(zone.udn)
                zone_dict['position'] = zone.position
                zone_dict['transport'] = zone.transport
                zone_dict['volume'] = zone.volume
                index += 1
            except Exception as e:
                pass
            values.append(zone_dict)

        values.sort(key=lambda k: k['name'])
        return values

    def get_all_rooms(self):
        room_list = dict()
        for zone in self.active_zones:
            try:
                for room in zone.rooms:
                    room_list.append({"zone": zone.udn, "room": room})
            except Exception as e:
                pass
        return room_list

    def get_current_media(self, param_dictionary):
        try:
            index = self.get_request_zone(param_dictionary)
            self.active_zones[index].update_media()
            return self.active_zones[index].media
        except Exception as e:
            err_print("error get_current_media {0}".format(e))

    def get_state(self):
        resstr = "current state"
        try:
            zones = self.get_zones_as_dict(1)
            for zone in zones:
                try:
                    resstr += "\nZone #" + zone['index'] + ": " + zone['name']
                    resstr += "\n      udn = " + zone['udn']
                    resstr += "\n     host = " + zone['host']
                    resstr += "\n  Room(s) : "
                    for room in zone['rooms']:
                        resstr += "\n          "
                        resstr += room[0]
                        resstr += ":" + room[1]
                    resstr += "\n   Volume = " + str(zone['volume'])
                except Exception as e:
                    resstr += "\nError: command failed:" + str(e)
                resstr += "\n"
            for item in ZonesHandler.media_servers:
                resstr += "Mediaserver = " + str(item.location) + "\n"
            resstr += "zone hash:" + self.zone_hash + "\n"
            return resstr
        except Exception as e:
            err_print("get_state error {0}".format(e))
        return resstr

    def create_zone_with_rooms(self, udn_list):
        pass

    def find_udn(self, udn):
        result_list = dict()
        for zone in self.get_active_zones():
            try:
                if zone.udn == udn:
                    result_list = dict({'type': 'zone', 'obj': zone})
                    return result_list
                for room in zone.rooms:
                    for renderer in room.get_renderer_list():
                        if renderer.get_udn() == udn:
                            result_list = dict({'type': 'room_renderer', 'obj': room})
                            return result_list
                        if room.get_udn() == udn:
                            result_list = dict({'type': 'room', 'obj': room})
                            return result_list
            except:
                pass
        return None

    def set_subscription_values(self, udn, xml_lastchange):
        state_var_items = XmlHelper.xml_extract_dict_by_val(xml_lastchange,
                                                            ['TransportState',
                                                             'AVTransportURIMetaData',
                                                             'AVTransportURI',
                                                             'CurrentPlayMode',
                                                             'CurrentTransportActions',
                                                             'CurrentTrack',
                                                             'CurrentTrackURI',
                                                             'CurrentTrackMetaData',
                                                             'CurrentTrackDuration',
                                                             'TransportStatus',
                                                             'TransportState',
                                                             'Mute',
                                                             'Volume'
                                                             ])
        if len(state_var_items):
            result = self.find_udn(udn)
            if result is not None:
                print("Notify UDN:", result['type'])
            else:
                print("Notify UDN {0} not found".format(udn))
            if result['type'] in ['room', 'room_renderer', 'zone']:
                result['obj'].set_event_update(udn, state_var_items)
            pprint(state_var_items, width=160)
            self.events_count += 1

    def browse_media(self, path):
        for server in self.media_servers:
            try:
                uc = UpnpCommand(server.location)
                res = uc.browsechildren(path)
                if res is None:
                    pass
                else:
                    return res
            except:
                pass

    def browse_info(self, path):
        for server in self.media_servers:
            uc = UpnpCommand(server.location)
            return uc.browse(path)

    def save_quick_access(self):
        values = dict()
        media_server_list = list()

        device_list = list()
        for renderer in self.renderers:
            device_dict = dict()
            try:
                device_dict['udn'] = str(renderer.udn)
                device_dict['location'] = str(renderer.location)
                device_dict['name'] = str(renderer.name)
            except Exception as e:
                pass
            device_list.append(device_dict)
        values['renderer'] = device_list

        device_list = list()
        for renderer in self.media_renderers:
            device_dict = dict()
            try:
                device_dict['udn'] = str(renderer.udn)
                device_dict['location'] = str(renderer.location)
                device_dict['type'] = str(renderer.type)
                device_dict['name'] = str(renderer.name)
            except Exception as e:
                pass
            device_list.append(device_dict)
        values['mediarenderer'] = device_list

        for server in self.media_servers:
            mserver_dict = dict()
            mserver_dict['udn'] = server.udn
            mserver_dict['type'] = server.type
            mserver_dict['location'] = server.location
            mserver_dict['services'] = server.upnp_service.services_list
            mserver_dict['name'] = str(server.name)
            media_server_list.append(mserver_dict)
        values['mediaserver'] = media_server_list

        values['host'] = str(self.found_protocol_ip)

        zone_list = list()
        for zone in self.active_zones:
            zone_dict = dict()
            try:
                zone_dict['host'] = str(zone.soap_host)
                zone_dict['name'] = zone.get_friendly_name()
                try:
                    zone_dict['services'] = zone.services.services_list
                except Exception as e:
                    pass
                room_list = []
                for room in zone.rooms:
                    room_config = dict()
                    room_config['name'] = room.get_name()
                    room_config['location'] = room.get_location()
                    room_config['udn'] = room.get_udn()
                    room_renderer = []
                    for renderer in room.get_renderer_list():
                        renderer_dict = dict()
                        renderer_dict['name'] = renderer.get_name()
                        renderer_dict['location'] = renderer.get_location()
                        renderer_dict['udn'] = renderer.get_udn()
                        room_renderer.append(renderer_dict)
                    room_config['room_renderers'] = room_renderer
                    room_list.append(room_config)
                zone_dict['rooms'] = room_list
                zone_dict['udn'] = str(zone.udn)
            except Exception as e:
                print("Error creating quickaccess object: {0}".format(e))
            zone_list.append(zone_dict)
        values['zones'] = zone_list

        device_list = list()
        for device in self.raumfeld_device:
            device_dict = dict()
            try:
                device_dict['udn'] = str(device.udn)
                device_dict['location'] = str(device.location)
                device_dict['type'] = str(device.type)
                device_dict['name'] = str(device.name)
            except Exception as e:
                pass
            device_list.append(device_dict)
        values['devices'] = device_list

        with open(Settings.home_directory()+"/data.json", 'w') as f:
            json.dump(values, f, ensure_ascii=True, sort_keys=True, indent=4)

    def __get_host_ip_from_local(self):
        try:
            s = open(Settings.home_directory()+"/data.json", 'r').read()
            quick_access = json.loads(s)
            return quick_access['host']
        except Exception as err:
            err_print("get_host_ip_from_local error: {0}".format(err))
        return None


def main(argv):
    if len(sys.argv) < 2:
        err_print("missing ip")
        sys.exit(2)
    host = sys.argv[1]
    zone = ZonesHandler()
    zone.process_batch(bytearray(host, "UTF-8"), False)
    print(zone.get_state())


if __name__ == "__main__":
    main(sys.argv)
