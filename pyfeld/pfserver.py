#!/usr/bin/env python3

"""


http://172.31.0.10:28282/text/play/album/1
http://192.168.2.115:8082/scjurgen/text/search/mymusic/albums/what
http://192.168.2.115:8082/scjurgen/text/play/album/1

pyfeld -d browse "0/Renderers/uuid:1dfc5e0f-bfcd-40f1-b1cd-0c2fbfb7637a/StationButtons"
C 0/Renderers/uuid:1dfc5e0f-bfcd-40f1-b1cd-0c2fbfb7637a/StationButtons/595 * "Awaken, My Love!"
+ 0/Renderers/uuid:1dfc5e0f-bfcd-40f1-b1cd-0c2fbfb7637a/StationButtons/687 * Antenne Brandenburg vom rbb
+ 0/Renderers/uuid:1dfc5e0f-bfcd-40f1-b1cd-0c2fbfb7637a/StationButtons/689 * Deutschlandradio Kultur

"""
import argparse
import json
import mimetypes
import telnetlib
import threading

from concurrent.futures import thread
from datetime import time, datetime

from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer, urllib

from os import unlink

from pyfeld.settings import Settings
from pyfeld.upnpCommand import UpnpCommand
from rfcmd import RfCmd
from socket import *
from time import sleep

import logging

LOG_FILENAME = Settings.home_directory()+'/pfserver.log'
unlink(LOG_FILENAME)
logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG)

logging.debug('This message should go to the log file')

def get_template(filename):
    with open(filename, "rb") as f:
        r = f.read()
    return r.decode("utf-8")

rewrite_pages = [  # const
        ['^/(.*)(html|ico|js|ttf|svg|woff|eot|otf|css|less|map).*$', './html/\\1\\2'],
        ['^/$', './html/index.html']
]


"""
handle a request
current schemes
/stop/{room}
/searchandplay/{origin}/{name}/{room}
/search/{origin}/{name}
/play/station/{#}/{room}

origin := radio | fm | usb |
room := all | {defined rooms from RfCmd.get_rooms}. -> if no room given lastroom
lastroom := room

predefined search containers:
0/RadioTime/local
0/RadioTime/{etc.}
0/My Music/Albums
0/My Music/AllTracks
0/My Music/Titles


other ideas:

s&p -> keep lastlist
/vol/lower  /higher  /very low
/eq/bass/min /max /more
/next/song
/pre/album
/whatisplayingnow
/playposition
/saveasfavorite/#
/play/favorite/#
/status
/seekto/#:#
/gostandby/
/repeat/

save last: room, list, volume, song
"""

class Model:
    def __init__(self):
        self.data_dict = dict()

    def set_state(self, key, value):
        self.data_dict[key] = value

    def get_state(self, key):
        if key in self.data_dict:
            return self.data_dict[key]
        else:
            return None

    def get_states(self):
        return self.data_dict

    def get_info(self):
        result = ""
        for item in self.data_dict:
            result += "\n" + item.first + ":" + item.second
        return result

    def load_states(self):
        try:
            s = open(Settings.home_directory() + "/pfserver.json", 'r').read()
            self.data_dict = json.loads(s)
        except:
            pass

    def save_states(self):
        with open(Settings.home_directory()+"/pfserver.json", 'w') as f:
            json.dump(self.data_dict, f, ensure_ascii=True, sort_keys=True, indent=4)

model = Model()
model.load_states()


def is_an_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def get_template(filename):
    with open(filename, "rb") as f:
        r = f.read()
    return r.decode("utf-8")


def create_search_path(origin, where):
    if origin.lower() in ["mymusic", "my%20music", "usb", "music"]:
        origin = "My Music"
    if where.lower() in ['album', 'albums']:
        where = 'Albums'
    if where.lower() in ['trackartists', 'artists', 'artist']:
        where = 'TrackArtists'
    if where.lower() in ['Composers', 'composer']:
        where = 'Composers'
    if where.lower() in ['', 'all', 'alltracks']:
        where = 'AllTracks'
    path = "0/"+origin+"/Search/" + where
    print("path="+path)
    return path

