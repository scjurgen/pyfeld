#!/usr/bin/env bash


if [ $# -ne 1 ]; 
    then echo "please specify a room, available rooms are:"
    pyfeld --discover rooms
    exit -1
fi

cmdColor="\\033[0;32m"
white="\\033[1;37m"
mainroom=$1

waitkey()  {
    echo -e "${cmdColor}$1:${white} (key)"
    read
    clear 
}

waitkey "discover and show info about your current Raumfeld system"
pyfeld --discover info
waitkey "create an extensive json of the system for parsing"
pyfeld --discover --json info

waitkey "simple list of rooms" 
pyfeld rooms
waitkey "json of rooms" 
pyfeld --json rooms
waitkey "simple list of zones" 
pyfeld zones
waitkey "same in json" 
pyfeld --json zones

waitkey "browse mediaserver" 
pyfeld browse "0"
waitkey "browse tunein" 
pyfeld browse "0/RadioTime/LocalRadio"
waitkey "browse tunein localradio" 
pyfeld --json browse "0/RadioTime/LocalRadio"

waitkey "search an album"
pyfeld search "0/My Music/Search/Albums" 'dc:title contains you'


pyfeld --discover
waitkey "drop our room ${mainroom}"
pyfeld drop ${mainroom}
pyfeld --discover rooms
pyfeld --discover unassignedrooms

waitkey "create a zone with ${mainroom}"
pyfeld createzone ${mainroom}
waitkey "do we have the zone?"
pyfeld --discover info

waitkey "play a station on ${mainroom}" 
pyfeld --zonewithroom ${mainroom} play "0/RadioTime/LocalRadio/s-s132954"
waitkey "get current position..."
pyfeld --zonewithroom ${mainroom} position
waitkey "and again (it moved?)"
pyfeld --zonewithroom ${mainroom} position

waitkey "play local content ${mainroom}"
pyfeld --zonewithroom ${mainroom} play ""
waitkey "get current position..."
pyfeld --zonewithroom ${mainroom} position
waitkey "and again (it moved?)"
pyfeld --zonewithroom ${mainroom} position

