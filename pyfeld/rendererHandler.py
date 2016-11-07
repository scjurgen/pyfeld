
from pyfeld.upnpsoap import UpnpSoap


class RendererHandler:

    def __init__(self, host, udn):
        self.host = "http://" + host + ":47365/"
        self.udn = udn

    def set_stereo_widening(self, enable):
        (xml_headers, xml_data) = UpnpSoap.get(self.host+"ToggleFilter?enable="+enable+"&filter=stereo-widening&udn=uuid%3A"+self.udn)

    def set_linein_volume(self, value):
        (xml_headers, xml_data) = UpnpSoap.get(self.host + "SetRendererLineinVolume?udn=uuid%3A" + self.udn + "&volumeLevel=" + value + "%25")

    def set_renderer_prefs_key_value(self, key, value):
        (xml_headers, xml_data) = UpnpSoap.get(self.host + "ChangeRendererPrefsAction?udn=uuid%3A" + self.udn + "+&key=" + key+"&value=" + value)

    def set_prefs_key_value(self, path, key, value):
        (xml_headers, xml_data) = UpnpSoap.get(
            self.host + "SetPrefValue?path="+path+"name=Renderer&id=uuid%3A" + self.udn + "+&key=" + key + "&value=" + value)

    def set_suspend_power(self, value):
        if value in ['yes', 'no']:
            self.set_prefs_key_value("%2FPreferences%2FZoneConfig%2FRenderers","SuspendOnPowerButtonPress", value)

    def set_max_sample_rate(self, value):
        if value in ['44100', '48000', '96000', '192000']:
            self.set_renderer_prefs_key_value("MaxSampleRate", value)

    def set_stereo_mono(self, value):
        if value in ['mono-l', 'mono-r', 'mono']:
            self.set_renderer_prefs_key_value("Routing", value)

    def share_cast_data(self, value):
        if value in ['yes', 'no']:
            self.set_prefs_key_value("%2FPreferences%2FZoneConfig%2FRenderers", "ShareGoogleCastUsageData", value)

    def set_autostandby_delay(self, seconds):
        self.set_renderer_prefs_key_value("AutoStandByDelayInSeconds", str(seconds))

    def set_leds(self, enable):
        if enable in ['on', 'off']:
            self.set_renderer_prefs_key_value("DisableLEDs", enable)

