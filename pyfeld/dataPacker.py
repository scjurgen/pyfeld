



class DataPacker:

    #list data type will only write out the values without the key
    @staticmethod
    def dataTypeList():
        return "list"

    @staticmethod
    def dataTypeObject():
        return "object"

    def __init__(self, type):
        self.type = type
        self.data = []

    def add_pair(self, key, value):
        self.data.append([key, value])

    def add_value(self, key, value):
        self.data.append(key, value)

    def to_string(self, coding):
        if self.type == self.dataTypeObject():
            if coding == 'json':
                s = "{"
                for item in self.data:
                    s += ' "' + item[0] + '": '
                    s += '"' + item[1] + '"\n'
                s += "}"
            else:
                for item in self.data:
                    s += item[0].replace('=', '\\=') + '='
                    s += item[1] + '\n'
        if self.type == self.dataTypeList():
            if coding == 'json':
                s = "["
                for item in self.data:
                    s += '"' + item[1] + '"\n'
                s += "]"
            else:
                for item in self.data:
                    s += item[1] + '\n'
        return s
