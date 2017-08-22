#!/usr/bin/env python3
from __future__ import unicode_literals

import subprocess
import sys
import threading
from time import sleep

import re

from texttable import Texttable

from pyfeld.pingTest import ping_test_alive


try:
    from pyfeld.rfcmd import RfCmd
except:
    pass

sshcmd = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@"
scpcmd = "scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "


#class RFMacroCommand:

class UpdateProcessesFreeToKill:
    def __init__(self):
        self.processList = list()

    def runCommand(self, cmd):
        try:
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processList.append(process)
        except Exception as e:
            return 0

    def killall(self):
        for proc in self.processList:
            proc.kill()


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


def get_ips():
    RfCmd.discover()
    result = RfCmd.get_device_ips(False, 'list')
    return result

def show_pretty_versions():
    result_list = list()
    header_list = ["IP", "Role", "Version", "Name", "Streamcast version", ]
    result_list.append(header_list)
    print("Versions installed:")
    ips = get_ips()
    for ip in ips:
        line = retrieve(sshcmd + ip + " cat /var/raumfeld-1.0/device-role.json")
        if "true" in line:
            moreinfo = "host"
        else:
            moreinfo = "slave"
        renderer_name = RfCmd.get_device_name_by_ip(ip)
        line = retrieve(sshcmd + ip + " cat /etc/raumfeld-version")
        line_streamcast = retrieve(sshcmd + ip + " streamcastd --version")
        single_result = list()
        single_result.append(ip)
        single_result.append(moreinfo)
        single_result.append(line.rstrip())
        single_result.append(renderer_name)
        single_result.append(line_streamcast.rstrip())
        result_list.append(single_result)
    t = Texttable(250)
    t.add_rows(result_list)
    print(t.draw())

def show_versions():
    print("Versions installed:")
    ips = get_ips()
    for ip in ips:
        line = retrieve(sshcmd+ip+" cat /var/raumfeld-1.0/device-role.json")
        if "true" in line:
            moreinfo = "host"
        else:
            moreinfo = "slave"
        renderer_name = RfCmd.get_device_name_by_ip(ip)
        line = retrieve(sshcmd+ip+" cat /etc/raumfeld-version")
        line_streamcast = retrieve(sshcmd+ip+" streamcastd --version")
        print(ip + "\t" + moreinfo + "\t" + line.rstrip() + "\t" + line_streamcast.rstrip() + "\t" + str(renderer_name))


def clean_host_keys():
    print("cleaning host_keys:")
    ips = get_ips()
    for ip in ips:
        line = retrieve("ssh-keygen -R "+ip)
        print(ip + ":\t" + line.rstrip())


def single_device_update(free_to_kill, ip, url):
    cmd = sshcmd + ip + " raumfeld-update --force " + url
    print("running cmd: "+cmd)
    free_to_kill.runCommand(cmd)


def force_update(url):
    print("Force updating with url " + url)
    ips = get_ips()
    processes = list()
    device_pingable = dict()
    free_to_kill = UpdateProcessesFreeToKill()
    count = 0
    for ip in ips:
        proc = threading.Thread(target=single_device_update, args=(free_to_kill, ip, url))
        proc.start()
        processes.append(proc)
        device_pingable[ip] = True
        count += 1

    temp_count = count
    print("Waiting for action...")
    sleep(5)
    while count > 0:
        sleep(10)
        print("")
        for ip in ips:
            if device_pingable[ip]:
                print("testing if ping alive: " + ip + " " + str(RfCmd.map_ip_to_friendly_name(ip)))
                if not ping_test_alive(ip):
                    device_pingable[ip] = False
                    count -= 1

    count = temp_count
    print("Rebooting in progress...")
    while count > 0:
        sleep(10)
        print("")
        for ip in ips:
            if not device_pingable[ip]:
                print("testing if ping reborn: " + ip + " " + str(RfCmd.map_ip_to_friendly_name(ip)))
                if ping_test_alive(ip):
                    device_pingable[ip] = True
                    count -= 1

    print("done updating shells. Leaving the houses now.")
    free_to_kill.killall()
    for proc in processes:
        proc.join()
    print("Processes joined joyfully")


def single_device_command(ip, cmd):
    cmd = sshcmd + ip + " " + cmd
    print("running cmd on device {0}: {1}".format(ip, cmd))
    lines = retrieve(cmd)
    print("result from {0}".format(ip))
    print(lines)


def ssh_command(cmd):
    print("Send command to all devices: " + cmd)
    ips = get_ips()
    processes = list()
    for ip in ips:
        proc = threading.Thread(target=single_device_command, args=(ip, cmd))
        proc.start()
        processes.append(proc)
    for proc in processes:
        proc.join()


def scp_up_file(local_file, target_location):
    print("Copy file:")
    ips = get_ips()
    for ip in ips:
        line = retrieve(scpcmd+" {1} root@{0}:{2}".format(ip, local_file, target_location))

        print(ip + ":\t" + line.rstrip())


def scp_down_file(remote_file, target_file):
    print("Copy file:")
    ips = get_ips()
    for ip in ips:
        line = retrieve(scpcmd+" root@{0}:{1} {2}".format(ip, remote_file, target_file))
        print(ip + ":\t" + line.rstrip())


def usage(argv):
    print("Usage: {0} COMMAND [params]".format(argv[0]))
    print("Execute macrocommands over ssh for interacting with raumfeld if you got many devices, these need SSH access allowed")
    print("COMMAND may be one of the following")
    print("version                   show versions")
    print("update <URL>              force update")
    print("ssh <command>             any shell available on device, command in quotes")
    print("upload <file> <target>    copy a file to a target location")
    print("download <file> <target>  copy a file from device to target")

    print("")
    print("clean-hostkeys     clean all host keys to avoid security messages")

    '''
    print("#you might add a file ~/.ssh/config with following content")
    print("Host *        (or 192.168.*")
    print("StrictHostKeyChecking no")
    '''


def run_macro(argv):
    if len(argv) < 2:
        usage(argv)
        sys.exit(2)
    command = argv[1]
    if command == 'version':
        show_pretty_versions()
    elif command == 'update':
        force_update(argv[2])
    elif command == 'ssh':
        ssh_command(" ".join(argv[2:]))
    elif command == 'upload':
        scp_up_file(argv[2], argv[3])
    elif command == 'download':
        scp_down_file(argv[2], argv[3])
    elif command == 'clean-hostkeys':
        clean_host_keys()
    else:
        print("Unknown command {0}".format(command))
        usage(argv)


def run_main():
    run_macro(sys.argv)

if __name__ == "__main__":
    run_main()