def search(origin, where, name):
    path = create_search_path(origin, where)
    title = "dc:title contains " + name
    uc_media = UpnpCommand(RfCmd.rfConfig['mediaserver'][0]['location'])
    jsonResult = uc_media.search(path, title, "json")
    real_json = json.loads(jsonResult)
    if len(real_json) > 0:
        response = ""
        i = 0
        for obj in real_json:
            i += 1
            itemIndex = where + " " + str(i)
            model.set_state(itemIndex, obj)
            response += itemIndex + ": " + obj['title'] + ", "
        return jsonResult, response
    else:
        return "[]", "Sorry! Couldn't find {0} in {1}".format(name, origin)


def play_this(song):
    uc = UpnpCommand(RfCmd.rfConfig['zones'][0]['host'])
    udn = RfCmd.rfConfig['mediaserver'][0]['udn']
    transport_data = dict()
    browseresult = uc_media.browsechildren(song)
    if browseresult is None:
        browseresult = uc_media.browse(song)
        transport_data['CurrentURI'] = RfCmd.build_dlna_play_single(udn, "urn:upnp-org:serviceId:ContentDirectory", song)
    else:
        transport_data['CurrentURI'] = RfCmd.build_dlna_play_container(udn, "urn:upnp-org:serviceId:ContentDirectory", song)
    transport_data['CurrentURIMetaData'] = '<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dlna="urn:schemas-dlna-org:metadata-1-0/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" xmlns:raumfeld="urn:schemas-raumfeld-com:meta-data/raumfeld"><container></container></DIDL-Lite>'
    uc.set_transport_uri(transport_data)
    didlExtract = RfCmd.get_didl_extract(browseresult['Result'], 'dict')
    return didlExtract['title']


def playAbleItems():
    return ['object.item.audioItem.musicTrack'
            , 'object.container.album.musicAlbum'
            , 'object.container.trackContainer.allTracks']


def search_and_play(origin, where, name, room):
    if room != '':
        model.set_state('lastroom', room)
    else:
        room = model.get_state('lastroom')
    path = create_search_path(origin, where)
    title = "dc:title contains " + name
    uc_media = UpnpCommand(RfCmd.rfConfig['mediaserver'][0]['location'])
    jsonResult = uc_media.search(path, title, "json")
    real_json = json.loads(jsonResult)
    if len(real_json) > 0:
        if real_json[0]['class'] in playAbleItems():
            play_this(real_json[0]['idPath'])
            model.set_state('songlist', real_json)
            return jsonResult, "Es spielt jetzt {0}".format(real_json[0]['title'])
        if real_json[0]['class'] == 'object.container.person.musicArtist':
            jsonResult = uc_media.browse_recursive_children(real_json[0]['idPath'], 0, "json")
            real_json = json.loads(jsonResult)
            if len(real_json) > 0:
                if real_json[0]['class'] in playAbleItems():
                    model.set_state('songlist', real_json)
                    play_this(real_json[0]['idPath'])
                    return jsonResult, "Es spielt jetzt  {0}".format(real_json[0]['title'])
    return "[]", "Folgendes konnte Raumfeld nicht finden: {0} in {1}".format(name, origin)


def createzone_if_room_unassigned(roomName):
    zoneIndex = RfCmd.get_room_zone_index(roomName)
    if "unassigned room" == RfCmd.rfConfig['zones'][zoneIndex]['name']:
        RfCmd.raumfeld_host_device.create_zone_with_rooms([roomName,])
        sleep(2)
        RfCmd.discover()


def handle_volume(arg1, arg2):
    get_volume = False
    if arg1 == "":
        get_volume = True
    elif is_an_int(arg1) and arg2 == "":
        value = int(arg1)
    elif is_an_int(arg2):
        handle_room(arg1)
        value = int(arg2)
    room_name = model.get_state('room')

    createzone_if_room_unassigned(room_name)

    zone_index = RfCmd.get_room_zone_index(room_name)
    uc = UpnpCommand(RfCmd.rfConfig['zones'][zone_index]['host'])
    udn = RfCmd.get_room_udn(room_name)
    if get_volume:
        volume = uc.get_room_volume(udn, "plain")
        result = "Volume in room {} is {}".format(room_name, volume)
        dict_result = {"result": volume}
    else:
        uc.set_room_volume(udn, value)
        result = "Volume {} set in room {}".format(value, room_name)
        dict_result = {"result": value}
    return json.dumps(dict_result), result


