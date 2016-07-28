
Synopsis
========

Small tools to Raumfeld functionalities using python.
With these simple tools you can control the following things in Raumfeld:

- playsettings: volume, position, pause, stop
- rooms: list rooms 
- zones: list, create, drop
- media: browse and search, play in zone
- macro operations: fade, wait for conditions (volume, position, title)


Installation
============
the easist way is to use pip

On Fedora
---------
sudo dnf install python-pip
pip install pyfeld

On Mac
------
brew install python
sudo easy_install pip



Usage
=====
you need nmap and/or gssdp_discover

on mac:
	brew install nmap

on linux:
	you know the drill ;-)


Known Unknowns
==============

A freshly installed version on a vergin machine will not check if nmap is installed and silently fails without telling yo why



