import time

from pyfeld.xmlHelper import XmlHelper

class UuidStoreKeys:
    @staticmethod
    def get_key_and_setting():
        return [['AbsoluteTimePosition', True, False],
                ['AVTransportURI', False, False],
                ['AVTransportURIMetaData', False, False],
                ['Bitrate', True, False],
                ['ContentType', True, False],
                ['CurrentPlayMode', False, False],
                ['CurrentRecordQualityMode', False, False],
                ['CurrentTrack', True, False],
                ['CurrentTrackDuration', True, False],
                ['CurrentTrackMetaData', False, True],
                ['CurrentTrackURI', False, False],
                ['CurrentTransportActions', False, False],
                ['HighDB', True, False],
                ['LowDB', True, False],
                ['MidDB', True, False],
                ['Mute', True, False],
                ['PowerState', True, False],
                ['RelativeCounterPosition', True, False],
                ['RelativeTimePosition', True, False],
                ['RoomMutes', False, False],
                ['RoomVolumes', False, False],
                ['SecondsUntilSleep', True, False],
                ['SleepTimerActive', True, False],
                ['TransportState', True, False],
                ['TransportStatus', True, False],
                ['Volume', True, False],
                ['VolumeDB', True, False],
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
        # print(xmldom.toprettyxml())
        key_list = list()
        for item in UuidStoreKeys.get_key_and_setting():
            key_list.append(item[0])
        items = XmlHelper.xml_extract_dict_by_val(xmldom, key_list)
        changed = False
        try:
            for key, value in items.items():
                if key in self.itemMap:
                    self.itemMap[key].update(value)
                else:
                    self.itemMap[key] = SingleItem(value)
    #            if key == 'CurrentTrackMetaData':
    #                DidlInfo(value[0])
            if changed:
                self.timeChanged = time.time()
        except Exception as e:

            print("SingleUUID error {0}".format(e))


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
        return
        print("###### SHOW UuidStore ######")
        for dummy, item in self.uuid.items():
            print(item.uuid, item.rf_type, item.name)
            for key, value in item.itemMap.items():
                print(key, value.value)
