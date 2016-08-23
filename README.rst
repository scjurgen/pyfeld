
Synopsis
========

Small tools to Raumfeld functionalities using python.
With these simple tools you can control the following things in Raumfeld:

- playsettings: volume, position, pause, stop, equalizer
- rooms: list rooms 
- zones: list, create, drop
- media: browse and search, play in zone
- macro operations: fade, wait for conditions (volume, position, title)


Installation
============
the easiest way is to use pip

``pip install pyfeld``

Usage
=====
you need nmap (for now, there is another simple discovery algorithm in progress)

on mac:
	``brew install nmap``

on linux:
	you know the drill ;-)

Running pyfeld
--------------

These example will suppose a device called ``kitchen``

Get some help:

    ``pyfeld --help``

Discover devices and print info of zones and rooms:

    ``pyfeld --discover info``

Same as bevor but print:

    ``pyfeld --discover --json info``

Browse some stuff:

    ``pyfeld browse "0/My Music/Albums"``

Play one of the browsed albums:

    ``pyfeld play --zonewithroom kitchen "0/My Music/Albums/Frank%20Zappa+"``


Check the volume in the kitchen, then set to 30%:

    ``pyfeld --discover --zonewithroom kitchen volume``
    ``pyfeld --zonewithroom kitchen setvolume 30``

Raise bass and treble, lower mids

    ``pyfeld  roomseteq kitchen 500 -100 700``

Create new zone (pay attention to spaces, quote!):

    ``pyfeld createzone kitchen "bath room" "living room"``

Drop a device from the zone it is in:
    ``pyfeld drop "bath room"``

Pyfeld advanced
---------------

You can do work on specific UDN

Retrive UDN's:
    ``pyfeld --discover -v info``


``pyfeld --udn createzone uuid:f7052a34-37f6-432f-b584-837466474205``
``pyfeld --udn roomsetvolume uuid:f7052a34-37f6-432f-b584-837466474205 10``

