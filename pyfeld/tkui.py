#!/usr/bin/env python3
from __future__ import unicode_literals

import json
import subprocess

try:
    from tkinter import *
    from tkinter import ttk
    from tkinter.font import Font
except:
    print("pyfeld ui requires tkinter under python 3.x")
    exit(-1)

from pyfeld.dirBrowseExtended import DirBrowseExtended


def retrieve(cmd):
    command = 'pyfeld '+cmd
    print(command)
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except Exception as e:
        return 0
    lines = ""
    while True:
        nextline = process.stdout.readline()
        if len(nextline) == 0 and process.poll() != None:
            break
        lines += nextline.decode('utf-8')
    return lines


class ZoneContextMenu:
    def __init__(self):
        self.current_zone = 0
        self.zones = list()
        self.retrieve_zones()

    def get_zones(self):
        return self.zones

    def zone_is_active(self, index):
        return self.current_zone == index

    def set_active_zone(self, index):
        print("current zone is set to {0}".format(index))
        self.current_zone = index

    def get_zone_string(self):
        return "--zone " + str(self.current_zone) + " "

    def retrieve_zones(self):
        info = json.loads(retrieve("--discover --json info"))

        for zone in info['zones']:
            self.zones.append(zone)


class RoomContextMenu:
    def __init__(self, master, callback, zone_index, zone_udn, room_name, room_udn, is_active, is_unassigned):
        menu = Menu(master, tearoff=0, takefocus=1)
        if not is_active and not is_unassigned:
            menu.add_command(label="set zone #{0} as active".format(zone_index),
                             command=lambda: self.select_zone(callback, int(zone_index)-1))
            menu.add_separator()
        if not is_unassigned:
            menu.add_command(label="remove room {0} from zone".format(room_name),
                             command=lambda: self.remove_from_zone(callback, room_udn))
        else:
            menu.add_command(label="create zone for room {0}".format(room_name),
                         command=lambda: self.create_zone(callback, room_udn))

        menu.add_separator()
        zone_udn = list()
        idx_zone_udn = 0
        for index, zone in enumerate(zone_context.get_zones()):
            if index != int(zone_index)-1:
                zone_udn = zone['udn']
                menu.add_command(label="move room {0} to zone #{1} {2}".format(room_name, index+1, zone['name']),
                                 command=lambda room=room_udn, zone=zone_udn: self.move_zone(callback, room, zone))

        x = master.winfo_pointerx()+10
        y = master.winfo_pointery()+10
        menu.tk_popup(x, y)

    def move_zone(self, callback, room_udn, zone_udn):
        print(zone_udn)
        retrieve("--zonebyudn " + zone_udn + " --udn addtozone " + room_udn)
        callback()

    def remove_from_zone(self, callback, room):
        retrieve("--udn drop " + room)
        callback()

    def select_zone(self, callback, zone_index):
        zone_context.set_active_zone(zone_index)
        callback()

    def create_zone(self, callback, room):
        retrieve("--udn createzone " + room)
        callback()


class ItemContextMenu:
    def __init__(self, master, callback, item):
        menu = Menu(master, tearoff=0, takefocus=0)
        menu.add_command(label="enter".format(item[0]), command=lambda: self.enter_item(callback, item[0]))
        menu.add_command(label="play".format(item[0]), command=lambda: self.enter_item(callback, item[0]))
        menu.add_command(label="queue".format(item[0]), command=lambda: self.enter_item(callback, item[0]))
        menu.add_command(label="info".format(item[0]), command=lambda: self.enter_item(callback, item[0]))
        menu.add_separator()

        x = master.winfo_pointerx()+10
        y = master.winfo_pointery()+10
        menu.tk_popup(x, y)


