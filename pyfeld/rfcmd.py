#!/usr/bin/env python3
from __future__ import unicode_literals

import json
import subprocess
import sys
import urllib
import urllib3
try:
    from texttable import Texttable
except:
    pass

from requests.utils import quote

from time import sleep

from pyfeld.settings import Settings
from pyfeld.upnpCommand import UpnpCommand
from pyfeld.getRaumfeld import RaumfeldDeviceSettings
from pyfeld.zonesHandler import ZonesHandler
from pyfeld.didlInfo import DidlInfo

version = "0.9.3"

quick_access = dict()
raumfeld_host_device = None

class InfoList:
    def __init__(self, sortItem, others):
        self.sortItem = sortItem
        self.others = others

    def get_list(self):
        return self.sortItem + self.others


class RfCmd:

    @staticmethod
    def get_raumfeld_infrastructure():
        global quick_access, raumfeld_host_device
        try:
            s = open(Settings.home_directory()+"/data.json", 'r').read()
            quick_access = json.loads(s)
            """sanitize"""
            for zone in quick_access['zones']:
                if not 'rooms' in zone:
                    zone['rooms'] = None
                if not 'udn' in zone:
                    zone['udn'] = None
            raumfeld_host_device = RaumfeldDeviceSettings(quick_access['host'])
        except Exception as err:
            print("get_raumfeld_infrastructure: Exception: {0}".format(err))
            return None


    '''
    most stuff is already in the zone handler, this needs some tidy up
    '''

    @staticmethod
    def get_renderer_udn(renderer_name):
        global quick_access
        for zone in quick_access['zones']:
            if zone['rooms'] is not None:
                for room in zone['rooms']:
                    for renderer in room.get_renderer_list():
                        if renderer['name'] == renderer_name:
                            return renderer['udn']
        return None

    @staticmethod
    def get_room_udn(room_name):
        global quick_access
        for zone in quick_access['zones']:
            if zone['rooms'] is not None:
                for room in zone['rooms']:
                    if room['name'] == room_name:
                        return room['udn']
        return None

    @staticmethod
    def get_room_zone_index(room_name):
        global quick_access
        index = 0
        for zone in quick_access['zones']:
            if zone['rooms'] is not None:
                for room in zone['rooms']:
                    if room['name'] == room_name:
                        return index
            index += 1
        return -1

    @staticmethod
    def build_dlna_play_container(udn, server_type, path):
        s = "dlna-playcontainer://" + quote(udn)
        s += "?"
        s += 'sid=' + quote(server_type)
        s += '&cid=' + quote(path)
        s += '&md=0'
        return s


    @staticmethod
    def build_dlna_play_single(udn, server_type, path):
        s = "dlna-playsingle://" + quote(udn)
        s += "?"
        s += 'sid=' + quote(server_type)
        s += '&iid=' + quote(path)
        return s


    @staticmethod
    def is_unassigned_room(roomName):
        global quick_access
        for zone in quick_access['zones']:
            if zone['rooms'] is not None:
                if zone['name'] == 'unassigned room':
                    for room in zone['rooms']:
                        if roomName == room['name']:
                            return True
        return False


    @staticmethod
    def get_unassigned_rooms(verbose, format):
        global quick_access

        result = ""
        for zone in quick_access['zones']:
            if zone['rooms'] is not None:
                if zone['name'] == 'unassigned room':
                    for room in zone['rooms']:
                        result += room['name'] + '\n'
        return result

    @staticmethod
    def get_renderer(verbose, format):
        global quick_access
        result = ""
        for renderer in quick_access['renderer']:
            if verbose == 2:
                result += renderer['location'] + "\t"
            if verbose == 1:
                result += RfCmd.get_pure_ip(renderer['location']) + "\t"
            result += renderer['name'] + '\n'
        return result

    @staticmethod
    def get_pure_ip(url):
        loc = urllib3.util.parse_url(url)
        return loc.hostname

    @staticmethod
    def map_ip_to_friendly_name(ip):
        global quick_access
        for zone in quick_access['zones']:
            if zone['rooms'] is not None:
                for room in zone['rooms']:
                    if RfCmd.get_pure_ip(room['location']) == ip:
                        return room['name']
                    for renderer in room['room_renderers']:
                        if RfCmd.get_pure_ip(renderer['location']) == ip:
                            return renderer['name']
        return None

    @staticmethod
    def map_udn_to_friendly_name(udn):
        global quick_access
        for zone in quick_access['zones']:
            if zone['rooms'] is not None:
                if zone['udn'] == udn:
                    return zone['name']
                for room in zone['rooms']:
                    if room['udn'] == udn:
                        return room['name']
                    for renderer in room['room_renderers']:
                        if renderer['udn'] == udn:
                            return renderer['name']
        return None

    @staticmethod
    def get_device_ips(verbose, format):
        global quick_access
        result = ""
        ip_list = []
        host_is_set = False
        for device in quick_access['devices']:
            ip_l = urllib3.util.parse_url(device['location'])
            if ip_l.host == quick_access['host']:
                ip_list.append(InfoList(ip_l.host, str(RfCmd.map_ip_to_friendly_name(ip_l.host)) + " <host>"))
                host_is_set = True
            else:
                ip_list.append(InfoList(ip_l.host, str(RfCmd.map_ip_to_friendly_name(ip_l.host))))
        if not host_is_set:
            ip_list.append(InfoList(quick_access['host'], "<host>"))
        ip_list.sort(key=lambda x: x.sortItem, reverse=False)
        if format == 'json':
            return json.dumps(ip_list) + "\n"
        f_list = []
        for ip in ip_list:
            if ip.sortItem not in f_list:
                f_list.append(ip.sortItem)
        if format == 'list':
            return f_list
        if verbose:
            for item in ip_list:
                result += item.sortItem + "\t" + item.others + "\n"
        else:
            for ip in f_list:
                result += ip + "\n"
        return result


    @staticmethod
    def get_device_location_by_udn(udn):
        global quick_access
        for zone in quick_access['zones']:
            for room in zone['rooms']:
                for renderer in room['room_renderers']:
                    if renderer['udn'] == udn:
                        loc = urllib3.util.parse_url(renderer['location'])
                        return loc.netloc
                if room is not None:
                    if room['udn'] == udn:
                        loc = urllib3.util.parse_url(room['location'])
                        return loc.netloc
        return None


    @staticmethod
    def get_rooms(verbose, format):
        global quick_access
        result = ""
        room_list = []
        for zone in quick_access['zones']:
            for room in zone['rooms']:
                if room is not None:
                    room_name = room['name']
                    if verbose:
                        room_name += ":"+room['location']
                    room_list.append(room_name)
        room_list.sort()

        if format == 'json':
            result += '['
            cnt = 0
            for r in room_list:
                result += '"' + r + '",'
                cnt += 1
            if cnt != 0:
                result = result[:-1] + ']\n'
            else:
                result = '[]\n'
        else:
            for r in room_list:
                result += r + "\n"
        return result


    @staticmethod
    def get_didl_extract(didl_result, format="plain"):
        didlinfo = DidlInfo(didl_result, True)
        items = didlinfo.get_items()
        if format == 'json':
            return json.dumps(items, sort_keys=True, indent=2)
        else:
            result = ""
            result += items['artist'] + "\n"
            result += items['title'] + "\n"
            result += items['album'] + "\n"
            result += items['resSampleFrequency'] + "\n"
            result += items['resSourceType'] + "\n"
            result += items['resBitrate'] + "\n"
            result += items['rfsourceID'] + "\n"
        return result


    @staticmethod
    #what should we do here i.e. pack vol, eq, balance?
    def get_room_info(uc, udn):
        result = uc.get_room_volume(udn)


    @staticmethod
    def get_specific_zoneinfo(uc, format):
        results = uc.get_position_info()
        if format == 'json':
            result = '{ "AbsTime" : '
            if 'AbsTime' in results:
                result += '"' + results['AbsTime'] + '",\n'
            else:
                result += '"",\n'
            result += '"TrackDuration" : '
            if 'TrackDuration' in results:
                result += '"' + results['TrackDuration'] + '",\n'
            else:
                result += '"",\n'
            result += '"TrackMetaData" : '
            if 'TrackMetaData' in results:
                result += RfCmd.get_didl_extract(results['TrackMetaData'], format)
            result += '}'
            return result
        else:

            result = ""
            if 'AbsTime' in results:
                result += results['AbsTime'] + "\n"
            else:
                result += "\n"
            if 'TrackDuration' in results:
                result += results['TrackDuration'] + "\n"
            else:
                result += "\n"
            if 'TrackMetaData' in results:
                result += RfCmd.get_didl_extract(results['TrackMetaData'])
            return result


    @staticmethod
    def get_info(verbose, format):
        global quick_access
        if format == 'json':
            return json.dumps(quick_access, sort_keys=True, indent=2) + "\n"
        else:
            i = 0
            result = ""
            for media_server in quick_access['mediaserver']:
                if verbose >= 1:
                    result += "Mediaserver #{0} : {1}\n".format(i, media_server['udn'])
                else:
                    result += "Mediaserver #{0}\n".format(i)
                i += 1
            i = 0
            for zone in quick_access['zones']:
                if verbose == 2:
                    result += "Zone #{0} : {1} : {2} -> {3}\n".format(i, zone['name'], str(zone['udn']), zone['host'])
                elif verbose == 1:
                    result += "Zone #{0} : {1} : {2}\n".format(i, zone['name'], str(zone['udn']))
                else:
                    result += "Zone #{0} : {1}\n".format(i, zone['name'])
                if zone['rooms'] is not None:
                    for room in zone['rooms']:
                        if verbose == 2:
                            result += "\tRoom '{0}' : {1} -> {2}\n".format(room['name'], room['udn'], room['location'])
                        elif verbose == 1:
                                result += "\tRoom '{0}' : {1}\n".format(room['name'], room['udn'])
                        else:
                            result += "\tRoom '{0}'\n".format(room['name'])
                        for renderer in room['room_renderers']:
                            if verbose == 2:
                                result += "\t\tRenderer '{0}' : {1} -> {2}\n".format(renderer['name'], renderer['udn'],
                                                                                     renderer['location'])
                            elif verbose == 1:
                                result += "\t\tRenderer '{0}' : {1}\n".format(renderer['name'], renderer['udn'])
                            else:
                                result += "\t\tRenderer '{0}'\n".format(renderer['name'])   #.
                    i += 1
        return result



    @staticmethod
    def get_play_info(verbose, format):
        global quick_access
        result = ""
        maxsize = 10
        for zone in quick_access['zones']:
            if zone['rooms'] is not None:
                if len(zone['name']) > maxsize:
                    maxsize = len(zone['name'])
        maxsize += 2
        result_list = list()
        result_list.append(["Zone","Vol","Track","Length","Pos","Src","BR","Src","Track title","Track Info"])
        for zone in quick_access['zones']:
            if zone['rooms'] is not None:
                single_result = list()
                uc = UpnpCommand(zone['host'])
                single_result.append(zone['name'])
                single_result.append(uc.get_volume())
                results = uc.get_position_info()
                single_result.append(str(results['Track']))
                single_result.append(str(results['TrackDuration']))
                single_result.append(str(results['AbsTime']))
                if 'DIDL-Lite' in results['TrackMetaData']:
                    didlinfo = DidlInfo(results['TrackMetaData'], True).get_items()
                    single_result.append(didlinfo['resSourceType'])
                    single_result.append(didlinfo['resBitrate'])
                    single_result.append(didlinfo['resSourceName'])
                    single_result.append(didlinfo['title'])
                else:
                    single_result.append("-")
                    single_result.append("-")
                    single_result.append("-")
                    single_result.append("-")

                media_info = uc.get_media_info()
                if 'CurrentURIMetaData' in media_info:
                    didlinfo = DidlInfo(media_info['CurrentURIMetaData']).get_items()
                    media = didlinfo['title']
                    single_result.append(media)
                else:
                    single_result.append("-")
                result_list.append(single_result)
        t = Texttable(250)
        t.add_rows(result_list)
        return t.draw()

    @staticmethod
    def get_zone_info(format):
        result = ""
        if format == 'json':
            result = json.dumps(quick_access['zones'], sort_keys=True, indent=2) + "\n"
        else:
            for zone in quick_access['zones']:
                if zone['rooms'] is not None:
                    if zone['name'] != "unassigned room":
                        result += zone['name']
                        result += '\n'
        return result


    @staticmethod
    def timecode_to_seconds(tc):
        components = tc.split(':')
        return int(components[0]) * 3600 + int(components[1]) * 60 + int(components[2])


    #unsused variables are used in the evil eval code
    @staticmethod
    def wait_operation(uc, condition):
        while True:
            result = uc.get_volume()
            volume = int(result['CurrentVolume'])
            results = uc.get_position_info()

            try:
                didlinfo = DidlInfo(results['TrackMetaData'])
                items = didlinfo.get_items()
                #print(items)
                title = items['title']
                artist = items['artist']
            except:
                pass

            track = -1
            if 'Track' in results:
                track = int(results['Track'])
            duration = -1
            if 'TrackDuration' in results:
                duration = RfCmd.timecode_to_seconds(results['TrackDuration'])
            position = -1
            if 'AbsTime' in results:
                position = RfCmd.timecode_to_seconds(results['AbsTime'])
            #print(volume, duration, position)
            eval_result = eval(condition)
            if eval_result:
                break
            sleep(1)
        return condition


    @staticmethod
    def fade_operation(uc, time, volume_start, volume_end):
        t = 0
        while t < time:
            volume_now = volume_start+(volume_end-volume_start)*t/time
            uc.set_volume(volume_now)
            sleep(1)
            t += 1
        uc.set_volume(volume_end)
        return "done"

    @staticmethod
    def discover():
        zones_handler = ZonesHandler()
        if not zones_handler.reprocess():
            local_ip = RaumfeldDeviceSettings.get_local_ip_address()
            zones_handler.search_nmap_range(local_ip + "/24")
            zones_handler.publish_state()
        RfCmd.get_raumfeld_infrastructure()

    @staticmethod
    def find_renderer(name):
        global quick_access
        for renderer in quick_access['renderer']:
            if name == renderer['name']:
                return RfCmd.get_pure_ip(renderer['location'])
        return None

    @staticmethod
    def find_device(name):
        global quick_access
        if name in '<host>':
            return quick_access['host']
        for device in quick_access['devices']:
            ip_l = urllib3.util.parse_url(device['location'])
            if str(RfCmd.map_ip_to_friendly_name(ip_l.host)) == name:
                return ip_l.host
        return None

