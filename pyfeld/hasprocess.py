#!/usr/bin/env python3

from __future__ import unicode_literals

import subprocess
import sys
import threading
import re

def retrieve(cmd):
    try:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        return 0
    lines = ""
    while True:
        nextline = process.stdout.readline()
        if len(nextline) == 0 and process.poll() != None:
            break
        lines += nextline.decode('utf-8')
    return lines

sshcmd = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@"

def single_device_command(ip, cmd):
    cmd = sshcmd + ip + " " + cmd
    lines = retrieve(cmd)
    return lines.split("\n")

def get_ps_list(ip):
    processes_found = single_device_command(ip, "ps -T")
    return processes_found

def usage(argv):
    print("Usage: {0} [OPTIONS] ip".format(argv[0]))
    print("get process list of device on given ip (needs ssh access to device via root)")
    print("OPTIONS:")
    print("  -m, --missing     show only missing processes")
    print("  -e, --existent    show only existent processes")
    print("  -a, --all         show the complete ps list")


def list_of_expected_command():
    return [
            ["/usr/bin/rfpd", "rfpd (soundbar/deck)", False],
            ["logger -t", "config-service gdbus", False],
            ["/system/chrome/cast_shell", "cast_shell", True],
            ["bluetoothd", "bluetoothd", False],
            ["rf-bluetoothd", "rf-bluetoothd", False],
            ["avahi-daemon", "avahi-daemon", False],
            ["dbus-daemon", "dbus-daemon", False],
            ["/usr/sbin/connmand", "connmand", False],
            ["/usr/sbin/wpa_supplicant", "wpa_supplicant", False],
            ["{gdbus} config-service", "config-service gdbus", False],
            ["{gdbus} master-process", "master-process gdbus",  False],
            ["{gdbus} meta-server", "meta-server gdbus",  False],
            ["{gdbus} renderer", "renderer gdbus",  False],
            ["{gdbus} run-streamcastd", "run-streamcastd gdbus",  False],
            ["{gdbus} stream-decoder", "stream-decoder gdbus",  False],
            ["{gdbus} stream-relay", "stream-relay gdbus",  False],
            ["{gdbus} web-service", "web-service gdbus",  False],
            ["{gmain} config-service", "config-service gmain",  True],
            ["{gmain} master-process", "master-process gmain",  True],
            ["{gmain} meta-server", "meta-server gmain",  True],
            ["{gmain} raumfeld-report-daemon", "raumfeld-report-daemon gmain",  True],
            ["{gmain} renderer", "renderer gmain",  True],
            ["{gmain} run-streamcastd", "run-streamcastd gmain",  True],
            ["{gmain} stream-decoder", "stream-decoder gmain",  True],
            ["{gmain} stream-relay", "stream-relay gmain",  True],
            ["{gmain} web-service", "web-service gmain",  True],
            ["{IdleCallbackHel} renderer", "renderer IdleCallbackHelper",  True],
            ["{pool} meta-server", "meta-server pool",  False],
            ["{pool} run-streamcastd", "run-streamcastd pool",  False],
            ["{pool} web-service", "web-service pool",  False],
            ["[cifsiod]", "cifsiod",  False],
            ["[cifsd]", "cifsd",  False],
            ["/usr/bin/dbus-daemon", "dbus-daemon",  True],
            ["{start-master-pr}", "start-master-process.sh",  True],
            ["/usr/sbin/wpa_supplicant", "wpa_supplicant",  False],
            ]

class ProcessItem:
    def __init__(self, name, exists):
        self.name = name
        self.exists = exists


def run_main(argv):
    if len(argv) < 2:
        usage(argv)
        sys.exit(2)
    cmds = list_of_expected_command()

    show_what = 'simple'

    arg_pos = 1
    while argv[arg_pos].startswith('-'):
        if argv[arg_pos].startswith('--'):
            option = argv[arg_pos][2:]
        else:
            option = argv[arg_pos]
        arg_pos += 1
        if option in ['m', 'missing']:
            show_what = 'missing'
        elif option in ['e', 'existent']:
            show_what = 'existent'
        elif option in ['a', 'all']:
            show_what = 'all'

    ps_list = get_ps_list(argv[arg_pos])
    pos = ps_list[0].find("COMMAND")  # get formatting of list
    ps_list = ps_list[1:]
    clean_list = list()
    for cmd in cmds:
        p_process = ProcessItem(cmd[1], False)
        for item in ps_list:
            item = " "+item[pos:]  # leave a space padded in front
            item = item.replace(" ./", " ")
            item = item.strip()
            if cmd[0] in item:
                p_process.exists = True
        clean_list.append(p_process)
    clean_list.sort(key=lambda x: x.name, reverse=False)
    for ci in clean_list:
        if ci.exists:
            if show_what in ['existent', 'all', 'simple']:
                tickmark = "[x]"
                print(tickmark, ci.name)
        else:
            if show_what in ['missing', 'all', 'simple']:
                tickmark = "[ ]"
                print(tickmark, ci.name)

if __name__ == "__main__":
    run_main(sys.argv)
