#!/usr/bin/env python
from __future__ import unicode_literals

import re
import subprocess
import sys
from time import sleep

from pyfeld.dirBrowse import DirBrowse


def retrieve(cmd):
    command = 'pyfeld '+cmd
    print(command)
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except Exception as e:
        return 0
    lines = ""
    while True:
        nextline = process.stdout.readline()
        if len(nextline) == 0 and process.poll() != None:
            break
        lines += nextline.decode('utf-8')
    return lines


def show_dir(dir_browser):
    for i in range(0, dir_browser.max_entries_on_level() - 1):
        print(dir_browser.get_friendly_name(i))


def info():
    print("This is a simple info")
    print(retrieve("--discover info"))

    print("This is an extended info")
    print(retrieve("--discover -v -v info"))
    dir_browser = DirBrowse()
    print("Feching containers and items")
    for i in [1, 1, 0]:
        dir_browser.enter(i)
        print("Friendly path: " + dir_browser.get_friendly_path_name(" -> "))
        print("Friendly name of item: " + dir_browser.get_friendly_name(0))
        print("Path: " + dir_browser.get_path_for_index(0))
        print("Info on item:"+retrieve('--json browseinfo "'+dir_browser.get_path_for_index(0) + '"'))

def rooms():
    print("This is a list of the rooms")
    rooms = retrieve("--discover rooms")
    room_list = rooms.splitlines(False)
    print(room_list)

    print("Going to remove all rooms from zones, say bye bye")
    for room in room_list:
        retrieve("drop " + room)
    retrieve("--discover")

    print("This is a simple info")
    print(retrieve("--discover info"))

    zonecmd = "createzone "
    for room in room_list:
        zonecmd += "'" + room + "' "
    retrieve(zonecmd)

    print("This is an updated list of the zone (should be one big only)")
    print(retrieve("--discover zones"))


def browse():
    print("Going to browse the root folder")

    dir_browser = DirBrowse()
    show_dir(dir_browser)

    print("Going to enter the second folder")
    dir_browser.enter(1)
    show_dir(dir_browser)

    print("Going to enter the next folder")
    dir_browser.enter(1)
    print(dir_browser.path)
    show_dir(dir_browser)

    print("Going to enter the next folder")
    dir_browser.enter(1)
    print(dir_browser.path)
    show_dir(dir_browser)

    retrieve("--discover rooms")

    dir_browser.leave()
    print(dir_browser.path)
    show_dir(dir_browser)

    retrieve("--discover zones")

    dir_browser.leave()
    print(dir_browser.path)
    show_dir(dir_browser)


def play():
    print("fetching rooms")
    rooms = retrieve("--discover rooms")
    room_list = rooms.splitlines(False)

    dir_browser = DirBrowse()
    dir_browser.enter(1)
    dir_browser.enter(1)
    path = dir_browser.get_path_for_index(2)
    retrieve("--zonewithroom " + room_list[0] + ' play "' + path +'"')
    print("waiting a moment, then we will look at some track info")
    sleep(10)
    print(retrieve("--zonewithroom " + room_list[0] + ' zoneinfo'))
    print("seeking to 02:00 and again we will look at some track info")
    print(retrieve("--zonewithroom " + room_list[0] + ' seek 00:01:34'))
    sleep(2)
    print(retrieve("--zonewithroom " + room_list[0] + ' zoneinfo'))
    print("Let's play with volume")
    print(retrieve("--zonewithroom " + room_list[0] + ' setvolume 30'))
    print(retrieve("--zonewithroom " + room_list[0] + ' getvolume'))
    sleep(2)
    print(retrieve("--zonewithroom " + room_list[0] + ' setvolume 40'))
    print(retrieve("--zonewithroom " + room_list[0] + ' getvolume'))
    sleep(2)
    print(retrieve("--zonewithroom " + room_list[0] + ' setvolume 20'))
    print(retrieve("--zonewithroom " + room_list[0] + ' getvolume'))


def usage(argv):
    print("Usage: {0} [test]", argv[0])
    print("  browse")
    print("  play")
    print("  rooms")
    print("  info")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        usage(sys.argv)
    else:
        if sys.argv[1] == 'browse':
            browse()
        elif sys.argv[1] == 'play':
            play()
        elif sys.argv[1] == 'rooms':
            rooms()
        elif sys.argv[1] == 'info':
            info()
        elif sys.argv[1] == 'all':
            browse()
            play()
            rooms()
            info()
        else:
            print("command {0} not found!".format(sys.argv[1]))
            usage(sys.argv)

