#!/usr/bin/env python
from __future__ import unicode_literals

import json
import requests
import sys
import cgi 

from xml.dom import minidom

from pyfeld.xmlHelper import XmlHelper
from pyfeld.didlInfo import DidlInfo


class UpnpCommand:

    def __init__(self, host):
        self.host = host
        self.verbose = False

    def host_send(self, action, control_path, control_name, action_args):

        if self.host.startswith("http://"):
            control_url = self.host + control_path
            host_name = self.host[7:]
        else:
            control_url = "http://" + self.host + control_path
            host_name = self.host

        body = '<?xml version="1.0"?>'
        body += '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" '
        body += 'SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        body += '<SOAP-ENV:Body>'
        body += '	<m:'+action+' xmlns:m="urn:schemas-upnp-org:service:'+control_name+':1">'
        body += action_args
        body += '	</m:'+action+'>'
        body += '</SOAP-ENV:Body>'
        body += '</SOAP-ENV:Envelope>'
        if self.verbose:
            print(body)
        headers = {'Host': host_name,
                   'User-Agent': 'xrf/1.0',
                   'Content-Type': 'text/xml; charset="utf-8"',
                   'Content-Length': str(len(body)),
                   'SOAPAction': '"urn:schemas-upnp-org:service:'+control_name+':1#'+action+'"'}
        try:
            response = requests.post(control_url, data=body, headers=headers, verify=False)
            if response.status_code < 300:
                if self.verbose:
                    print(response.content)
                result = minidom.parseString(response.content)
                if self.verbose:
                    print(result.toprettyxml())
                return result
            else:
                print("query {0} returned status_code:{1}".format(control_url,response.status_code))
        except Exception as e:
            print("host send error {0}".format(e))
        return None

    def device_send_rendering(self, action, action_args):
        return self.host_send(action,
                              "/RenderingControl/ctrl",
                              "RenderingControl",
                              action_args)

    def host_send_rendering(self, action, action_args):
        return self.host_send(action,
                              "/RenderingService/Control",
                              "RenderingControl",
                              action_args)

    def host_send_transport(self, action, action_args):
        return self.host_send(action,
                              "/TransportService/Control",
                              "AVTransport",
                              action_args)

    def host_send_contentdirectory(self, action, action_args):
        return self.host_send(action,
                          "/cd/Control",
                          "ContentDirectory",
                          action_args)

    def play(self):
        xml_root = self.host_send_transport("Play",  '<InstanceID>0</InstanceID><Speed>1</Speed>')
        return xml_root.toprettyxml()

    def stop(self):
        xml_root = self.host_send_transport("Stop",  '<InstanceID>0</InstanceID>')
        return xml_root.toprettyxml()

    def pause(self):
        xml_root = self.host_send_transport("Pause",  '<InstanceID>0</InstanceID>')
        return xml_root.toprettyxml()

    def seek(self, value):
        xml_root = self.host_send_transport("Seek",
                                           '<InstanceID>0</InstanceID><Unit>ABS_TIME</Unit>'
                                           '<Target>' + value + '</Target>')
        return xml_root.toprettyxml()

    def previous(self):
        xml_root = self.host_send_transport("Previous", '<InstanceID>0</InstanceID>')
        return xml_root.toprettyxml()

    def next(self):
        xml_root = self.host_send_transport("Next", '<InstanceID>0</InstanceID>')
        return xml_root.toprettyxml()

    def get_state_var(self):
        xml_root = self.host_send_rendering("GetStateVariables",
                                           '<InstanceID>0</InstanceID><'
                                           'StateVariableList>TransportStatus</StateVariableList>')
        return xml_root.toprettyxml()

    def get_position_info(self):
        xml_root = self.host_send_transport("GetPositionInfo",  '<InstanceID>0</InstanceID>')
        return XmlHelper.xml_extract_dict(xml_root, ['Track',
                                                    'TrackDuration',
                                                    'TrackMetaData',
                                                    'TrackURI',
                                                    'RelTime',
                                                    'AbsTime',
                                                    'RelCount',
                                                    'AbsCount'])

    def get_transport_setting(self):
        xml_root = self.host_send_transport("GetTransportSettings",  '<InstanceID>0</InstanceID>')
        return XmlHelper.xml_extract_dict(xml_root, ['PlayMode'])

    def get_media_info(self):
        xml_root = self.host_send_transport("GetMediaInfo",  '<InstanceID>0</InstanceID>')
        return XmlHelper.xml_extract_dict(xml_root, ['PlayMedium', 'NrTracks', 'CurrentURI', 'CurrentURIMetaData'])

    def set_transport_uri(self, data):
        print("CurrentURI:\n" + data['CurrentURI'])
        print("CurrentURIMetaData:\n" + data['CurrentURIMetaData'])
        send_data = '<InstanceID>0</InstanceID>'
        add_uri = data['CurrentURI']
        if 'raumfeldname' in data:
            if data['raumfeldname'] == 'Station':
                if 'TrackURI' in data:
                    add_uri = data['TrackURI']

        send_data += "<CurrentURI><![CDATA[" + add_uri + "]]></CurrentURI>"
        send_data += "<CurrentURIMetaData>" + cgi.escape(data['CurrentURIMetaData']) + "</CurrentURIMetaData>"
        # + cgi.escape(data['CurrentURIMetaData']) +
        print(send_data)
        xml_root = self.host_send_transport("SetAVTransportURI", send_data)
        return XmlHelper.xml_extract_dict(xml_root, ['SetAVTransportURI'])

    '''Rendering service'''

    def get_volume(self, format='plain'):
        xml_root = self.host_send_rendering("GetVolume", '<InstanceID>0</InstanceID><Channel>Master</Channel>')
        dict = XmlHelper.xml_extract_dict(xml_root, ['CurrentVolume'])
        if format == 'json':
            return '{ "CurrentVolume": "'+dict['CurrentVolume'] + '"}'
        else:
            return dict['CurrentVolume']

    def set_volume(self, value):
        xml_root = self.host_send_rendering("SetVolume",
                                           '<InstanceID>0</InstanceID><Channel>Master</Channel>' +
                                           '<DesiredVolume>' + str(value) + '</DesiredVolume>')
        return xml_root.toprettyxml()

    def get_volume_by_udn(self, format='plain'):
        xml_root = self.device_send_rendering("GetVolume", '<InstanceID>0</InstanceID><Channel>Master</Channel>')
        dict = XmlHelper.xml_extract_dict(xml_root, ['CurrentVolume'])
        if format == 'json':
            return '{ "CurrentVolume": "'+dict['CurrentVolume'] + '"}'
        else:
            return dict['CurrentVolume']

    def set_volume_by_udn(self, value):
        xml_root = self.device_send_rendering("SetVolume",
                                           '<InstanceID>0</InstanceID><Channel>Master</Channel>' +
                                           '<DesiredVolume>' + str(value) + '</DesiredVolume>')
        return xml_root.toprettyxml()

    def get_room_volume(self, uuid, format='plain'):
        xml_root = self.host_send_rendering("GetRoomVolume", '<InstanceID>0</InstanceID>'
                                           '<Room>' + uuid + '</Room>')
        dict = XmlHelper.xml_extract_dict(xml_root, ['CurrentVolume'])
        if format == 'json':
            return '{ "CurrentVolume": "'+dict['CurrentVolume'] + '"}'
        else:
            return dict['CurrentVolume']

    def set_room_volume(self, uuid, value):
        xml_root = self.host_send_rendering("SetRoomVolume",
                                           '<InstanceID>0</InstanceID><Channel>Master</Channel>' +
                                           '<DesiredVolume>' + str(value) + '</DesiredVolume>' +
                                           '<Room>' + uuid + '</Room>')
        return None

    def get_mute(self, format='plain'):
        xml_root = self.host_send_rendering("GetMute", '<InstanceID>0</InstanceID><Channel>Master</Channel>')
        dict = XmlHelper.xml_extract_dict(xml_root, ['CurrentMute'])
        if format == 'json':
            return '{ "CurrentMute": "'+dict['CurrentMute'] + '"}'
        else:
            return dict['CurrentMute']

    def set_mute(self, value):
        xml_root = self.host_send_rendering("SetMute",
                                           '<InstanceID>0</InstanceID><Channel>Master</Channel>' +
                                           '<DesiredMute>' + str(value) + '</DesiredMute>')
        return xml_root.toprettyxml()

    def get_room_mute(self, uuid, format='plain'):
        xml_root = self.host_send_rendering("GetRoomMute", '<InstanceID>0</InstanceID>'
                                           '<Room>' + uuid + '</Room>')
        dict = XmlHelper.xml_extract_dict(xml_root, ['CurrentMute'])
        if format == 'json':
            return '{ "CurrentMute": "'+dict['CurrentMute'] + '"}'
        else:
            return dict['CurrentMute']

    def set_room_mute(self, uuid, value):
        xml_root = self.host_send_rendering("SetRoomMute",
                                           '<InstanceID>0</InstanceID><Channel>Master</Channel>' +
                                           '<DesiredMute>' + str(value) + '</DesiredMute>' +
                                           '<Room>' + uuid + '</Room>')
        return None

    """
    device stuff
    """
    def get_filter(self, output_format='plain'):
        xml_root = self.device_send_rendering("GetFilter", '<InstanceID>0</InstanceID>'
                                           )
        dict_result = XmlHelper.xml_extract_dict(xml_root, ['LowDB', 'MidDB', 'HighDB'])
        if output_format == 'json':
            return '{ "LowDB": "'+dict_result['LowDB'] + '",  "MidDB": "'+dict_result['MidDB'] + '",  "HighDB": "'+dict_result['HighDB'] + '"}'
        else:
            return dict_result['LowDB'] + " " + dict_result['MidDB'] + " " + dict_result['HighDB']

    def set_filter(self, valueLow, valueMid, valueHigh):
        xml_root = self.device_send_rendering("SetFilter",
                                           '<InstanceID>0</InstanceID><Channel>Master</Channel>' +
                                           '<LowDB>' + str(valueLow) + '</LowDB>' +
                                           '<MidDB>' + str(valueMid) + '</MidDB>' +
                                           '<HighDB>' + str(valueHigh) + '</HighDB>'
                                           )
        return None

    def get_balance(self, output_format='plain'):
        xml_root = self.device_send_rendering("GetBalance", '<InstanceID>0</InstanceID>')
        dict_result = XmlHelper.xml_extract_dict(xml_root, ['CurrentBalance'])
        if output_format == 'json':
            return '{ "CurrentBalance": "'+dict_result['CurrentBalance'] + '"}'
        else:
            return dict_result['CurrentBalance']

    def set_balance(self, value):
        xml_root = self.device_send_rendering("SetBalance",
                                           '<InstanceID>0</InstanceID><Channel>Master</Channel>' +
                                           '<DesiredBalance>' + str(value) + '</DesiredBalance>'
                                           )
        return None

    def get_browse_capabilites(self):
        xml_root = self.host_send_contentdirectory("GetSearchCapabilities", '')
        return XmlHelper.xml_extract_dict(xml_root, ['SearchCaps'])

    def search(self, path, search_string, format="plain"):
        browse_data = "<ContainerID>" + path + "</ContainerID>" \
                     + "<SearchCriteria>" + search_string + "</SearchCriteria>" \
                     + "<Filter>*</Filter>" \
                     + "<StartingIndex>0</StartingIndex>" \
                     + "<RequestedCount>0</RequestedCount>" \
                     + "<SortCriteria>dc:title</SortCriteria>"
        xml_root = self.host_send_contentdirectory("Search", browse_data)
        result = XmlHelper.xml_extract_dict(xml_root, ['Result', 'TotalMatches', 'NumberReturned'])
        return self.scan_browse_result(result, 0, format)

    def browse(self, path):
        browse_data = "<ObjectID>" + path +"</ObjectID>" \
            + "<BrowseFlag>BrowseMetadata</BrowseFlag>" \
            + "<Filter>*</Filter>" \
            + "<StartingIndex>0</StartingIndex>" \
            + "<RequestedCount>0</RequestedCount>" \
            + "<SortCriteria>dc:title</SortCriteria>"
        xml_root = self.host_send_contentdirectory("Browse", browse_data)
        return XmlHelper.xml_extract_dict(xml_root, ['Result', 'TotalMatches', 'NumberReturned'])

    def browsechildren(self, path):
        browse_data = "<ObjectID>" + path + "</ObjectID>" \
            + "<BrowseFlag>BrowseDirectChildren</BrowseFlag>" \
            + "<Filter>*</Filter>" \
            + "<StartingIndex>0</StartingIndex>" \
            + "<RequestedCount>0</RequestedCount>" \
            + "<SortCriteria>dc:title</SortCriteria>"
        xml_root = self.host_send_contentdirectory("Browse", browse_data)
        if xml_root is None:
            return None
        return XmlHelper.xml_extract_dict(xml_root, ['Result', 'TotalMatches', 'NumberReturned'])

    def get_node_element(self, node, tag):
        element = node.getElementsByTagName(tag)
        if element[0].firstChild is not None:
            title = element[0].firstChild.nodeValue

    def scan_browse_result(self, result, level, output_format='plain'):
        if output_format == 'plain':
            s = ""
            xml_root = minidom.parseString(result['Result'].encode('utf-8'))
            container_list = xml_root.getElementsByTagName("container")
            for container in container_list:
                dict = DidlInfo.extract_from_node(container, True)
                npath = dict["idPath"]
                adds = "C " + npath + " * " + dict["title"] + "\n"
                s += adds
                if int(level) > 0:
                     self.browse_recursive_children(npath, int(level) - 1, output_format)
            item_list = xml_root.getElementsByTagName("item")
            for item in item_list:
                dict = DidlInfo.extract_from_node(item, True)
                npath = dict["idPath"]
                s += "+ " + npath + " * " + dict["title"] + "\n"
            return s
        else:
            s = "["
            xml_root = minidom.parseString(result['Result'])
            container_list = xml_root.getElementsByTagName("container")
            for container in container_list:
                dict = DidlInfo.extract_from_node(container, True)
                s += json.dumps(dict)
                s += ","
            item_list = xml_root.getElementsByTagName("item")
            for item in item_list:
                dict = DidlInfo.extract_from_node(item, True)
                s += json.dumps(dict)
                s += ","
            if len(s) > 2:
                s = s[:-1]
            s += "]"
            return s

    def browse_recursive_children(self, path, level=3, output_format='plain'):
        if int(level) < 0:
            return "error on level < 0"
        result = self.browsechildren(path)
        if result is None:
            result = self.browse(path)

        if len(result) == 0:
            return ""
        return self.scan_browse_result(result, int(level), output_format)

