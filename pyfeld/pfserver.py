#!/usr/bin/env python3

"""
macronize rfcmd values
create intelligent room name handling
search deeper (create permutations of search string with typical errors, is there a google service)
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
from pyfeld.rfcmd import RfCmd


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


def search_and_play(origin, name, room):
    """
    /searchandplay/{origin}/{name}/{room}
    :param origin:radio | my music | everywhere
    :param name: searchname
    :param room: target room to play
    :return: textual description of playing item or "couldn't find searchname"
    """
    if room != '':
        model.set_state('lastroom', room)
    else:
        room = model.get_state('lastroom')
    path = "0/My Music/Search/AllTracks"
    title = "dc:title contains "+name
    uc_media = UpnpCommand(RfCmd.rfConfig['mediaserver'][0]['location'])
    jsonResult = uc_media.search(path, title, "json")
    real_json = json.loads(jsonResult)
    if len(real_json) > 0:
        print(real_json[0]['title'])
        print(real_json[0]['artist'])
        print(real_json[0]['idPath'])
        return "[]", "playing {0} by {1}".format(real_json[0]['title'], real_json[0]['artist'])
    else:
        return "[]", "Sorry! Couldn't find {0} in {1}".format(name, origin)


def handle_volume(room, value):
    if value != '':
        uc = UpnpCommand(RfCmd.rfConfig['zones'][0]['host'])
        udn = RfCmd.get_room_udn(room)
        result = uc.set_room_volume(udn, value)
        return result
    else:
        uc = UpnpCommand(RfCmd.rfConfig['zones'][0]['host'])
        udn = RfCmd.get_room_udn(room)
        result = uc.get_room_volume(udn, value, "json")
        return result
    return "Sorry! Couldn't find {0} in {1}".format(name, origin)


def handle_path_request(path):
    print("requestpath:" + path)
    text_result = "Sorry! Did not understand what you are looking for!"
    padded_path = path + "//////"
    components = padded_path.split('/')
    if components[1] == 'volume':
        json_result, text_result = handle_volume(components[2], components[3])
    if components[1] == 'searchandplay':
        json_result, text_result = search_and_play(components[2], components[3], components[4])

    results = {'textresponse': text_result}
    return json_result


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
            output = "Internal server error {0}".format(e)
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
    RfCmd.discover()
    uc_media = UpnpCommand(RfCmd.rfConfig['mediaserver'][0]['location'])
    this_servers_ip = get_local_ip_address()
    run_server(this_servers_ip, 28282)

