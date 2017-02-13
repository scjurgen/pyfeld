#!/usr/bin/env python3

import getpass
import sys
import telnetlib

HOST = "192.168.2.115"
#user = raw_input("Enter your remote account: ")
#password = getpass.getpass()

tn = telnetlib.Telnet(HOST, 8080)

tn.read_until(b"Id please:")
#tn.write(user + "\n")
#if password:
#    tn.read_until("Password: ")
#    tn.write(password + "\n")

tn.write(b"#id scjurgen\n")
tn.write(b"#pwd: bogus\n")
while True:
    print("waiting for data")
    print(tn.read_until(b"\n"))
    tn.write(b"{ \"result\":\"ACK\"}\n")