def play(what, which, room):
    if room != '':
        model.set_state('lastroom', room)
    else:
        room = model.get_state('lastroom')
    if what == 'localradio':
        browse_query = "0/RadioTime/LocalRadio"
        uc_media = UpnpCommand(RfCmd.rfConfig['mediaserver'][0]['location'])
        jsonResult = uc_media.browse_recursive_children(browse_query, 0, "json")
        real_json = json.loads(jsonResult)
        if len(real_json) > 0:
            if is_an_int(which):
                song = real_json[int(which)]['idPath']
                play_this(song)
                result = "Ich spiele jetzt {}".format(real_json[int(which)]['title'])
        return "[]", result

    if what == 'station':
        udn = RfCmd.get_udn_from_renderer_by_room(room)
        if udn is None:
            return "[]", "Ein Fehler ist aufgetreten. Renderer fuer raum {} wurde nicht gefunden. Mist!".format(room)
        browse_query = "0/Renderers/{0}/StationButtons".format(udn)
        uc_media = UpnpCommand(RfCmd.rfConfig['mediaserver'][0]['location'])
        jsonResult = uc_media.browse_recursive_children(browse_query, 0, "json")
        real_json = json.loads(jsonResult)
        if len(real_json) > 0:
            if is_an_int(which):
                song = real_json[int(which)]['idPath']
                play_this(song)
                result = "Ich spiele jetzt {}".format(real_json[int(which)]['title'])
        return "[]", result
    itemIndex = what + " " + str(which)
    try:
        obj = model.get_state(itemIndex)
        play_this(obj['idPath'])
        return obj, "playing {0}".format(obj['title'])
    except:
        return "[]", "Sorry! Couldn't play {0} {1} in room {2}".format(what, which, room)

def get_status():
    text = RfCmd.get_info(0, 'text')
    json = RfCmd.get_info(0, 'json')
    return json, text

def handle_room(room_name):
    room_dict = {'room': room_name+' not found'}
    textresult = "The Room " + room_name + " has not been found!"
    zoneIndex = RfCmd.get_room_zone_index(room_name)
    if zoneIndex != -1:
        if RfCmd.is_unassigned_room(room_name):
            udn = RfCmd.get_room_udn(room_name)
            #raumfeld_host_device.create_zone_with_rooms(rooms)
            #RfCmd.create_zone(roomName)
        model.set_state('lastroom', room_name)
        textresult = room_name + " is active"
        room_dict = {'room': room_name+' is active'}
    return json.dumps(room_dict), textresult


def handle_path_request(path):
    try:
        json_result = ""
        print("requestpath:" + path)
        text_result = "Sorry! Did not understand what you are looking for! Request wants a format like text or json!"
        padded_path = path + "//////"

        components = padded_path.split('/')
        request_format = components[1]
        if request_format in ['text', 'json']:
            if components[2] == 'room':
                json_result, text_result = handle_room(components[3])
            elif components[2] == 'volume':
                json_result, text_result = handle_volume(components[3], components[4])
            elif components[2] == 'searchandplay':
                json_result, text_result = search_and_play(components[3], components[4], components[5], components[6])
            elif components[2] == 'search':
                json_result, text_result = search(components[3], components[4], components[5])
            elif components[2] == 'play':
                json_result, text_result = play(components[3], components[4], components[5])
            elif components[2] == 'status':
                json_result, text_result = get_status()

            if request_format == 'text':
                return text_result
            if request_format == 'json':
                return json_result
        return text_result
    except Exception as e:
        if request_format == 'text':
            return "an error occured: {}".format(e)
        if request_format == 'json':
            return json_result
            return "{\"error\":\"{}\"}".format(e)



