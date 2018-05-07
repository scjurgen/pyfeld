#!/usr/bin/env python3

import re
import socket
import threading
import urllib3

from getRaumfeld import RaumfeldDeviceSettings

from urllib.parse import urlparse



class DiscoverHost:
    def __init__(self):
        self.found_ip = None
        self.processes = list()

    def discoverByIpList(self, ipList):
        self.found_ip = None
        local_ip = RaumfeldDeviceSettings.get_local_ip_address()
        decomposed = local_ip.split(".")
        self.processes = list()
        for ip in ipList:
            p = "http://"+ip + ":47365/WelcomePage"
            proc = threading.Thread(target=self.get, args=(p, ip, 2.0, 5.0))
            proc.start()
            self.processes.append(proc)

        for proc in self.processes:
            proc.join()
        return self.found_ip

    def discoverByHttp(self):
        self.found_ip = None
        local_ip = RaumfeldDeviceSettings.get_local_ip_address()
        decomposed = local_ip.split(".")
        self.processes = list()
        ip_list = list()
        for seg in range(0, 3):
            for i in range(0+seg*64, (seg+1)*64):
                ip_list.append(decomposed[0] + "." + decomposed[1] + "." + decomposed[2] + "." + str(i))
            if self.discoverByIpList(ip_list) is not None:
                return self.found_ip
        return None

    def kill_after_found(self):
        for proc in self.processes:
            proc.kill()

    def get(self, url, ip, timeoutConnect, timeoutRead):
        headers = {
            'CONTENT-TYPE': 'text/xml; charset="utf-8"',
            'USER-AGENT': 'uPNP/1.0'
        }
        try:
            timeout = urllib3.util.timeout.Timeout(connect=timeoutConnect, read=timeoutRead)
            http = urllib3.PoolManager(timeout=5.0)
            r = http.request("GET", url, headers=headers)
            if r.status == 200:
                self.found_ip = ip
                self.kill_after_found()
        except Exception as e:
            pass
            #print("Request for '%s' failed: %s" % (url, e))

    def found_IP(self):
        return self.found_ip

    def discoverBySsdp(self, timeout=1, retries=1):
        locations = []

        group = ('239.255.255.250', 1900)
        service = 'ssdp:urn:schemas-upnp-org:device:MediaServer:1'  # 'ssdp:all'
        message = '\r\n'.join(['M-SEARCH * HTTP/1.1', 'HOST: {group[0]}:{group[1]}', 'MAN: "ssdp:discover"', 'ST: {st}', 'MX: 1', '', '']).format(group=group, st=service)

        socket.setdefaulttimeout(timeout)
        for _ in range(retries):
            sock = socket.socket(socket.AF_INET,
                                 socket.SOCK_DGRAM,
                                 socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.sendto(message.encode('utf-8'), group)
            while True:
                try:
                    response = sock.recv(2048).decode('utf-8')
                    for line in response.split('\r\n'):
                        if line.startswith('Location: '):
                            location = line.split(' ')[1].strip()
                            m = re.search('http://([0-9.]*):', location)
                            if m:
                                ip = m.group(1)
                                if not ip in locations:
                                    locations.append(ip)
                except socket.timeout:
                    break
        return self.discoverByIpList(locations)



if __name__ == '__main__':
    print(DiscoverHost().discoverByHttp())
    print(DiscoverHost().discoverBySsdp())
