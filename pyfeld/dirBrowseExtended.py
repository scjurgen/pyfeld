#!/usr/bin/env python3

from __future__ import unicode_literals
import json


from rfcmd import run_command


def rf_command_line():
    return 'pyfeld --json browse'


class DirLevel:
    def __init__(self, path, friendly_name, items):
        self.path = path
        self.friendly_name = friendly_name
        self.items = items

class DirBrowseExtended:

    def __init__(self):
        dNull = DirLevel("0", "services", self.retrieve("0"))
        self.path = "0"
        self.pathes = ["0"]
        self.dirs = [dNull]
        self.depth = 0
        self.retrieve(self.pathes[self.depth])

    def get_current_path(self):
        return self.path

    def enter(self, index):
        self.path = self.dirs[self.depth].items[index]['idPath']
        items = self.retrieve(self.path)
        new_dir = DirLevel(self.path, self.dirs[self.depth].items[index]['title'], items)
        self.depth += 1
        if len(self.dirs) <= self.depth:
            self.dirs.append(new_dir)
        else:
            self.dirs[self.depth] = new_dir

    def enter_by_friendly_name(self, name):
        pass

    def leave(self):
        if self.depth != 0:
            self.depth -= 1
        self.path = self.dirs[self.depth].path

    def retrieve(self, path):
        command = rf_command_line()
        if type(path).__name__ == 'bytes':
            command += ' ' + path.decode('utf-8') + ''
        else:
            command += ' ' + path + ''
        try:
            args = command.split(" ")
            jsonFile = run_command(args)
        except Exception as e:
            return 0
        return json.loads(jsonFile)

    def get_friendly_path_name(self, separator=" -> "):
        s = ""
        for i in range(1, self.depth+1):
            s += self.dirs[i].friendly_name + separator
        return s[:-len(separator)]  #remove padded separator

    def get_friendly_name(self, index):
        return self.dirs[self.depth].items[index]['title']

    def get_path_for_index(self, index):
        return self.dirs[self.depth].items[index]['idPath']

    def get_type(self, index):
        return self.dirs[self.depth].items[index]['class']

    def get_albumarturi(self, index):
        return self.dirs[self.depth].items[index]['albumarturi']

    def get_album(self, index):
        return self.dirs[self.depth].items[index]['album']

    def get_artist(self, index):
        return self.dirs[self.depth].items[index]['artist']

    def get_class(self, index):
        return self.dirs[self.depth].items[index]['class']

    def get_resourceName(self, index):
        return self.dirs[self.depth].items[index]['resSourceName']

    def get_resourceType(self, index):
        return self.dirs[self.depth].items[index]['resSourceType']

    def max_entries_on_level(self):
        return len(self.dirs[self.depth].items)

if __name__ == '__main__':
    db = DirBrowseExtended()
    db.enter(0)
    db.enter(3)
    print(str(db.dirs[2].items[0]))
    for item in db.dirs[2].items:
        print(item['title'].encode('utf-8'),
              item['class'].encode('utf-8'),
              item['resSourceName'].encode('utf-8'),
              item['album'].encode('utf-8'),
              item['albumarturi'].encode('utf-8'),
              item['artist'].encode('utf-8'),
              )
