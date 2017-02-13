#!/usr/bin/env python3

import mimetypes
import re
import socketserver
import signal
import sys
import threading

from datetime import time, datetime
from _socket import socket, AF_INET, SOCK_DGRAM
from time import sleep


from http.server import BaseHTTPRequestHandler, HTTPServer



class RequestsStore:
    def __init__(self, id, request):
        self.id = id
        self.request = request
        self.expecting_data = False
        self.running_id = 0
        self.next_keep_alive = 10

clients = dict()



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
    global clients
    try:
        r = path.split('/', 2)
        user_id = r[1]
        clients[user_id].next_keep_alive = 10
        clients[user_id].expecting_data = True
        clients[user_id].running_id += 1
        msg = "#alexa {} {}\n".format(clients[user_id].running_id, path[len(user_id)+1:])
        print("sending msg: " + msg)
        clients[user_id].request.sendall(bytearray(msg.encode('Utf-8')))
        print("waiting for response")
        response_data = clients[user_id].request.recv(1500).decode('utf-8')
        print("got response from pfserver: '{}'".format(response_data))
        if response_data.startswith("#ack {} ".format(clients[user_id].running_id)):
            clients[user_id].expecting_data = False
            return response_data.split(" ", 2)[2]
        else:
            clients[user_id].expecting_data = False
            return response_data

    except Exception as e:
        print("send_infos error occured: {}".format(e))
        clients[user_id].expecting_data = False
        return "not allowed"


def scan_raumfeld():
    global clients
    while 1:
        for key, value in clients.items():
            if value.next_keep_alive == 0:
                value.next_keep_alive = 10
                msg = '#keep-alive ' + key + datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f") + '\n'
                print(msg)
                try:
                    value.request.sendall(bytearray(msg.encode('Utf-8')))
                except:
                    pass
            value.next_keep_alive -= 1

        sleep(1)


def signal_handler(signal, frame):
    global fetcher_server
    print('received signal', signal)
    print("shutting down connections")
    for key, value in clients.items():
        value.request.close()
    fetcher_server.shutdown()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
print('Press Ctrl+C')

threading.Thread(target=scan_raumfeld).start()


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        print("got a connection from ", self.client_address)
        self.request.settimeout(5)
        user_id = None
        end_connection = False
        error_count = 0
        empty_count = 0
        self.request.sendall(b'login:\r\n')
        while True:
            try:
                raw_data = self.request.recv(1500)
            except:
                raw_data = b""
            if len(raw_data) == 0:
                empty_count += 1
                if empty_count > 120/5:
                    print("receiving rubbish, terminating connection")
                    self.request.sendall(b'bye bye :(\r\n')
                    self.request.close()
                    return
            else:
                empty_count = 0
                data = str(raw_data, 'utf-8').strip()

                print("I received '{}'".format(data))
                if data.startswith('#id '):
                    if user_id is not None:
                        self.request.sendall(b'You already gave an ID!\r\n')
                    else:
                        user_id = data.split(' ')[1]
                        self.request.sendall(b'password:\r\n')
                if data.startswith('#pwd '):
                    if user_id is not None:
                        print("client identified with id {}. Adding to pool.".format(user_id))
                        clients[user_id] = RequestsStore(user_id, self.request)
                        self.request.sendall(b'ok\r\n')

                    else:
                        print("sends password (which is wrong).".format(user_id))
                        end_connection = True

                if user_id is None:
                    error_count += 1
                    if error_count == 3:
                        end_connection = True
                    self.request.sendall(b'asked you to login:\r\n')

                if data.startswith('#quit'):
                    self.request.sendall(b'see you! :)\r\n')
                    self.request.close()
                    try:
                        del clients[user_id]
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
