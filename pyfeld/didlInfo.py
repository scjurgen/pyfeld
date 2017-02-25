#!/usr/bin/env python
from __future__ import unicode_literals

from xml.dom import minidom


class DidlInfo:

    @staticmethod
    def getTagNameValue(root_item, tag):
        return root_item.getElementsByTagName(tag)[0].childNodes[0].nodeValue

    def __init__(self, didl_data, fill_all=False):
        xml_Root = minidom.parseString(didl_data.encode('utf-8'))
        try:
            elem = xml_Root.getElementsByTagName("item")[0]

        except:
            try:
                elem = xml_Root.getElementsByTagName("container")[0]
            except Exception as e:
                print("parsing didl is odd {0}".format(e))
                return
        self.items = self.extract_from_node(elem, fill_all)

    @staticmethod
    def extract_from_node(elem, fill_all):
        item_list = {
            'id': 'id'
            , 'raumfeld:name': 'raumfeldname'
            , 'raumfeld:sourceID': 'rfsourceID'
            , 'dc:title': 'title'
            , 'dc:description': 'description'
            , 'dc:creator': 'creator'
            , 'dc:date': 'date'
            , 'upnp:album': 'album'
            , 'upnp:artist': 'artist'
            , 'upnp:genre': 'genre'
            , 'upnp:originalTrackNumber': 'tracknumber'
            , 'upnp:albumArtURI': 'albumarturi'
            , 'upnp:class': 'class'
            , 'res': 'res'
        }
        #print(xml_Root.toprettyxml())
        items = dict()

        try:
            items['parentID'] = elem.attributes["parentID"].value
        except:
            items['parentID'] = ""
        try:
            items['refID'] = elem.attributes["refID"].value
        except:
            items['refID'] = None
        try:
            items['idPath'] = elem.attributes["id"].value
        except:
            items['idPath'] = ""
        if fill_all:
            items['resSampleFrequency'] = ""
            items['resBitrate'] = ""
            items['resSourceType'] = ""
            items['resSourceName'] = ""
            items['resSourceID'] = ""
        try:
            resElem = elem.getElementsByTagName('res')[0]
            items['resSampleFrequency'] = resElem.attributes['sampleFrequency'].value
            items['resBitrate'] = resElem.attributes['bitrate'].value
            items['resSourceType'] = resElem.attributes['sourceType'].value
            items['resSourceName'] = resElem.attributes['sourceName'].value
            items['resSourceID'] = resElem.attributes['sourceID'].value
        except Exception as e:
            pass
        for item_tag, key in item_list.items():
            try:
                res = DidlInfo.getTagNameValue(elem, item_tag)
                items[key] = res
            except Exception as e:
                if fill_all:
                    items[key] = ""
        return items
#                print("I guess not found: {0} {1}".format(item_tag,e))

    def get_items(self):
        return self.items

    def print_items(self):
        print(self.items)



if __name__ == "__main__":
    didl = '''&lt;DIDL-Lite xmlns=&quot;urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/&quot; xmlns:raumfeld=&quot;urn:schemas-raumfeld-com:meta-data/raumfeld&quot; xmlns:upnp=&quot;urn:schemas-upnp-org:metadata-1-0/upnp/&quot; xmlns:dc=&quot;http://purl.org/dc/elements/1.1/&quot; xmlns:dlna=&quot;urn:schemas-dlna-org:metadata-1-0/&quot; lang=&quot;en&quot;&gt;&lt;item parentID=&quot;0/My Music/Artists/Al%20Di%20Meola/Al%20Di%20Meola+Elegant%20Gypsy&quot; id=&quot;0/My Music/Artists/Al%20Di%20Meola/Al%20Di%20Meola+Elegant%20Gypsy/74b3a119cec2e26e1d3bd0c9d4740e51&quot; restricted=&quot;1&quot;&gt;&lt;raumfeld:name&gt;Track&lt;/raumfeld:name&gt;&lt;upnp:class&gt;object.item.audioItem.musicTrack&lt;/upnp:class&gt;&lt;raumfeld:section&gt;My Music&lt;/raumfeld:section&gt;&lt;dc:title&gt;Flight Over Rio&lt;/dc:title&gt;&lt;upnp:album&gt;Elegant Gypsy&lt;/upnp:album&gt;&lt;upnp:artist&gt;Al Di Meola&lt;/upnp:artist&gt;&lt;upnp:genre&gt;Fusion&lt;/upnp:genre&gt;&lt;dc:creator&gt;Al Di Meola&lt;/dc:creator&gt;&lt;upnp:originalTrackNumber&gt;1&lt;/upnp:originalTrackNumber&gt;&lt;dc:date&gt;1977-01-01&lt;/dc:date&gt;&lt;upnp:albumArtURI dlna:profileID=&quot;JPEG_TN&quot;&gt;http://192.168.2.100:47366/?artist=Al%20Di%20Meola&amp;amp;albumArtist=Al%20Di%20Meola&amp;amp;album=Elegant%20Gypsy&amp;amp;track=Flight%20Over%20Rio&lt;/upnp:albumArtURI&gt;&lt;res protocolInfo=&quot;http-get:*:audio/mpeg:DLNA.ORG_PN=MP3&quot; size=&quot;13957120&quot; duration=&quot;0:07:16.000&quot; bitrate=&quot;256000&quot; sampleFrequency=&quot;44100&quot; nrAudioChannels=&quot;2&quot; sourceName=&quot;KINGSTON&quot; sourceType=&quot;usb&quot; sourceID=&quot;E2CC-190B&quot;&gt;http://192.168.2.100:53918/redirect?uri=file%3A%2F%2F%2Fmedia%2FE2CC-190B%2FAl%2520Di%2520Meola%2520-%2520%255BElegant%2520Gypsy%255D%2FAl%2520Di%2520Meola%2520-%2520%255BElegant%2520Gypsy%255D%2520-%2520%252801%2529%2520-%2520Flight%2520Over%2520Rio.mp3&lt;/res&gt;&lt;/item&gt;&lt;/DIDL-Lite&gt;'''
    d = DidlInfo(didl)
    d.print_items()