class RequestHandler (BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def page_not_found(self):
        self.send_response(404)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        output = '{"errors":[{"status": 404, "message": "page not found: '+self.path+'"}]}'
        self.wfile.write(bytearray(output, 'UTF-8'))

    def send_json_response(self, json_string):
        try:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(bytearray(json_string, 'UTF-8'))
        except Exception as e:
            print("handle_get_query error {0}".format(e))

    def handle_infos(self, type):
        try:
            if type == 'status':
                output = RfCmd.get_info(0,  "json")
            elif type == 'rooms':
                output = RfCmd.get_rooms(0, "json")
            elif type == 'zones':
                output = RfCmd.get_zone_info("json")
            self.send_json_response(output)
        except Exception as e:
            print("handle_get_query error {0}".format(e))

    def do_GET(self):
        try:
            if self.path == '/':
                output = get_template("info.html")
                self.send_response(200)
                self.send_header("Content-type", "text/html")
            elif self.path == '/text/search':
                output = "search in mymusic: album  all artists or composer."
                output += "search in radio: album  all artists or composer."
                self.send_header("Content-type", "text/html")
                self.send_response(200)
            elif self.path == '/debug':
                output = json.dumps(model.get_states())
                self.send_response(200)
                self.send_header("Content-type", "application/json")
            else:
                output = handle_path_request(self.path)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b"\n")
            self.wfile.write(bytearray(output, 'UTF-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            output = "Internal server error:<br/> {0}".format(e)
            self.wfile.write(bytearray(output, 'UTF-8'))


def open_info_channel(ip, port):
    pass


def scan_raumfeld():
    while 1:
        print("discovery")
        RfCmd.discover()
        print("done")
        model.save_states()
        sleep(120)


running = True


def call_forwarder(host, port):
    global running
    while running:
        try:
            tn = telnetlib.Telnet(host, port)
        except:
            print("no telnet server {}:{}".format(host, port))
            sleep(10)
            continue
        try:
            print("connected to telnet server {}:{}".format(host, port))

            tn.read_until(b"login:")
            tn.write(b"#id scjurgen\n")
            tn.read_until(b"password:")
            tn.write(b"#pwd bogus\n")
            tn.read_until(b"ok")
            while True:
                print("waiting for data")
                received_data = tn.read_until(b"\n")
                data = received_data.decode('utf-8')
                print(data)
                try:
                    if data.startswith('#keep-alive'):
                        res = '{ "result":"#alive ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f") + '"}\n'
    #                    tn.write(b"{ \"result\":\"#ack\"}\n")
    #                    print(res)
                        tn.write(res.encode('Utf-8'))
                    elif data.startswith('#alexa '):
                        dataset = data.split(' ', 2)
                        msg_number = dataset[1]
                        data = dataset[2].rstrip()
                        res = "#ack {} {}\n".format(msg_number, handle_path_request(data))
                        tn.write(res.encode('utf-8'))
                except Exception as e:
                    print("error occured {}".format(e))
        except Exception as e:
            print("error occured {}".format(e))
            print("peer reset connection {}:{}".format(host, port))
            sleep(1)


def run_server(host, port):
    threading.Thread(target=scan_raumfeld).start()
    try:
        print("Starting json server {}:{}".format(host, int(port)))
        server = HTTPServer((host, int(port)), RequestHandler)
        server.serve_forever()
    except Exception as e:
        print("run_Server error:"+str(e))


def get_local_ip_address():
    s = socket(AF_INET, SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='pfserver,A.K.A. Raumfeldserver with pyfeld.')
    parser.add_argument('--telnetserverip', default="127.0.0.1", help='Address of telnet server in the cloud')
    parser.add_argument('--telnetserverport', default='4445', help='Port of telnet server in the cloud')
    parser.add_argument('--localport', default='8088', help='local port for eventual rest interface')
    arglist = parser.parse_args()

    threading.Thread(target=call_forwarder, args=[arglist.telnetserverip, arglist.telnetserverport]).start()

    #UpnpCommand.overwrite_user_agent("Raumfeld-Control/1.0")
    RfCmd.discover()
    uc_media = UpnpCommand(RfCmd.rfConfig['mediaserver'][0]['location'])
    this_servers_ip = get_local_ip_address()
    run_server(this_servers_ip, arglist.localport)