def usage(argv):
    print("Usage: " + argv[0] + " [OPTIONS] [COMMAND] {args}")
    print("Version: " + version)
    print("OPTIONS: ")
    print("  -j,--json                 Use json as output format, default is plain text lines")
    print("  -u,--udn  udn             Specify room by udn rather by name")
    print("  -d,--discover             Discover again (will be fast if host didn't change)")
    print("     --zonebyudn #          Specify zone by udn")
    print("  -z,--zone #               Specify zone index (use info to get a list), default 0 = first")
    print("  -r,--zonewithroom name    Specify zone index by using room name")
    print("  -s,--renderer name        Specify renderer by using renderer name")
    print("  -e,--device name          specify device by name, special case is <host> as name")
    print("  -m,--mediaserver #        Specify media server, default 0 = first")
    print("  -v,--verbose              Increase verbosity (use twice for more)")

    print("COMMANDS: (some commands return xml)")
    print("  browse path               Browse for media append /* for recursive")
    print("  play browseitem           Play item in zone i.e. play '0/My Music/Albums/TheAlbumTitle'")
    print("  pause|stop|prev|next      Control currently playing items in zone")
#    print("  currentsong              show current song info")
    print("  volume #                  Set volume of zone")
    print("  getvolume                 Get volume of zone")
    print("  roomvolume room  #        Set volume of room")
    print("  roomgetvolume room        Get volume of room")
    print("  roomgeteq room            Get equalizer settings of device")
    print("  mute #                    Set mute state")
    print("  getmute                   Get mute state of zone")
    print("  roommute room #           Mute room")
    print("  roomgetmute room          Get mute state of room")
    print("  roomgeteq room            Get equalizer settings of device")
    print("  roomseteq room L M H      Set equalizer device Low Mid High range is -1536 to 1536")
    print("  position                  Get position info of zone")
    print("  seek #                    Seek to a specific position")
    print("  standby state {room(s)}   Set a room into standby state=on/off/auto")
    print("INFOS: (return lists of easily parsable text/json)")
    print("  host                      print host ip")
    print("  rooms                     Show list of rooms ordererd alphabetically")
    print("  deviceips                 Show list of devices (rooms/host) ip address (verbose shows name)")
    print("  renderer                  Show list of renderer names (verbose shows ip)")
    print("  unassignedrooms           Show list of unassigned rooms")
    print("  zoneinfo                  Show info on zone")
    print("  zones                     Show list of zones, unassigned room is skipped")
    print("  info                      Show list of zones, rooms and renderers")
    print("  playinfo                  Show playing info of renderers")
    # print("  examples                  Show commandline examples")
    print("#MACRO OPERATIONS")
    print("  wait condition            wait for condition (expression) [volume, position, duration, title, artist] i.e. volume < 5 or position==120 ")
    print("  fade time vols vole       fade volume from vols to vole in time seconds ")
    print("#ZONE MANAGEMENT (will automatically discover after operating)")
    print("  createzone {room(s)}      create zone with list of rooms (space seperated)")
    print("  addtozone {room(s)}       add rooms to existing zone")
    print("  drop {room(s)}            drop rooms from it's zone")
    print("#SSH ")
    print("  ssh {command...}          send command to given device, device is determined by --renderer or --device")

