#!/usr/bin/env python

from __future__ import unicode_literals

import re
import subprocess
def rfCmd():
    return 'pyfeld browse'


class DirLevel:
    def __init__(self, path, friendly_name, items):
        self.path = path
        self.friendly_name = friendly_name
        self.items = items

class DirBrowse:

    def __init__(self):
        dNull = DirLevel("0", "services", self.retrieve("0"))
        self.path = "0"
        self.pathes = ["0"]
        self.dirs = [dNull]
        self.depth = 0
        self.retrieve(self.pathes[self.depth])

    def get_current_path(self):
        return self.path

    @staticmethod
    def split_browse(lines, nextline):
        result = re.match('^([C+]) (.*) \\*(.*)$', nextline)
        if result:
            type_string = ""
            if result.group(1) == 'C':
                type_string = "D"  #directory (container)
            if result.group(1) == '+':
                type_string = "F"  #file (track)
            path = result.group(2).encode('utf-8')
            friendly_name = result.group(3)
            lines.append([type_string, path, friendly_name])

    def enter(self, index):
        self.path = self.dirs[self.depth].items[index][1]
        items = self.retrieve(self.path)
        new_dir = DirLevel(self.path, self.dirs[self.depth].items[index][2], items)
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
        command = rfCmd()
        if type(path).__name__ == 'bytes':
            command += ' "' + path.decode('utf-8') + '"'
        else:
            command += ' "' + path + '"'
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except Exception as e:
            return 0
        lines = list()
        while True:
            nextline = process.stdout.readline()
            if len(nextline) == 0 and process.poll() != None:
                break
            self.split_browse(lines, nextline.decode('utf-8'))
        return lines

    def get_friendly_path_name(self, separator=" -> "):
        s = ""
        for i in range(1, self.depth+1):
            s += self.dirs[i].friendly_name + separator
        return s[:-len(separator)]  #remove padded separator

    def get_friendly_name(self, index):
        return self.dirs[self.depth].items[index][2]

    def get_path_for_index(self, index):
        return self.dirs[self.depth].items[index][1]

    def get_type(self, index):
        return self.dirs[self.depth].items[index][0]

    def max_entries_on_level(self):
        return len(self.dirs[self.depth].items)

