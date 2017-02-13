#!/usr/bin/env python3

import socketserver
import signal
import sys
import threading
from _socket import socket, AF_INET, SOCK_DGRAM
from time import sleep
import mimetypes
import re

from http.server import BaseHTTPRequestHandler, HTTPServer

requests = dict()


def get_base_port():
    return 8080


def get_template(filename):
    with open(filename, "rb") as f:
        r = f.read()
    return r.decode("utf-8")


rewrite_pages = [  # const
    ['^/(.*)(html|ico|js|ttf|svg|woff|eot|otf|css|less|map).*$', './\\1\\2'],
    ['^/$', './index.html']
]


class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def page_not_found(self):
        self.send_response(404)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        output = '{"errors":[{"status": 404, "message": "page not found: ' + self.path + '"}]}'
        self.wfile.write(bytearray(output, 'UTF-8'))

    def send_json_response(self, json_string):
        try:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(bytearray(json_string, 'UTF-8'))
        except Exception as e:
            print("handle_get_query error {0}".format(e))

    def do_GET(self):
        print("Get request: {}".format(self.path))
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
                    self.wfile.write(get_template('index.html'), 'UTF-8')
                    return
                except Exception as e:
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    output = "Rephrase your request, this is 404<br/>you asked for [" + str(self.path) + "]"
                    self.wfile.write(bytearray(output, 'UTF-8'))
                    return
            else:
                result = send_infos(self.path)
                if result == "not allowed":
                    output = b'{"result":"not allowed","reason":"no active client connected to the forwarder with your id. Or you are a teapot."}'
                    self.send_response(401)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                else:
                    output = result.encode('utf-8')
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                self.wfile.write(output)
                return

            output = open("./html/" + self.path[1:], 'r').read()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b"\n")
            self.wfile.write(bytearray(output, 'UTF-8'))
        except Exception as e:
            print("Error ", e)
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            output = "Rephrase your request, this is 404<br/>you asked for [" + str(self.path) + "]"
            self.wfile.write(bytearray(output, 'UTF-8'))


def send_infos(path):
    try:
        r = path.split('/', 2)
        id = r[1]
        msg = '#alexa ' + path[len(id)+1:] + '\n'
        print(msg)
        requests[id].sendall(bytearray(msg.encode('Utf-8')))
        response_data = requests[id].recv(1024).decode('utf-8')
        if response_data.startswith("ack "):
            return response_data[4:]
        else:
            return response_data
    except:
        return "not allowed"


def scan_raumfeld():
    global requests
    sleep(10)
    count = 0
    while 1:
        count += 1
        for key, value in requests.items():
            msg = '#keep-alive ' + str(count) + " " + key + '\n'
            print(msg)
            try:
                value.sendall(bytearray(msg.encode('Utf-8')))
            except:
                pass
        ''' not a good solution, doesn't scale,
        server would send bursts of data every 60 seconds
         if there are many connections'''
        sleep(60)


def signal_handler(signal, frame):
    global fetcher_server
    print('received signal', signal)
    print("shutting down connections")
    for key, value in requests.items():
        value.close()
    fetcher_server.shutdown()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
print('Press Ctrl+C')

threading.Thread(target=scan_raumfeld).start()


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        print("got a connection from ", self.client_address)
        self.request.settimeout(120)
        id = None
        end_connection = False
        error_count = 0
        empty_count = 0
        self.request.sendall(b'login:\r\n')
        while True:
            raw_data = self.request.recv(1024)
            if len(raw_data) == 0:
                empty_count += 1
                if empty_count > 4:
                    print("receiving rubbish, terminating connection")
                    end_connection = True
                sleep(1)
            else:
                empty_count = 0
            data = str(raw_data, 'utf-8').strip()

            print("I received '{}'".format(data))
            cur_thread = threading.current_thread()
            response = "{}: {}".format(cur_thread.name, data)
            if data.startswith('#id '):
                if id is not None:
                    self.request.sendall(b'You already gave an ID!\r\n')
                else:
                    id = data.split(' ')[1]
                    self.request.sendall(b'password:\r\n')
            if data.startswith('#pwd '):
                if id is not None:
                    print("client identified with id {}. Adding to pool.".format(id))
                    requests[id] = self.request
                    self.request.sendall(b'ok\r\n')

                else:
                    print("sends password (which is wrong).".format(id))
                    end_connection = True
            if id == '':
                error_count += 1
                if error_count == 3:
                    end_connection = True
                self.request.sendall(b'asked you to login:\r\n')
            if data.startswith('#quit'):
                self.request.sendall(b'see you! :)\r\n')
                self.request.close()
                try:
                    del requests[id]
                except KeyError:
                    pass
                print("Client exit!")
                return
            if data.startswith('#ack '):
                print("response is {}".format(data[5:]))

            if end_connection:
                self.request.sendall(b'bye bye :(\r\n')
                self.request.close()
                return


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


def get_local_ip_address():
    s = socket(AF_INET, SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    host, server_port = get_local_ip_address(), get_base_port()
    print("Starting fetcher server as {0}:{1}".format(host, server_port))

    fetcher_server = ThreadedTCPServer((host, server_port), ThreadedTCPRequestHandler)
    http_server = HTTPServer((host, server_port + 2), RequestHandler)
    print("Starting http server as {0}:{1}".format(host, server_port + 2))

    fetcher_server_thread = threading.Thread(target=fetcher_server.serve_forever)
    fetcher_server_thread.daemon = True
    fetcher_server_thread.start()

    server_thread = threading.Thread(target=http_server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    fetcher_server_thread.join()
    server_thread.join()

    fetcher_server.shutdown()
    fetcher_server.server_close()
    http_server.shutdown()
    http_server.server_close()
    print("stopped all")
