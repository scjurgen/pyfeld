#!/usr/bin/env python3


"""
-> json

GET /{where}/{identifier}/{command}/values

where:=room|zone|udn|all
identifier:=byname|udn|#
command:=volume/eq/play
values:=browsepath/#/

GET /room/name/volume
GET /zone/number/volume
GET /udn/volume

POST/GET /room/volume/#

GET /browse/path --> json

"""

import mimetypes
import json
import re
import threading
from concurrent.futures import thread

from socket import *

from http.server import HTTPServer, urllib
from http.server import BaseHTTPRequestHandler

from datetime import time
from time import sleep

from pyfeld.rfcmd import RfCmd


def get_template(filename):
    with open(filename, "rb") as f:
        r = f.read()
    return r.decode("utf-8")

rewrite_pages = [  # const
        ['^/(.*)(html|ico|js|ttf|svg|woff|eot|otf|css|less|map).*$', './html/\\1\\2'],
        ['^/$', './html/index.html']
]

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

    def handle_button_query(self, param):
        try:
            output = '{"error":"possible"}'
            cmd = param['cmd'][0]
            if cmd in model.kv:
                if 'value' in param:
                    value = param['value'][0]
                    model.set_value(cmd,value)
                    output = json.dumps({cmd: value})
                else:
                    output = json.dumps({'error': 'parameter value missing'})
            else:
                self.page_not_found()
                return
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(bytearray(output, 'UTF-8'))
        except Exception as e:
            print("handle_set_query error {0}".format(e))

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

    def handle_get(self, item):
        try:
            data = {item: model.get_value(item)}
            output = json.dumps(data, sort_keys=False, indent=2)
            self.send_json_response(output)
        except Exception as e:
            print("handle_get_query error {0}".format(e))

    def handle_set(self, item, value):
        try:
            model.set_value(item, value)
            output = json.dumps('{"result":"done"}', sort_keys=False, indent=2)
            self.send_json_response(output)
        except Exception as e:
            print("handle_get_query error {0}".format(e))

    def handle_get_query(self, param):
        try:
            cmd = param['cmd'][0]
            if cmd in model.kv:
                data = {cmd: model.get_value(cmd)}
                output = json.dumps(data, sort_keys=False, indent=2)
            elif cmd == 'info':
                output = json.dumps(model.kv, sort_keys=False, indent=2)
            else:
                self.page_not_found()
                return
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(bytearray(output, 'UTF-8'))
        except Exception as e:
            print("handle_get_query error {0}".format(e))

    def do_PUT(self):
        print("Put", self.path)
        r = self.path.split('/')
        print(r)

    def do_POST(self):
        print("Post", self.path)
        try:
            r = self.path.split('/')
            if len(r) == 3:
                if r[0] == 'button':
                    self.handle_button(r)
                elif r[0] == 'encoder':
                    self.handle_encoder(r)
                elif r[0] == 'reset':
                    self.handle_reset(r)
                else:
                    self.page_not_found()
                return
        except Exception as e:
            print("do_POST error {0}".format(e))

    def do_GET(self):
        try:
            for pair in rewrite_pages:
                key = pair[0]
                replacement = pair[1]
                if re.match(key, self.path):
                    path = re.sub(key, replacement, self.path)
                    try:
                        print(path)
                        output = open(path, 'rb').read()
                        self.send_response(200)
                        guessed_mime_type = mimetypes.guess_type(path, strict=False)
                        print(path, guessed_mime_type)
                        self.send_header("Content-type", guessed_mime_type)
                        self.end_headers()
                        self.wfile.write(output)
                        return
                    except Exception as e:
                        print("Exception {0}".format(e))
                        pass
        except:
            pass
        try:
            if self.path == './html/index.html':
                try:
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(get_template('template.html'), 'UTF-8')
                    return
                except Exception as e:
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    output = "Rephrase your request, this is 404<br/>you asked for [" + str(self.path)+"]"
                    self.wfile.write(bytearray(output, 'UTF-8'))
                    return
            else:
                r = self.path.split('/')
                if r[1] == 'status' or r[1] == 'rooms' or r[1] == 'zones':
                    self.handle_infos(r[1])
                elif r[1] in ['volume', 'indication']:
                    if len(r) == 3:
                        self.handle_set(r[1], r[2])
                    else:
                        self.handle_get(r[1])
                else:
                    self.page_not_found()
                return
            output = open("./html/" + self.path[1:], 'r').read()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b"\n")
            self.wfile.write(bytearray(output, 'UTF-8'))
        except Exception as e:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            output = "Rephrase your request, this is 404<br/>you asked for [" + str(self.path)+"]"
            self.wfile.write(bytearray(output, 'UTF-8'))



def open_info_channel(server):
    '''
    connect to server
    wait for commands on it
    '''
    s = socket()

def scan_raumfeld():
    while 1:
        print("discovery")
        RfCmd.discover()
        print("done")
        sleep(60)

def run_server(port):
    threading.Thread(target=scan_raumfeld).start()
    try:
        print("Starting json server on port {0}".format(port))
        server = HTTPServer(("", port), RequestHandler)
        server.serve_forever()
    except Exception as e:
        print("run_Server error:"+str(e))


def get_local_ip_address():
    s = socket(AF_INET, SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

if __name__ == "__main__":
    run_server(29292)