sshcmd = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@"
scpcmd = "scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "


def retrieve(cmd):
    try:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        return 0
    lines = ""
    while True:
        nextline = process.stdout.readline()
        if len(nextline) == 0 and process.poll() != None:
            break
        lines += nextline.decode('utf-8')
    return lines


def single_device_command(ip, cmd):
    cmd = sshcmd + ip + " " + cmd
    print("running cmd on device {0}: {1}".format(ip, cmd))
    lines = retrieve(cmd)
    print("result from {0}".format(ip))
    return lines


#TODO: this thing is ugly big and needs refactoring

def run_main():
    global quick_access
    argv = list()
    for arg in sys.argv:
        argv.append(arg)
    verbose = 0
    if len(argv) < 2:
        usage(argv)
        sys.exit(2)
    target_device = None
    zoneIndex = -1
    mediaIndex = 0
    room = ""
    device_format = "named"
    format = "plain"
    argpos = 1
    RfCmd.get_raumfeld_infrastructure()

    while argv[argpos].startswith('-'):
        if argv[argpos].startswith('--'):
            option = argv[argpos][2:]
        else:
            option = argv[argpos]
        argpos += 1
        if option == 'verbose' or option == '-v':
            verbose += 1
        elif option == '-vv':
            verbose += 2
        elif option == 'help' or option == '-h':
            usage(argv)
            sys.exit(2)
        elif option == 'renderer' or option == '-s':
            target_device = RfCmd.find_renderer(argv[argpos])
            argpos += 1
        elif option == 'device' or option == '-e':
            target_device = RfCmd.find_device(argv[argpos])
            argpos += 1
        elif option == 'udn' or option == '-u':
            device_format = "udn"
        elif option == 'json' or option == '-j':
            format = "json"
        elif option == 'discover' or option == '-d':
            RfCmd.discover()
            uc = UpnpCommand(quick_access['zones'][zoneIndex]['host'])
            if argpos == len(argv):
                print("done")
                sys.exit(0)
        elif option == 'zonebyudn':
            found = False
            for index, zone in enumerate(quick_access['zones']):
                if argv[argpos] == zone['udn']:
                    zoneIndex = index
                    uc = UpnpCommand(quick_access['zones'][zoneIndex]['host'])
                    found = True
            if not found:
                print("Zoneudn {0} not found".format(argv[argpos]))
                sys.exit(-1)
            argpos += 1
        elif option == 'zone' or option == '-z':
            zoneIndex = int(argv[argpos])
            uc = UpnpCommand(quick_access['zones'][zoneIndex]['host'])
            argpos += 1
        elif option == 'zonewithroom' or option == '-r':
            roomName = argv[argpos]
            zoneIndex = RfCmd.get_room_zone_index(roomName)
            if verbose:
                print("Room found in zone ", zoneIndex)
            if zoneIndex == -1:
                print("ERROR: room with name '{0}' not found".format(roomName))
                print("Available rooms are to be found here:\n" + RfCmd.get_info(verbose))
                exit(-1)
            if RfCmd.is_unassigned_room(roomName):
                print('error: room is unassigned: ' + roomName)
                exit(-1)
            uc = UpnpCommand(quick_access['zones'][zoneIndex]['host'])
            argpos += 1
        elif option == 'mediaserver' or option == '-m':
            mediaIndex = int(argv[argpos])
            argpos += 1
        else:
            print("unknown option --{0}".format(option))
            usage(argv)
            sys.exit(2)

    if zoneIndex == -1:
        zoneIndex = 0
        uc = UpnpCommand(quick_access['zones'][0]['host'])

    uc_media = UpnpCommand(quick_access['mediaserver'][mediaIndex]['location'])
    operation = argv[argpos]
    argpos += 1
    result = None

    if operation == 'play':
        udn = quick_access['mediaserver'][mediaIndex]['udn']
        transport_data = dict()
        browseresult = uc_media.browsechildren(argv[argpos])
        if browseresult is None:
            browseresult = uc_media.browse(argv[argpos])
            transport_data['CurrentURI'] = RfCmd.build_dlna_play_single(udn, "urn:upnp-org:serviceId:ContentDirectory", argv[argpos])
        else:
            transport_data['CurrentURI'] = RfCmd.build_dlna_play_container(udn, "urn:upnp-org:serviceId:ContentDirectory",
                                                                     argv[argpos])
        print("URI", argv[argpos], transport_data['CurrentURI'])
        transport_data['CurrentURIMetaData'] = '<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dlna="urn:schemas-dlna-org:metadata-1-0/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" xmlns:raumfeld="urn:schemas-raumfeld-com:meta-data/raumfeld"><container></container></DIDL-Lite>'
        uc.set_transport_uri(transport_data)
        result = 'ok'
    elif operation == 'pause':
        result = uc.pause()
    elif operation == 'stop':
        result = uc.stop()
    elif operation == 'next':
        result = uc.next()
    elif operation == 'prev':
        result = uc.previous()
    elif operation == 'roomgetinfo':
        if device_format == 'udn':
            udn = argv[argpos]
        else:
            udn = RfCmd.get_room_udn(argv[argpos])
        result = RfCmd.get_room_info(uc, udn)
    elif operation == 'volume' or operation == 'setvolume':
        if device_format == 'udn':
            for renderer in quick_access['renderer']:
                if renderer['udn'] == argv[argpos]:
                    host = urllib3.util.parse_url(renderer['location'])
                    uc = UpnpCommand(host.netloc)
            argpos += 1
            result = uc.set_volume_by_udn(argv[argpos])
        else:
            result = uc.set_volume(argv[argpos])
    elif operation == 'getvolume':
        if device_format == 'udn':
            for renderer in quick_access['renderer']:
                if renderer['udn'] == argv[argpos]:
                    host = urllib3.util.parse_url(renderer['location'])
                    uc = UpnpCommand(host.netloc)
            result = uc.get_volume_by_udn(format)
        else:
            result = uc.get_volume(format)
    elif operation == 'roomgetvolume':
        if device_format == 'udn':
            udn = argv[argpos]
        else:
            udn = RfCmd.get_room_udn(argv[argpos])
        result = uc.get_room_volume(udn)
    elif operation == 'roomsetvolume':
        if device_format == 'udn':
            udn = argv[argpos]
        else:
            udn = RfCmd.get_room_udn(argv[argpos])
        argpos += 1
        result = uc.set_room_volume(udn, argv[argpos])
    elif operation == 'mute' or operation == 'setmute':
        result = uc.set_mute(argv[argpos])
    elif operation == 'getmute':
        result = uc.get_mute(format)
    elif operation == 'roomgetmute':
        if device_format == 'udn':
            udn = argv[argpos]
        else:
            udn = RfCmd.get_room_udn(argv[argpos])
        result = uc.get_room_mute(udn)
    elif operation == 'roomsetmute':
        if device_format == 'udn':
            udn = argv[argpos]
        else:
            udn = RfCmd.get_room_udn(argv[argpos])
        argpos += 1
        result = uc.set_room_mute(udn, argv[argpos])
    elif operation == 'roomgeteq':
        if device_format == 'udn':
            udn = argv[argpos]
        else:
            udn = RfCmd.get_room_udn(argv[argpos])
        location = RfCmd.get_device_location_by_udn(udn)
        urc = UpnpCommand(location)
        result = urc.get_filter(format)
    elif operation == 'roomseteq':
        if device_format == 'udn':
            udn = argv[argpos]
        else:
            udn = RfCmd.get_room_udn(argv[argpos])
        location = RfCmd.get_device_location_by_udn(udn)
        urc = UpnpCommand(location)
        result = urc.set_filter(argv[argpos + 1], argv[argpos + 2], argv[argpos + 3])
    elif operation == 'roomgetbalance':
        if device_format == 'udn':
            udn = argv[argpos]
        else:
            udn = RfCmd.get_room_udn(argv[argpos])
        location = RfCmd.get_device_location_by_udn(udn)
        urc = UpnpCommand(location)
        result = urc.get_balance(format)
    elif operation == 'roomsetbalance':
        if device_format == 'udn':
            udn = argv[argpos]
        else:
            udn = RfCmd.get_room_udn(argv[argpos])
        location = RfCmd.get_device_location_by_udn(udn)
        urc = UpnpCommand(location)
        result = urc.set_balance(argv[argpos+1])
    elif operation == 'standby':
        state = argv[argpos]
        argpos += 1
        while argpos < len(argv):
            udn = RfCmd.get_room_udn(argv[argpos])
            if udn is None:
                print("unknown room "+argv[argpos])
            else:
                raumfeld_host_device.set_room_standby(str(udn), state)
            argpos += 1
    elif operation == 'position':
        results = uc.get_position_info()
        if format == 'json':
            return json.dumps(results,  sort_keys=True, indent=2) + '\n'
        else:
            result = ""
            if 'TrackDuration' in results:
                result += str(results['TrackDuration'])
            result += '\n'
            if 'AbsTime' in results:
                result += str(results['AbsTime'])
            result += '\n'
    elif operation == 'seek':
        #check argv[argpos] if contains :
        result = uc.seek(argv[argpos])
    elif operation == 'wait':
        result = RfCmd.wait_operation(uc, argv[argpos])
    elif operation == 'fade':
        result = RfCmd.fade_operation(uc, int(argv[argpos]), int(argv[argpos+1]), int(argv[argpos+2]))
    elif operation == 'createzone':
        rooms = set()
        result = "zone creation adding rooms:\n"
        while argpos < len(argv):
            if device_format == 'udn':
                udn = argv[argpos]
            else:
                udn = RfCmd.get_room_udn(argv[argpos])
            result += "{0}'\n".format(str(udn))
            rooms.add(str(udn))
            argpos += 1
        raumfeld_host_device.create_zone_with_rooms(rooms)
        sleep(2)
        RfCmd.discover()
    elif operation == 'addtozone':
        zone_udn = quick_access['zones'][zoneIndex]['udn']
        rooms = set()
        result = "zone creation adding rooms:\n"
        while argpos < len(argv):
            if device_format == 'udn':
                udn = argv[argpos]
            else:
                udn = RfCmd.get_room_udn(argv[argpos])
            result += "{0}'\n".format(str(udn))
            rooms.add(str(udn))
            argpos += 1
        raumfeld_host_device.add_rooms_to_zone(zone_udn, rooms)
        sleep(2)
        RfCmd.discover()
    elif operation == 'drop':
        result = "drop rooms from zone:\n"
        while argpos < len(argv):
            if device_format == 'udn':
                udn = argv[argpos]
            else:
                udn = RfCmd.get_room_udn(argv[argpos])
            result += str(raumfeld_host_device.drop_room(str(udn)))
            argpos += 1
        sleep(2)
        RfCmd.discover()
    elif operation == 'browse':
        if argv[argpos].endswith('/*'):
            result = uc_media.browse_recursive_children(argv[argpos][:-2], 3, format)
        else:
            result = uc_media.browse_recursive_children(argv[argpos], 0, format)
    elif operation == 'browseinfo':
        results = uc_media.browse(argv[argpos])
        result = RfCmd.get_didl_extract(results['Result'], format)
    elif operation == 'search':
        result = uc_media.search(argv[argpos], argv[argpos+1], format)
    elif operation == 'rooms':
        result = RfCmd.get_rooms(verbose, format)
        result = result[:-1]
    elif operation == 'urls':
        result = ""
    elif operation == 'host':
        result = raumfeld_host_device.server_ip
    elif operation == 'deviceips':
        result = RfCmd.get_device_ips(verbose, format)
        result = result[:-1]
    elif operation == 'renderer':
        result = RfCmd.get_renderer(verbose, format)
        result = result[:-1]
    elif operation == 'unassignedrooms':
        result = RfCmd.get_unassigned_rooms(verbose, format)
        result = result[:-1]
    elif operation == 'zones':
        result = RfCmd.get_zone_info(format)
        result = result[:-1]
    elif operation == 'zoneinfo':
        result = RfCmd.get_specific_zoneinfo(uc, format)
        result = result[:-1]
    elif operation == 'info':
        result = RfCmd.get_info(verbose, format)
        result = result[:-1]
    elif operation == 'playinfo':
        result = RfCmd.get_play_info(verbose, format)
        result = result[:-1]
    elif operation == 'ssh':
        combined_args = " ".join(argv[argpos:])
        result = single_device_command(target_device, combined_args)
    else:
        usage(argv)
    if result is not None:
        sys.stdout.write(result)
    sys.stdout.write('\n')

if __name__ == "__main__":
    run_main()
