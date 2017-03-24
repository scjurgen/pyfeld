import time

from pyfeld.xmlHelper import XmlHelper


class SingleItem:
    def __init__(self, value):
        self.timeChanged = time.time()
        self.value = value

    def update(self, value):
        pass


class SingleUuid:
    def __init__(self, uuid, rf_type, name):
        self.uuid = uuid
        self.rf_type = rf_type
        self.name = name
        self.timeChanged = time.time()
        self.itemMap = dict()

    def update(self, xmldom):
        #print(xmldom.toprettyxml())
        items = XmlHelper.xml_extract_dict_by_val(xmldom, ['AbsoluteTimePosition',
                                                           'AVTransportURI',
                                                           'AVTransportURIMetaData',
                                                           'Bitrate',
                                                           'ContentType',
                                                           'CurrentPlayMode',
                                                           'CurrentRecordQualityMode',
                                                           'CurrentTrack',
                                                           'CurrentTrackDuration',
                                                           'CurrentTrackMetaData',
                                                           'CurrentTrackURI',
                                                           'CurrentTransportActions',
                                                           'HighDB',
                                                           'LowDB',
                                                           'MidDB',
                                                           'Mute',
                                                           'PowerState',
                                                           'RelativeCounterPosition',
                                                           'RelativeTimePosition',
                                                           'RoomMutes',
                                                           'RoomVolumes',
                                                           'SecondsUntilSleep',
                                                           'SleepTimerActive',
                                                           'TransportState',
                                                           'TransportStatus',
                                                           'Volume',
                                                           'VolumeDB'
                                                           ])
        changed = False
        for key, value in items.items():
            if key in self.itemMap:
                self.itemMap[key].update(value)
            else:
                self.itemMap[key] = SingleItem(value)
        if changed:
            self.timeChanged = time.time()
        pass


class UuidStore:
    def __init__(self):
        self.uuid = dict()

    def set(self, uuid, rf_type, name, xmldom):
        if uuid not in self.uuid:
            self.uuid[uuid] = SingleUuid(uuid, rf_type, name)
        self.uuid[uuid].update(xmldom)
        self.show()

    def show(self):
        for key, item in self.uuid.items():
            print(item.uuid, item.rf_type, item.name)
            for key, value in item.itemMap.items():
                print(key, value.value)