"""
#for testing
"""
def usage(argv):
    print("Usage: " + argv[0] + " ip:port [COMMAND|INFO] {args}")
    print("COMMAND: ")
    print("  play                  play last stuff")
    print("  stop                  stop current playing")
    print("  setv vol              set volume args=0..100")
    print("  seek pos              seek to position args=00:00:00 ... 99:59:59")
    print("INFO: ")
    print("  getv                  get volume info")
    print("  position              GetPositionInfo ")
    print("  media                 GetMediaInfo")
    print("  transport             GetTransportSettings ")
    print("  allinfo               all infos in one call ")
    print("BROWSE: ")
    print("  cap                   get browse capabilities")
    print("  browse path           Browse for data")
    print("  browsechildren path   Browse for data append /* for recursive")


def main(argv):
    if len(sys.argv) < 3:
        usage(sys.argv)
        sys.exit(2)

    host = sys.argv[1]
    uc = UpnpCommand(host)
    operation = sys.argv[2]
    result = None
    if operation == 'play':
        result = uc.play()
    elif operation == 'stop':
        result = uc.stop()
    elif operation == 'getv':
        result = uc.get_volume()
    elif operation == 'getfilter':
        result = uc.get_filter()
    elif operation == 'setv':
        result = uc.set_volume(sys.argv[3])
    elif operation == 'seek':
        result = uc.seek(sys.argv[3])
    elif operation == 'prev':
        result = uc.previous()
    elif operation == 'next':
        result = uc.next()
    elif operation == 'position':
        result = uc.get_position_info()
    elif operation == 'transport':
        result = uc.get_transport_setting()
    elif operation == 'getstatevar':
        result = uc.get_state_var()
    elif operation == 'media':
        result = uc.get_media_info()
        result += uc.get_position_info()
    elif operation == 'allinfo':
        result = uc.get_volume()
        result += uc.get_position_info()
        result += uc.get_transport_setting()
        result += uc.get_media_info()
    elif operation == 'cap':
        result = uc.get_browse_capabilites()
    elif operation == 'browse':
        result = uc.browse(argv[3])
        xml_root = minidom.parseString(result['Result'])
        print(xml_root.toprettyxml(indent="\t"))
    elif operation == 'browsechildren':
        if argv[3].endswith('/*'):
            result = uc.browse_recursive_children(argv[3][:-2])
            print(result)
        else:
            result = uc.browsechildren(argv[3])
            xml_root = minidom.parseString(result['Result'])
            print(xml_root.toprettyxml(indent="\t"))
        return

    else:
        usage(sys.argv)
    print(result)

if __name__ == "__main__":
    main(sys.argv)