class RaumfeldRoomInfo(Frame):
    def __init__(self, parent):
        Frame.__init__(self, master=parent)
        self.dataCols = ('Z#', 'A', 'zone', 'room', 'info')
        self.dataColSize = (40, 50, 200, 200, 200)
        self.tree = ttk.Treeview(columns=self.dataCols, show='headings')
        self.tree.bind("<Double-1>", self.on_click)
        self.tree.grid(in_=self, row=0, column=0, sticky=NSEW)
        # set frame resize priorities
        self.rowconfigure(0, weight=0)

        for i in range(len(self.dataCols)):
            c = self.dataCols[i]
            self.tree.heading(c, text=c.title(),
                              command=lambda c=c: self._column_sort(c, RaumfeldDesktop.SortDir))
            self.tree.column(c, width=self.dataColSize[i])
        self._load_browse_data()

    def _get_room_list(self):

        info_str = retrieve("--discover --json info")
        print("**** Loaded:\n",info_str,"\n**** end loaded")
        try:
            info = json.loads(info_str)
        except:
            print(info_str)
            print("there was an error with json.loads")
        i = 0
        browse_list = list()
        zone_index = 0

        for zone in info['zones']:
            if zone_context.zone_is_active(zone_index):
                active = "active"
            else:
                active = "-"

            for room in zone['rooms']:
                item = [
                    i,
                    "#" + str(zone_index+1),
                    active,
                    zone['name'],
                    room['name'],
                    "-",
                    zone['udn'],  #pack additional info to it, this is not visualized
                    room['udn'],
                    room['udn'],
                ]
                i += 1
                browse_list.append(item)
            zone_index += 1
            item = [-1, "", "", "", "", "", "", "", "", ""]
            browse_list.append(item)
        self.browse_list = browse_list
        return browse_list

    def _load_browse_data(self):
        print("reloading room/zones browse data")
        self.data = self._get_room_list()
        self.tree.delete(*self.tree.get_children())
        self.tree_index = dict()
        for idx in range(len(self.dataCols)):
            self.tree.column(self.dataCols[idx], width=10)
        for item in self.data:
            index = self.tree.insert('', 'end', values=item[1:])
            self.tree_index[index] = item
            if item[2] == 'active':
                self.tree.selection_add(index)
            for idx in range(len(self.dataCols)-1):
                i_width = Font().measure(item[idx+1]) + 10
                if self.tree.column(self.dataCols[idx], 'width') < i_width:
                    self.tree.column(self.dataCols[idx], width=i_width)

    def on_click(self, event):
        try:
            item = self.tree.selection()
            room_item = self.tree_index[item[0]]
            print("you clicked on ", str(room_item))
            is_active = room_item[2] == 'active'
            is_unassigned = 'unassigned room' in room_item[3]
            RoomContextMenu(self, self._load_browse_data, room_item[1][1:], room_item[6], room_item[4], room_item[7], is_active, is_unassigned)
        except:
            print("error with on_click ", str(item))


class ModifyRoomParam(Frame):
    def __init__(self, parent, name, minvalue, maxvalue, stepsize,
                 callback_getvalue, callback_setvalue, callback_value_up, callback_value_down):
        Frame.__init__(self, master=parent)
        self.stepsize = stepsize
        self.minvalue = minvalue
        self.maxvalue = maxvalue
        self.current_column = 0
        if name is not None:
            self.pathLabel = ttk.Label(text=name)
            self.pathLabel.grid(in_=self, row=0, column=self.current_column, ticky=EW)
        self.current_column += 1
        self.current_value = callback_getvalue()

    def value_up(self):
        self.current_value += self.stepsize
        if self.current_value > self.maxvalue:
            self.current_value = self.maxvalue

    def value_down(self):
        self.current_value -= self.stepsize
        if self.current_value < self.minvalue:
            self.current_value = self.minvalue


class CurrentZoneInfo(Frame):
    def __init__(self, parent):
        Frame.__init__(self, master=parent)
        self.show_values()

    def show_values(self):
        info_str = retrieve("--json info")
        try:
            info = json.loads(info_str)
        except:
            print("there was an error with json.loads")
        zone_index = 0
        #name  vol balance eqbass egmid eqhigh
        for zone in info['zones']:
            if zone_context.zone_is_active(zone_index):
                self.current_row = 0
                self.pathLabel = ttk.Label(text="Zone: " + zone['name'])
                self.pathLabel.grid(in_=self, row=self.current_row, column=0, columnspan=6, sticky=EW)
                self.rowconfigure(self.current_row, weight=0)
                self.current_row += 1
                for room in zone['rooms']:
                    roomlabel = ttk.Label(text=room['name'])
                    roomlabel.grid(in_=self, row=self.current_row, column=0, sticky=EW)
                    vol = ttk.Label(text="-")
                    vol.grid(in_=self, row=self.current_row, column=1, sticky=EW)
                    vol = ttk.Label(text="-")
                    vol.grid(in_=self, row=self.current_row, column=2, sticky=EW)
                    vol = ttk.Label(text="-")
                    vol.grid(in_=self, row=self.current_row, column=3, sticky=EW)
                    vol = ttk.Label(text="-")
                    vol.grid(in_=self, row=self.current_row, column=4, sticky=EW)
                    vol = ttk.Label(text="-")
                    vol.grid(in_=self, row=self.current_row, column=5, sticky=EW)
                    self.current_row += 1
            zone_index += 1


