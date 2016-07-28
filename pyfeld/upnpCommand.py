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
        xmlroot = self.host_send_transport("Play",  '<InstanceID>0</InstanceID><Speed>1</Speed>')
        return xmlroot.toprettyxml()

    def stop(self):
        xmlroot = self.host_send_transport("Stop",  '<InstanceID>0</InstanceID>')
        return xmlroot.toprettyxml()

    def seek(self, value):
        xmlroot = self.host_send_transport("Seek",
                                           '<InstanceID>0</InstanceID><Unit>ABS_TIME</Unit>'
                                           '<Target>' + value + '</Target>')
        return xmlroot.toprettyxml()

    def previous(self):
        xmlroot = self.host_send_transport("Previous", '<InstanceID>0</InstanceID>')
        return xmlroot.toprettyxml()

    def next(self):
        xmlroot = self.host_send_transport("Next", '<InstanceID>0</InstanceID>')
        return xmlroot.toprettyxml()

    def get_state_var(self):
        xmlroot = self.host_send_rendering("GetStateVariables",
                                           '<InstanceID>0</InstanceID><'
                                           'StateVariableList>TransportStatus</StateVariableList>')
        return xmlroot.toprettyxml()

    def get_position_info(self):
        xmlroot = self.host_send_transport("GetPositionInfo",  '<InstanceID>0</InstanceID>')
        return XmlHelper.xml_extract_dict(xmlroot, ['Track',
                                                    'TrackDuration',
                                                    'TrackMetaData',
                                                    'TrackURI',
                                                    'RelTime',
                                                    'AbsTime',
                                                    'RelCount',
                                                    'AbsCount'])

    def get_transport_setting(self):
        xmlroot = self.host_send_transport("GetTransportSettings",  '<InstanceID>0</InstanceID>')
        return XmlHelper.xml_extract_dict(xmlroot, ['PlayMode'])

    def get_media_info(self):
        xmlroot = self.host_send_transport("GetMediaInfo",  '<InstanceID>0</InstanceID>')
        return XmlHelper.xml_extract_dict(xmlroot, ['PlayMedium', 'NrTracks', 'CurrentURI', 'CurrentURIMetaData'])

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
        print(data['CurrentURIMetaData'])
        xmlroot = self.host_send_transport("SetAVTransportURI", send_data)
        return XmlHelper.xml_extract_dict(xmlroot, ['SetAVTransportURI'])

    '''Rendering service'''

    def get_volume(self, format = 'plain'):
        xmlroot = self.host_send_rendering("GetVolume", '<InstanceID>0</InstanceID><Channel>Master</Channel>')
        dict = XmlHelper.xml_extract_dict(xmlroot, ['CurrentVolume'])
        if format == 'json':
            return '{ "CurrentVolume": "'+dict['CurrentVolume'] + '"}'
        else:
            return dict['CurrentVolume']

    def set_volume(self, value):
        xmlroot = self.host_send_rendering("SetVolume",
                                           '<InstanceID>0</InstanceID><Channel>Master</Channel>' +
                                           '<DesiredVolume>' + str(value) + '</DesiredVolume>')
        return xmlroot.toprettyxml()

    def get_room_volume(self, uuid):
        xmlroot = self.host_send_rendering("GetRoomVolume", '<InstanceID>0</InstanceID>'
                                           '<Room>' + uuid + '</Room>')
        return XmlHelper.xml_extract_dict(xmlroot, ['CurrentVolume'])

    def set_room_volume(self, uuid, value):
        xmlroot = self.host_send_rendering("SetVolume",
                                           '<InstanceID>0</InstanceID><Channel>Master</Channel>' +
                                           '<DesiredVolume>' + str(value) + '</DesiredVolume>' +
                                           '<Room>' + uuid + '</Room>')
        return None

    def get_browse_capabilites(self):
        xmlroot = self.host_send_contentdirectory("GetSearchCapabilities", '')
        return XmlHelper.xml_extract_dict(xmlroot, ['SearchCaps'])

    def search(self, path, search_string, format="plain"):
        browseData = "<ContainerID>" + path + "</ContainerID>" \
                     + "<SearchCriteria>" + search_string + "</SearchCriteria>" \
                     + "<Filter>*</Filter>" \
                     + "<StartingIndex>0</StartingIndex>" \
                     + "<RequestedCount>0</RequestedCount>" \
                     + "<SortCriteria>dc:title</SortCriteria>"
        xmlroot = self.host_send_contentdirectory("Search", browseData)
        result = XmlHelper.xml_extract_dict(xmlroot, ['Result', 'TotalMatches', 'NumberReturned'])
        return self.scan_browse_result(result, 0, format)


    def browse(self, path):
        browseData = "<ObjectID>" + path +"</ObjectID>" \
            + "<BrowseFlag>BrowseMetadata</BrowseFlag>" \
            + "<Filter>*</Filter>" \
            + "<StartingIndex>0</StartingIndex>" \
            + "<RequestedCount>0</RequestedCount>" \
            + "<SortCriteria>dc:title</SortCriteria>"
        xmlroot = self.host_send_contentdirectory("Browse", browseData)
        return XmlHelper.xml_extract_dict(xmlroot, ['Result', 'TotalMatches', 'NumberReturned'])

    def browsechildren(self, path):
        browseData = "<ObjectID>" + path + "</ObjectID>" \
            + "<BrowseFlag>BrowseDirectChildren</BrowseFlag>" \
            + "<Filter>*</Filter>" \
            + "<StartingIndex>0</StartingIndex>" \
            + "<RequestedCount>0</RequestedCount>" \
            + "<SortCriteria>dc:title</SortCriteria>"
        xmlroot = self.host_send_contentdirectory("Browse", browseData)
        if xmlroot is None:
            return None
        return XmlHelper.xml_extract_dict(xmlroot, ['Result', 'TotalMatches', 'NumberReturned'])

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
                s += "C " + npath + " * " + dict["title"] + "\n"
                if level > 0:
                     self.browse_recursive_children(npath, level - 1, output_format)
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

    def browse_recursive_children(self, path, output_format='plain', level=3):
        if level < 0:
            return "error on level < 0"
        result = self.browsechildren(path)
        if result is None:
            result = self.browse(path)

        if len(result) == 0:
            return ""
        return self.scan_browse_result(result, level, output_format)


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
        xmlRoot = minidom.parseString(result['Result'])
        print(xmlRoot.toprettyxml(indent="\t"))
    elif operation == 'browsechildren':
        if argv[3].endswith('/*'):
            result = uc.browse_recursive_children(argv[3][:-2])
            print(result)
        else:
            result = uc.browsechildren(argv[3])
            xmlRoot = minidom.parseString(result['Result'])
            print(xmlRoot.toprettyxml(indent="\t"))
        return

    else:
        usage(sys.argv)
    print(result)

if __name__ == "__main__":
    main(sys.argv)
