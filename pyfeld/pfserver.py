#!/usr/bin/env python3

"""

http://172.31.0.10:28282/text/search/mymusic/album/sh
http://172.31.0.10:28282/text/play/album/1

pyfeld -d browse "0/Renderers/uuid:1dfc5e0f-bfcd-40f1-b1cd-0c2fbfb7637a/StationButtons"
C 0/Renderers/uuid:1dfc5e0f-bfcd-40f1-b1cd-0c2fbfb7637a/StationButtons/595 * "Awaken, My Love!"
+ 0/Renderers/uuid:1dfc5e0f-bfcd-40f1-b1cd-0c2fbfb7637a/StationButtons/687 * Antenne Brandenburg vom rbb
+ 0/Renderers/uuid:1dfc5e0f-bfcd-40f1-b1cd-0c2fbfb7637a/StationButtons/689 * Deutschlandradio Kultur

"""

import mimetypes
import json
import threading
from concurrent.futures import thread

from socket import *

from http.server import HTTPServer, urllib
from http.server import BaseHTTPRequestHandler

from datetime import time
from time import sleep

from pyfeld.upnpCommand import UpnpCommand
from rfcmd import RfCmd


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

    def get_states(self, key):
        return self.data_dict

    def get_info(self):
        result = ""
        for item in self.data_dict:
            result += "\n" + item.first + ":" + item.second
        return result


model = Model()

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
            return jsonResult, "playing {0}".format(real_json[0]['title'])
        if real_json[0]['class'] == 'object.container.person.musicArtist':
            jsonResult = uc_media.browse_recursive_children(real_json[0]['idPath'], 0, "json")
            real_json = json.loads(jsonResult)
            if len(real_json) > 0:
                if real_json[0]['class'] in playAbleItems():
                    model.set_state('songlist', real_json)
                    play_this(real_json[0]['idPath'])
                    return jsonResult, "playing {0}".format(real_json[0]['title'])
    return "[]", "Sorry! Couldn't find {0} in {1}".format(name, origin)


def handle_volume(arg1, arg2):
    if arg1 == "":
        getVolume = True
        return "can't get volume"

    zoneIndex = RfCmd.get_room_zone_index(roomName)
    print("Room found in zone ", zoneIndex)
    if zoneIndex == -1:
        print("ERROR: room with name '{0}' not found".format(roomName))
        print("Available rooms are to be found here:\n" + RfCmd.get_info(False))
        return
    if RfCmd.is_unassigned_room(roomName):
        print('error: room is unassigned: ' + roomName)
        return
    uc = UpnpCommand(RfCmd.rfConfig['zones'][zoneIndex]['host'])
    udn = RfCmd.get_room_udn(roomName)
    result = uc.set_room_volume(udn, value)
    return result

def play(what, which):
    pass


def handle_room(roomName):
    room_dict = {'room':'not found'}
    textresult = "The Room " + roomName " has not been found!"
    zoneIndex = RfCmd.get_room_zone_index(roomName)
    if zoneIndex == -1:
        return "the room "
    if RfCmd.is_unassigned_room(roomName):
    model.set_state('room', components[3])
    return textresult, json.dumps(room_dict)

def handle_path_request(path):
    json_result = ""
    print("requestpath:" + path)
    text_result = "Sorry! Did not understand what you are looking for!"
    padded_path = path + "//////"

    components = padded_path.split('/')
    format = components[1]
    if format in ['text', 'json']:
        if components[2] == 'room':
            json_result, text_result = handle_room(components[3])
        if components[2] == 'volume':
            json_result, text_result = handle_volume(components[3], components[4])
        if components[2] == 'searchandplay':
            json_result, text_result = search_and_play(components[3], components[4], components[5], components[6])
        if components[2] == 'search':
            json_result, text_result = search(components[3], components[4], components[5])
        if components[2] == 'play':
            json_result, text_result = play(components[3], components[4])
        if format == 'text':
            return text_result
        if format == 'json':
            return json_result
    return text_result


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


def open_info_channel(server):
    pass


def scan_raumfeld():
    while 1:
        print("discovery")
        RfCmd.discover()
        print("done")
        sleep(120)


def run_server(host, port):
    threading.Thread(target=scan_raumfeld).start()
    try:
        print("Starting json server {}:{}".format(host, port))
        server = HTTPServer((host, port), RequestHandler)
        server.serve_forever()
    except Exception as e:
        print("run_Server error:"+str(e))


def get_local_ip_address():
    s = socket(AF_INET, SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


if __name__ == "__main__":
    UpnpCommand.overwrite_user_agent("RaumfeldControl")
    RfCmd.discover()
    uc_media = UpnpCommand(RfCmd.rfConfig['mediaserver'][0]['location'])
    this_servers_ip = get_local_ip_address()
    run_server(this_servers_ip, 28282)