class RaumfeldInfo(Frame):
    def __init__(self, parent):
        Frame.__init__(self, master=parent)
        self.room_info = RaumfeldRoomInfo(self)
        self.room_info.pack(side=TOP, expand=N, fill=NONE)
        self.zone_info = CurrentZoneInfo(self)
        self.zone_info.pack(side=TOP, expand=N, fill=NONE)


class RaumfeldBrowseContent(Frame):
    def __init__(self, parent):
        Frame.__init__(self, master=parent)
        self.dir_browser = DirBrowseExtended()

        current_row = 0

        self.pathLabel = ttk.Label(text="0/Path")
        self.pathLabel.grid(in_=self, row=current_row, column=0, sticky=EW)
        self.rowconfigure(current_row, weight=0)
        current_row += 1
        self.search_frame = Frame()

        self.search = ttk.Label(master=self.search_frame, text="Search:")
        self.search.pack(side=LEFT, expand=N, fill=NONE)
        self.search = ttk.Entry(master=self.search_frame, text="?")
        self.search.pack(side=LEFT, expand=Y, fill=X)
        self.search_frame.grid(in_=self, row=current_row, column=0, sticky=EW)
        current_row += 1
        self.rowconfigure(current_row, weight=0)

        # create the tree and scrollbars
        self.dataCols = ('title', 'album', 'artist', 'info')
        self.dataColSize = (200, 200, 200, 100)
        self.tree = ttk.Treeview(columns=self.dataCols, show='headings')
        self.tree.bind("<Double-1>", self.OnDoubleClick)
        self.tree.bind("<Button-3>", self.OnRightClick)

        ysb = ttk.Scrollbar(orient=VERTICAL, command=self.tree.yview)
        xsb = ttk.Scrollbar(orient=HORIZONTAL, command=self.tree.xview)
        self.tree['yscroll'] = ysb.set
        self.tree['xscroll'] = xsb.set

        # add tree and scrollbars to frame
        self.tree.grid(in_=self, row=current_row, column=0, sticky=NSEW)
        ysb.grid(in_=self, row=current_row, column=1, sticky=NS)
        xsb.grid(in_=self, row=current_row+1, column=0, sticky=EW)
        # set frame resize priorities
        self.rowconfigure(current_row, weight=1)
        self.columnconfigure(0, weight=1)
        self._init_tree()
        self._load_browse_data()


    def OnDoubleClick(self, event):
        item = self.tree.selection()
        if item[0] == -1:
            return
        playitem = self.tree_index[item[0]]
        if playitem[0] == -1:
           self.dir_browser.leave()
        else:
            self.dir_browser.enter(playitem[0])
        self._load_browse_data()
        print("you clicked on ", str(playitem))

    def OnRightClick(self, event):
        item = self.tree.selection()
        if item[0] == -1:
            return
        playitem = self.tree_index[item[0]]
        res = retrieve(zone_context.get_zone_string() +'play "' + playitem[5] + '"')
        ZoneContextMenu()

    def _get_current_browse_list(self):
        browse_list = []
        if "0" != self.dir_browser.get_current_path():
            item = [-1, "..", "", "", "", ""]
            browse_list.append(item)
        for i in range(0, self.dir_browser.max_entries_on_level()):
            info = ""
            info += self.dir_browser.get_resourceType(i) + ":" + self.dir_browser.get_resourceName(i)
            if info == ':':
                info = ""
            item = [
                i,
                self.dir_browser.get_friendly_name(i),
                self.dir_browser.get_album(i),
                self.dir_browser.get_artist(i),
                info,
                self.dir_browser.get_path_for_index(i),
            ]
            browse_list.append(item)
        return browse_list

    def _init_tree(self):
        # configure column headings
        for i in range(len(self.dataCols)):
            c = self.dataCols[i]
            self.tree.heading(c, text=c.title(),
                              command=lambda c=c: self._column_sort(c, RaumfeldDesktop.SortDir))
            self.tree.column(c, width=self.dataColSize[i])

    def _load_browse_data(self):
        self.data = self._get_current_browse_list()
        self.pathLabel['text'] = "> " + self.dir_browser.get_friendly_path_name(" + ")
        self.tree.delete(*self.tree.get_children())
        # add data to the tree
        self.tree_index = dict()
        for idx in range(len(self.dataCols)):
            self.tree.column(self.dataCols[idx], width=10)
        for item in self.data:
            index = self.tree.insert('', 'end', values=item[1:])
            self.tree_index[index] = item
            for idx in range(len(self.dataCols)):
                iwidth = Font().measure(item[idx + 1]) + 10
                if self.tree.column(self.dataCols[idx], 'width') < iwidth:
                    self.tree.column(self.dataCols[idx], width=iwidth)

    def _column_sort(self, col, descending=False):
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        data.sort(reverse=descending)
        for index, item in enumerate(data):
            self.tree.move(item[1], '', index)  # item[1] = item Identifier
        RaumfeldDesktop.SortDir = not descending

    def play_selection(self):
        item = self.tree.selection()
        play_item = self.tree_index[item[0]]
        res = retrieve(zone_context.get_zone_string() + 'play "' + play_item[5] + '"')
        print(str(res))


