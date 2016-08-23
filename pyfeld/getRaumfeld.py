#!/usr/bin/env python3
from __future__ import unicode_literals

# GET https://172.31.0.102:48366/raumfeldSetup/v1/device
# IPs used for X-AuthKey: Server IP: 172.31.0.102 - Local IP: 172.31.0.100
# Request header:
# "Content-Type": "application/json"
# "X-AuthKey": "66a34279983ecbd09c22dc3ad84f58da63653f6eff8ce2058d97ff19c4d02daf"

"""
ADD:
SetRendererFilters
Calls RPC to set the filter params of a renderer.
udn: udn of the desired renderer
lo: the low frequency slider position in percent
mi: the mid frequency slider position in percent
hi: the high frequency slider position in percent

SetRendererLineinVolume
Calls RPC to set the linein volume of a renderer.
udn: udn of the desired renderer
volumeLevel: current volume level in percent

SetEqualizer
Changes the equalizer settings of a renderer.
udn: udn of the desired renderer
lo: the low frequency slider position in percent
mi: the mid frequency slider position in percent
hi: the high frequency slider position in percent

"""


import hashlib
import socket
import requests
import json
import sys
import xml.etree.ElementTree as ET

import subprocess
from time import sleep

class HostDevice:

    __raumfeld_host_device = None

    @staticmethod
    def set(ip):
        HostDevice.__raumfeld_host_device = RaumfeldDeviceSettings(ip)

    @staticmethod
    def get():
        return HostDevice.__raumfeld_host_device


