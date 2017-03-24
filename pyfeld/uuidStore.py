import time

from pyfeld.xmlHelper import XmlHelper

class UuidStoreKeys:
    @staticmethod

    def get_keys():
        return ['AbsoluteTimePosition',
                # 'AVTransportURI',
                # 'AVTransportURIMetaData',
                'Bitrate',
                'ContentType',
                #'CurrentPlayMode',
                #'CurrentRecordQualityMode',
                'CurrentTrack',
                'CurrentTrackDuration',
                # 'CurrentTrackMetaData',
                # 'CurrentTrackURI',
                #'CurrentTransportActions',
                'HighDB',
                'LowDB',
                'MidDB',
                'Mute',
                'PowerState',
                'RelativeCounterPosition',
                'RelativeTimePosition',
                # 'RoomMutes',
                # 'RoomVolumes',
                'SecondsUntilSleep',
                'SleepTimerActive',
                'TransportState',
                'TransportStatus',
                'Volume',
                'VolumeDB'
                ]

class SingleItem:
    def __init__(self, value):
        self.timeChanged = time.time()
        self.value = value

    def update(self, value):
        self.value = value
        self.timeChanged = time.time()


class SingleUuid:
    def __init__(self, uuid, rf_type, name):
        self.uuid = uuid
        self.rf_type = rf_type
        self.name = name
        self.timeChanged = time.time()
        self.itemMap = dict()

    def update(self, xmldom):
        #print(xmldom.toprettyxml())
        items = XmlHelper.xml_extract_dict_by_val(xmldom, UuidStoreKeys.get_keys())
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
        self.callback = None

    def set_update_cb(self, cb):
        self.callback = cb

    def set(self, uuid, rf_type, name, xmldom):
        if uuid not in self.uuid:
            self.uuid[uuid] = SingleUuid(uuid, rf_type, name)
        self.uuid[uuid].update(xmldom)
        if self.callback is None:
            self.show()
        else:
            self.callback(self)

    def show(self):
        for dummy, item in self.uuid.items():
            print(item.uuid, item.rf_type, item.name)
            for key, value in item.itemMap.items():
                print(key, value.value)
