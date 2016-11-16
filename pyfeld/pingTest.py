#!/usr/bin/env python3
import subprocess
import sys

def ping_test_alive(ip):
    cmd = "ping -W 1 -c 1 " + ip
    try:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        return 0
    output_received = ""
    while True:
        line = process.stdout.readline()
        if len(line) == 0 and process.poll() != None:
            break
        v = line.decode('utf-8')
        output_received += v
    return "1 received" in output_received

if __name__ == "__main__":
    print(ping_test_alive(sys.argv[1]))

