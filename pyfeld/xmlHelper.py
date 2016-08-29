from __future__ import unicode_literals

class XmlHelper:
    @staticmethod
    def xml_extract_dict(xml, extract_keys):
        result_dict = {}
        for k in extract_keys:
            try:
                element = xml.getElementsByTagName(k)
                result_dict[k] = element[0].firstChild.nodeValue
            except Exception as e:
                result_dict[k] = ""
        return result_dict

    def xml_extract_dict_by_val(xml, extract_keys):
        result_dict = {}
        for k in extract_keys:
            try:
                element = xml.getElementsByTagName(k)
                result_dict[k] = element[0].getAttribute("val")
            except Exception as e:
                pass
        return result_dict