class RaumfeldDesktop(Frame):

    """
    the interfaces is divided in 2x2 parts
    """
    SortDir = True     # descending

    def __init__(self, isapp=True, name='raumfelddesktop', master=None):
        global zone_context
        zone_context = ZoneContextMenu()
        Frame.__init__(self, master=master, name=name)
        self.grid()
        ws = self.winfo_screenwidth()  # width of the screen
        hs = self.winfo_screenheight()  # height of the screen
        if float(ws)/float(hs) > 2.5:
            ws /= 2
        geo_set = str(int(ws)-300) + "x" + str(int(hs)-300) + "+150+150"
        print(geo_set)
        self.master.geometry(geo_set)
        self.master.rowconfigure(0, weight=0)
        self.master.columnconfigure(0, weight=0)
        self.master.rowconfigure(1, weight=1)
        self.master.columnconfigure(1, weight=1)
        self.info = json.loads(retrieve('--json --discover info'))
        self.volume = retrieve(zone_context.get_zone_string() + "getvolume")
        self.master.title('Raumfeld browse songs')
        self.isapp = isapp
        self._create_panel(master)

    def _reload_button_hit(self):
        self._create_panel(self.master)

    def _play_button_hit(self):
        self.browse_tree_frame.play_selection()

    def _volume_down_button_hit(self):
        self.volume = retrieve(zone_context.get_zone_string() + "getvolume")
        self.volume = int(self.volume) - 5
        if self.volume < 0:
            self.volume = 0
        retrieve(zone_context.get_zone_string() + 'volume ' + str(self.volume))

    def _volume_up_button_hit(self):
        self.volume = retrieve(zone_context.get_zone_string() + "getvolume")
        self.volume = int(self.volume) + 5
        if self.volume > 100:
            self.volume = 100
        retrieve(zone_context.get_zone_string() + 'volume ' + str(self.volume))

    def _stop_button_hit(self):
        retrieve(zone_context.get_zone_string() + 'stop')

    def _prev_button_hit(self):
        retrieve(zone_context.get_zone_string() + 'prev')

    def _next_button_hit(self):
        retrieve(zone_context.get_zone_string() + 'next')

    def _create_buttons(self, parent):
        f = Frame(parent)
        Button(f, text="reload", command=self._reload_button_hit).pack(side=LEFT)
        Button(f, text="play", command=self._play_button_hit).pack(side=LEFT)
        Button(f, text="stop", command=self._stop_button_hit).pack(side=LEFT)
        Button(f, text="prev", command=self._prev_button_hit).pack(side=LEFT)
        Button(f, text="next", command=self._next_button_hit).pack(side=LEFT)
        Button(f, text="vol-", command=self._volume_down_button_hit).pack(side=LEFT)
        Button(f, text="vol+", command=self._volume_up_button_hit).pack(side=LEFT)
        return f

    def _create_panel(self, master):
        self.browse_tree_frame = RaumfeldBrowseContent(master)
        self.browse_tree_frame.grid(row=1, column=1, padx=2, sticky=NSEW)
        self.buttons_frame = self._create_buttons(master)
        self.buttons_frame.grid(row=0, column=0, rowspan=1, padx=2, columnspan=2, sticky=NSEW)
        self.rooms_tree_frame = RaumfeldInfo(master)
        self.rooms_tree_frame.grid(row=1, column=0, padx=2, sticky=NSEW)

def run_main():
    RaumfeldDesktop().mainloop()

if __name__ == '__main__':
    RaumfeldDesktop().mainloop()
