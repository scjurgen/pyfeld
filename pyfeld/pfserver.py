#!/usr/bin/env python3
"""


urls to implement:
current/volume
current/title
current/room

action/lower

C 0/My Music/Artists * Artists
C 0/My Music/Albums * Albums
C 0/My Music/Genres * Genres
C 0/My Music/Composers * Composers
C 0/My Music/ByFolder * By Folder
C 0/My Music/RecentlyAdded * Recently Added
C 0/My Music/AllTracks * All Tracks
C 0/My Music/Favorites * Raumfeld Favourites
C 0/My Music/Search * Search

C 0/Playlists/MyPlaylists * Raumfeld Playlists
C 0/Playlists/Imported * Imported Playlists
C 0/Playlists/Shuffles * Shuffles

C 0/Favorites/MyFavorites * Favourites
C 0/Favorites/RecentlyPlayed * Last Played
C 0/Favorites/MostPlayed * Personal Trends

C 0/Tidal/New * New
C 0/Tidal/Moods * Playlists
C 0/Tidal/Recommended * Recommended
C 0/Tidal/Genres * Genres
C 0/Tidal/TopLists * Charts
C 0/Tidal/MyWiMP * My Music
C 0/Tidal/Search * Search
C 0/Tidal/Favorites * Raumfeld Favourites

C 0/RadioTime/CategoryMusic * Music
C 0/RadioTime/CategoryTalk * Talk
C 0/RadioTime/CategorySports * Sports
C 0/RadioTime/LocalRadio * Local
C 0/RadioTime/Favorites * Raumfeld Favourites
C 0/RadioTime/Search * Search


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
import html.parser

from concurrent.futures import thread
from datetime import time, datetime

from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer, urllib

from os import unlink
from urllib import parse

from pyfeld.didlInfo import DidlInfo

from pyfeld.settings import Settings
from pyfeld.upnpCommand import UpnpCommand
from pyfeld.rfcmd import RfCmd
from socket import *
from time import sleep

import logging


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

list_of_actions = []

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


def get_room_uc():
    zoneIndex = RfCmd.get_room_zone_index(model.get_state('lastroom'))
    return UpnpCommand(RfCmd.rfConfig['zones'][zoneIndex]['host'])


def tellme_search_pathes():
    return ['album', 'my music', 'artist', 'composer', 'all']

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
    zoneIndex = RfCmd.get_room_zone_index(model.get_state('lastroom'))

    uc = UpnpCommand(RfCmd.rfConfig['zones'][zoneIndex]['host'])
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


def human_handle_volume(val):
    if is_an_int(val):
        return ['absolute', int(val)]
    if val == 'low':
        return ['absolute', 20]
    if val == 'medium':
        return ['absolute', 40]
    if val == 'high':
        return ['absolute', 60]
    if val == 'whisper':
        return ['absolute', 10]
    if val == 'loud':
        return ['absolute', 70]
    if val == 'lower':
        return ['relative', -5]
    if val == 'much lower':
        return ['relative', -20]
    if val == 'higher':
        return ['relative', 5]
    if val == 'much higher':
        return ['relative', 20]
    return None


def handle_volume(arg1, arg2=''):
    get_volume = False
    if arg1 == "":
        get_volume = True
    else:
        value = human_handle_volume(arg1)
        if value is not None and arg2 == "":
            pass
        else:
            value = human_handle_volume(arg2)
            if value is not None and arg2 == "":
                handle_room(arg1)
    room_name = model.get_state('lastroom')
    createzone_if_room_unassigned(room_name)

    uc = get_room_uc()
    udn = RfCmd.get_room_udn(room_name)
    if get_volume:
        volume = uc.get_room_volume(udn, "plain")
        result = "Lautstärke im Raum {} ist {}".format(room_name, volume)
        dict_result = {"result": volume}
    else:
        if value[0] == 'relative':
            volume = int(uc.get_room_volume(udn, "plain"))
            volume += value[1]
            if volume < 0:
                volume = 0
            elif volume > 100:
                volume = 100
        else:
            volume = value[1]
        uc.set_room_volume(udn, volume)
        result = "Lautstärke {} in Raum {}".format(volume, room_name)
        dict_result = {"result": volume}
    return json.dumps(dict_result), result


def play_browse_content(browse_query, onebased_index, room_name):
    uc_media = UpnpCommand(RfCmd.rfConfig['mediaserver'][0]['location'])
    jsonResult = uc_media.browse_recursive_children(browse_query, 0, "json")
    real_json = json.loads(jsonResult)
    if len(real_json) > 0:
        if is_an_int(onebased_index):
            model.set_state("currentlist", real_json)
            song = real_json[int(onebased_index)]['idPath']
            play_this(song)
            result = "Es spielt jetzt {} in raum {}".format(real_json[int(onebased_index)]['title'], room_name)
    return "[]", result


def play_station(onebased_index, room_name):
    udn = RfCmd.get_udn_from_renderer_by_room(room_name)
    if udn is None:
        return "[]", "Ein Fehler ist aufgetreten. Renderer fuer Raum {} wurde nicht gefunden. Mist!".format(room_name)
    browse_query = "0/Renderers/{0}/StationButtons".format(udn)
    uc_media = UpnpCommand(RfCmd.rfConfig['mediaserver'][0]['location'])
    jsonResult = uc_media.browse_recursive_children(browse_query, 0, "json")
    real_json = json.loads(jsonResult)
    if len(real_json) > 0:
        if is_an_int(onebased_index):
            model.set_state("currentlist", real_json)
            song = real_json[int(onebased_index)]['idPath']
            play_this(song)
            result = "Es spielt jetzt {} in raum {}".format(real_json[int(onebased_index)]['title'], room_name)
    return "[]", result


def play(what, onebased_index, room_name):
    if room_name != '':
        model.set_state('lastroom', room_name)
    else:
        room_name = model.get_state('lastroom')
    createzone_if_room_unassigned(room_name)
    if what == 'radio':
        return play_browse_content("0/RadioTime/LocalRadio", onebased_index, room_name)
    elif what == 'station':
        return play_station(onebased_index, room_name)
    elif what in ['mostplayed', 'lieblings musik']:
        return play_browse_content("0/Favorites/MostPlayed", onebased_index, room_name)
#    itemIndex = " " + str(onebased_index)
#    try:
#        obj = model.get_state(itemIndex)
#        play_this(obj['idPath'])
#        return obj, "playing {0}".format(obj['title'])
#    except:
    return "[]", "Sorry! Couldn't play {0} {1} in room {2}".format(what, onebased_index, room_name)


def get_status():
    text = RfCmd.get_info(0, 'text')
    json = RfCmd.get_info(0, 'json')
    return json, text


def handle_transportaction(action):
    if action == 'stop':
        get_room_uc().stop()
    if action in ['next', 'weiter']:
        get_room_uc().next()
    if action == ['prev', 'previous', 'vorher', 'vorheriges']:
        get_room_uc().previous()
    if action == 'pause':
        get_room_uc().pause()
    return "[]", "ok"


def handle_action(action):
    if action == 'leiser':
        return handle_volume('lower')
    if action == 'lauter':
        return handle_volume('higher')
    if action == 'leise':
        return handle_volume('low')
    if action == 'laut':
        return handle_volume('high')
    if action in ['stop', 'next', 'prev', 'pause', 'weiter', 'vorher']:
        return handle_transportaction(action)
    return "[]", "Das weiss raumfeld nicht? Das ist wirklich doof, nicht wahr?! Frage Juergen dass er das macht!"

def play_at(time_point, what, index):
    list_of_actions.append([time_point, 'play', what, index])
    return "[]", "Ok! Um {} spiele ich dann {} {}, aber bitte ... nicht erschrecken!".format(time_point, what, int(index)+1)



def handle_info(info):
    found = False
    if info == 'room':
        textresult = model.get_state('lastroom')
    if info == 'title':
        results = get_room_uc().get_position_info()
        print(results)
        textresult = ""
        if is_an_int(results['Track']):
            track = int(results['Track'])
            if track != 0:
                textresult = "Track {} ".format(track)
        if 'DIDL-Lite' in results['TrackMetaData']:
            didlinfo = DidlInfo(results['TrackMetaData'], True).get_items()
            print(didlinfo)
            textresult += didlinfo['title']
            if didlinfo['album']!='':
                textresult += " album: "+didlinfo['album']
        else:
            textresult += "kein titel gefunden"

        media_info = get_room_uc().get_media_info()
        try:
            if 'CurrentURIMetaData' in media_info:
                didlinfo = DidlInfo(media_info['CurrentURIMetaData']).get_items()
                media = didlinfo['title']
                textresult += " info: " + media
        except:
            pass

    if info == 'remaining':
        results = get_room_uc().get_position_info()
        print(results)
        duration = RfCmd.timecode_to_seconds(results['TrackDuration'])
        currentPosition = RfCmd.timecode_to_seconds(results['RelTime'])
        if duration == 0:
            textresult = "keine track information vorhanden"
        else:
            seconds = duration-currentPosition
            minutes = int(seconds / 60)
            seconds = seconds % 60
            textresult = ""
            if minutes == 1:
                textresult = "1 minute"
            elif minutes:
                textresult = "{} minutes".format(minutes)
            if seconds:
                textresult += " {} seconds".format(seconds)

    return "[]", textresult

def handle_room(room_name):
    room_dict = {'room': room_name+' not found'}
    found = False
    textresult = room_name + " nicht gefunden"
    zoneIndex = RfCmd.get_room_zone_index(room_name)
    if zoneIndex != -1:
        if RfCmd.is_unassigned_room(room_name):
            udn = RfCmd.get_room_udn(room_name)
            #raumfeAld_host_device.create_zone_with_rooms(rooms)
            #RfCmd.create_zone(roomName)
        model.set_state('lastroom', room_name)
        textresult = room_name + " is active"
        room_dict = {'room': room_name+' is active'}
        found = True

    if not found:
        textresult = "Der Raum " + room_name + " ist nicht auffindbar!"
        output = RfCmd.get_rooms(0, "plain")
        output = output.replace("\n", ", ")
        textresult += " Wir haben hier: " + output

    return json.dumps(room_dict), textresult


def handle_path_request(path):
    try:
        try:
            path = parse.unquote(path)
        except Exception as e:
            return "an error occured: {}".format(e)
        print("requestpath:" + path)
        text_result = "Sorry! Did not understand what you are looking for! Request wants a format like text or json!"
        padded_path = path + "//////"

        components = padded_path.split('/')
        request_format = components[1]
        if request_format in ['text', 'json']:
            if components[2] in ['room','raum']:
                json_result, text_result = handle_room(components[3])
            elif components[2] == 'info':
                json_result, text_result = handle_info(components[3])
            elif components[2] == 'action':
                json_result, text_result = handle_action(components[3])
            elif components[2] == 'volume':
                json_result, text_result = handle_volume(components[3], components[4])
            elif components[2] == 'searchandplay':
                json_result, text_result = search_and_play(components[3], components[4], components[5], components[6])
            elif components[2] == 'search':
                json_result, text_result = search(components[3], components[4], components[5])
            elif components[2] == 'play':
                json_result, text_result = play(components[3], components[4], components[5])
            elif components[2] == 'playat':
                json_result, text_result = play_at(components[3], components[4], components[5])
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
        sleep(60)


running = True


def call_forwarder(host, port):
    global running
    while running:
        try:
            tn = telnetlib.Telnet(host, port)
        except:
            print("no server {}:{}".format(host, port))
            sleep(10)
            continue
        try:
            print("connected to server {}:{}".format(host, port))

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


def timed_action():
    global list_of_actions
    while 1:
        current_time = datetime.now().strftime('%H:%M')
        print(current_time)
        for value in list_of_actions:
            if value[0] == current_time:
                value[0] = 'done'
                if value[1] == 'play':
                    play(value[2], value[3], "")
                print(list_of_actions)
        sleep(10)

def run_server(host, port):
    threading.Thread(target=scan_raumfeld).start()
    threading.Thread(target=timed_action).start()
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


def run_main():
    global uc_media

    LOG_FILENAME = Settings.home_directory() + '/pfserver.log'
    unlink(LOG_FILENAME)
    logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG)

    logging.debug('This message should go to the log file')

    parser = argparse.ArgumentParser(description='pfserver,A.K.A. Raumfeldserver with pyfeld.')
    parser.add_argument('--telnetserverip', default="127.0.0.1", help='Address of telnet server in the cloud')
    parser.add_argument('--telnetserverport', default='24445', help='Port of telnet server in the cloud')
    parser.add_argument('--localport', default='8088', help='local port for eventual rest interface')
    arglist = parser.parse_args()

    threading.Thread(target=call_forwarder, args=[arglist.telnetserverip, arglist.telnetserverport]).start()

    #UpnpCommand.overwrite_user_agent("Raumfeld-Control/1.0")
    RfCmd.discover()
    uc_media = UpnpCommand(RfCmd.rfConfig['mediaserver'][0]['location'])
    this_servers_ip = get_local_ip_address()
    run_server(this_servers_ip, arglist.localport)

if __name__ == "__main__":
    run_main()


