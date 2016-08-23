#!/usr/bin/env python3
from __future__ import unicode_literals

import subprocess
import sys
import threading

try:
    from pyfeld.rfcmd import RfCmd
except:
    pass

sshcmd = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@"
scpcmd = "scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "


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
    result = RfCmd.get_device_ips('list')
    return result


def show_versions():
    print("Versions installed:")
    ips = get_ips()
    for ip in ips:
        line = retrieve(sshcmd+ip+" cat /etc/raumfeld-version")
        print(ip + ":\t" + line.rstrip())


def clean_host_keys():
    print("cleaning host_keys:")
    ips = get_ips()
    for ip in ips:
        line = retrieve("ssh-keygen -R "+ip)
        print(ip + ":\t" + line.rstrip())


def single_device_update(ip, url):
    cmd = sshcmd + ip + " raumfeld-update --force " + url
    print("running cmd: "+cmd)
    retrieve(cmd)


def force_update(url):
    print("Force updating with url " + url)
    ips = get_ips()
    processes = list()
    for ip in ips:
        proc = threading.Thread(target=single_device_update, args=(ip, url))
        proc.start()
        processes.append(proc)
    for proc in processes:
        proc.join()


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


def scp_file(local_file, target_location):
    print("Copy file:")
    ips = get_ips()
    for ip in ips:
        line = retrieve(scpcmd+" {1} root@{0}:{2}".format(ip, local_file,target_location))
        print(ip + ":\t" + line.rstrip())

def usage(argv):
    print("Usage: {0} COMMAND [params]".format(argv[0]))
    print("will execute macrocommands for interacting with raumfeld if you got many devices, these need SSH access allowed")
    print("COMMAND may be one of the following")
    print("version            show versions")
    print("update URL         force update")
    print("ssh command        any shell available on device, command in quotes")
    print("scp file target    copy a file to a target location")

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
        show_versions()
    if command == 'update':
        force_update(argv[2])
    if command == 'ssh':
        ssh_command(argv[2])
    if command == 'scp':
        scp_file(argv[2], argv[3])
    if command == 'clean-hostkeys':
        clean_host_keys()

def run_main():
    run_macro(sys.argv)

if __name__ == "__main__":
    run_main()