class RaumfeldDeviceSettings:
    def __init__(self, server_ip):
        self.server_ip = server_ip
        self.model = "unknown"
        self.modelName = "unknown"
        self.modelNumber = "unknown"
        self.modelImageURL = "unknown"
        self.isAccessPoint = "unknown"
        self.isSetupInProgress = "unknown"
        self.deviceId = "unknown"
        self.state = "unknown"
        self.ssid = "unknown"
        self.renderer_uuid = "unknown"
        self.version = "unknown"
        self.valid = False
        self.local_ip = ""

    def set_verbose(self):
        self.verbose = True

    def retrieve_device_settings(self):
        self.local_ip = self.get_local_ip_address()
        json_result = self.get_hostdata("device")
        if json_result is None:
            return
        print(json_result.text)
        self.valid = True
        try:
            json_dict = json.loads(json_result.text)
            self.model = json_dict["model"]
            self.modelName = json_dict["modelName"]
            self.modelNumber = json_dict["modelNumber"]
            self.modelImageURL = json_dict["modelImageURL"]
            self.isAccessPoint = json_dict["isAccessPoint"]
            if 'isSetupInProgress' in json_dict:
                self.isSetupInProgress = json_dict["isSetupInProgress"]
            else:
                self.isSetupInProgress = "NA"

            headers = json_result.headers
            self.deviceId = headers['x-deviceid']

            result = self.get_hostdata("deviceConfiguration")
            if result is not None:
                json_dict = json.loads(result.text)
                if 'state' in json_dict:
                    self.state = json_dict['state']
                else:
                    self.state = "NA"
        except Exception as err:
            print("RaumfeldDeviceSettings.retrieve_device_settings Exception: {0}".format(err))
            return None
        self.get_zones()
        self.get_media_servers()
        print(self.get_info_str())

    def get_info_str(self):
        res =    "Model:        " + self.modelName
        res += "\nDeviceId:     " + self.deviceId
        res += "\nState:        " + self.state
        res += "\n"
        return res

    def create_auth_key(self):
        hash = hashlib.sha256()
        hash.update(bytes(self.server_ip, 'UTF-8'))
        hash.update(b"$392G3hJ7Dl3qZ4")
        hash.update(bytes(self.local_ip, 'UTF-8'))
        hash_result = hash.hexdigest()
        return hash_result

    @staticmethod
    def get_local_ip_address():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            res = s.getsockname()[0]
            print("Local IP address:" + res)
            return res
        except Exception as err:
            print("Exception get_local_ip_address: {0}".format(err))
            return None

    def get_media_servers(self):
        try:
            requests.packages.urllib3.disable_warnings()
            url = "http://"+self.server_ip+":47365/getMediaServers"
            print(url)
            r = requests.get(url)
            root = ET.fromstring(r.content)
            #print(ET.dump(root))

            #for atype in root.findall('mediaserver'):
            for child in root:
                print("+", child.tag, child.get('name'), child.get('udn'))
            return r
        except Exception as err:
            print("Exception get_media_servers: {0}".format(err))
            return None

    def create_zone_with_rooms(self, rooms):
        try:
            requests.packages.urllib3.disable_warnings()
            url = "http://" + self.server_ip + ":47365/connectRoomsToZone?"
            url += "roomUDNs="
            for item in rooms:
                url += item+","
            url = url[:-1]
            r = requests.get(url)
            return r

        except Exception as err:
            print("Exception create_zone_with_rooms: {0}".format(err))
            return None

    def add_rooms_to_zone(self, zone_udn, rooms):
        try:
            requests.packages.urllib3.disable_warnings()
            url = "http://" + self.server_ip + ":47365/connectRoomsToZone?"
            url += "zoneUDN=" + zone_udn
            url += "&roomUDNs="
            for item in rooms:
                url += item+","
            url = url[:-1]
            print(url)
            r = requests.get(url)
            return r

        except Exception as err:
            print("Exception create_zone_with_rooms: {0}".format(err))
        return None

    def set_room_standby(self, uuid, state):
        if state == 'on':
            cmd = "enterManualStandby"
        elif state == 'off':
            cmd = "leaveStandby"
        elif state == 'auto':
            cmd = "enterAutomaticStandby"
        else:
            raise "standby with unknown state called (use on|off|auto)"
        try:
            requests.packages.urllib3.disable_warnings()
            url = "http://" + self.server_ip + ":47365/"+cmd+"?"
            url += "&roomUDN=" + uuid
            r = requests.get(url)
            return r

        except Exception as err:
            print("Exception create_zone_with_rooms: {0}".format(err))
        return None

    def drop_room(self, room_udn):
        try:
            requests.packages.urllib3.disable_warnings()
            url = "http://" + self.server_ip + ":47365/dropRoomJob?"
            url += "&roomUDN=" + room_udn
            r = requests.get(url)
            return r

        except Exception as err:
            print("Exception create_zone_with_rooms: {0}".format(err))
            return None

    def get_zones(self):
        try:
            requests.packages.urllib3.disable_warnings()
            url = "http://"+self.server_ip+":47365/getZones"
            print(url)
            r = requests.get(url)
            root = ET.fromstring(r.content)
            #print(ET.dump(root))

            for atype in root.findall('zones'):
                for child in atype:
                    print(child.tag, child.get('udn'))
                    for room in child:
                        print("+", room.tag, room.get('name'), room.get('udn'))
                        for renderer in room:
                            print("  +", renderer.tag, renderer.get('name'), renderer.get('udn'))
            return r
        except Exception as err:
            print("Exception get_zones: {0}".format(err))
            return None

    def get_hostdata(self, what):
        try:
            requests.packages.urllib3.disable_warnings()
            # print("---> ", socket.gethostname ())
            # self.local_ip = socket.gethostbyname(socket.gethostname())

            headers = {"Content-Type": "application/json",
                       "X-AuthKey": self.create_auth_key()}
            url = "https://"+self.server_ip+":48366/raumfeldSetup/v1/" + what
            print(url)
            r = requests.get(url, headers=headers, verify=False)
            return r
        except Exception as err:
            print("Exception get_hostdata: {0}".format(err))
            return None

    def get_host_id(self):
        return self.host_id

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("usage: "+sys.argv[0]+" <raumfeld-device ip>")
        sys.exit(2)
    ds = RaumfeldDeviceSettings(sys.argv[1])
    ds.set_verbose()
    ds.retrieve_device_settings()

