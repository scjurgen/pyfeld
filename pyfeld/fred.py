#!/usr/bin/env python3


import threading
from concurrent.futures import thread


from datetime import time
from time import sleep

from pyfeld.upnpCommand import UpnpCommand
from pyfeld.rfcmd import RfCmd

def handle_volume(roomName, value):
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

uc = UpnpCommand(RfCmd.rfConfig['zones'][0]['host'])

def scan_raumfeld():
    while 1:
        print("discovery")
        RfCmd.discover()
        print("done")
        sleep(120)

if __name__ == "__main__":
    RfCmd.discover()
    threading.Thread(target=scan_raumfeld).start()

    for i in range(20):
        handle_volume('one-s-serial', 20-i)
        sleep(1)

