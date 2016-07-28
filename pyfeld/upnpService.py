from __future__ import unicode_literals

import urllib3

from xml.dom import minidom

from pyfeld.upnpsoap import UpnpSoap
from pyfeld.xmlHelper import XmlHelper


class Services:

    @staticmethod
    def get_services_from_location(location):
        try:
            (xml_headers, xml_data) = UpnpSoap.get(location)
            if xml_data is not False:
                xml_root = minidom.parseString(xml_data)
                services_list = list()
                for service in xml_root.getElementsByTagName("service"):
                    service_dict = XmlHelper.xml_extract_dict(service, ['serviceType',
                                                                   'controlURL',
                                                                   'eventSubURL',
                                                                   'SCPDURL',
                                                                   'serviceId'])
                    services_list.append(service_dict)
                return services_list
        except Exception as e:
            print("Error get_subscription_urls:{0}".format(e))
        return None


class UpnpService:
    def __init__(self):
        self.services_list = list()
        self.xml_location = ""
        self.network_location = ""

    def set_location(self, location):
        self.xml_location = location
        result = urllib3.util.parse_url(location)
        self.network_location = result.netloc
        self.services_list = Services.get_services_from_location(location)

    def get_network_location(self):
        return self.network_location

    def get_services_list(self):
        return self.services_list