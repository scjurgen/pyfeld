#!/usr/bin/env python3
from __future__ import unicode_literals

import curses
import re
import sys

import subprocess

from pyfeld.dirBrowse import DirBrowse

returnString = None

class MainGui:
    def __init__(self):
        self.selected_index_stack = [0]
        self.returnString = ""
        self.play_in_room = None
        self.dir = DirBrowse()
        self.selected_index = 0
        self.selected_column = 0
        self.window = curses.initscr()
        curses.start_color()
        curses.noecho()
        curses.cbreak()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_BLUE, curses.COLOR_RED)
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLUE)

        self.window.keypad(1)
        self.draw_ui()

    def set_room(self, room):
        self.play_in_room = room

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.window.keypad(0)
        curses.echo()
        curses.nocbreak()
        curses.endwin()

    def draw_ui(self):
        self.window.clear()
        self.window.addstr(0, 0, "Path:  " + self.dir.get_friendly_path_name(">"))

        (self.screen_height, self.screen_width) = self.window.getmaxyx()
        self.window.addstr(0, 0, "")
        self.window.addstr(self.screen_height - 2, 0, "Arrow keys: select device")
        self.window.addstr(self.screen_height - 1, 0, "P)lay S)top H)elp Q)uit Return")
        self.show_dir()
        self.window.refresh()

    def show_dir(self):
        try:
            for i in range(0, self.dir.max_entries_on_level()):
                if i == self.selected_index:
                    col = curses.color_pair(1)
                else:
                    col = curses.color_pair(3)
                if self.dir.get_type(i) == 'D':
                    vis_string = "> "
                else:
                    vis_string = "  "
                vis_string += self.dir.get_friendly_name(i)
                self.window.addstr(i+3, 0, vis_string, col)
        except:
            pass

    def enter_dir(self):
        self.dir.enter(self.selected_index)

    def leave_dir(self):
        self.dir.leave()

    def play(self):
        path = self.dir.get_path_for_index(self.selected_index).decode("utf-8")
        if self.play_in_room is None:
            command = 'pyfeld -z 0 play "' + path + '"'
        else:
            command = 'pyfeld --zonewithroom "' + self.play_in_room + '" play "' + path + '"'
        self.window.addstr(1, 0, command)

        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except Exception as e:
            self.window.addstr(0, 0, "Launching pyfeld failed")
            return 0
        lines = list()
        while True:
            nextline = process.stdout.readline()
            if len(nextline) == 0 and process.poll() != None:
                break
        self.window.addstr(1, 0, str(lines))
        return lines


    def run_main_loop(self):
        self.draw_ui()
        while 1:
            c = self.window.getch()
            if curses.keyname(c) in [b'h', b'H']:
                self.show_help()
            elif curses.keyname(c) in [b'p', b'P']:
                self.play()
            elif curses.keyname(c) in [b'q', b'Q']:
                return None
            elif c == 27:
                self.returnString = self.dir.get_current_path()
                return self.returnString
            elif c == curses.KEY_ENTER or c == 10:
                self.returnString = self.dir.get_current_path()
                return self.returnString
            elif c == curses.KEY_UP:
                if self.selected_index > 0:
                    self.selected_index -= 1
                self.draw_ui()
            elif c == curses.KEY_DOWN:
                if self.selected_index < self.dir.max_entries_on_level()-1:
                    self.selected_index += 1
                self.draw_ui()
            elif c == curses.KEY_LEFT:
                self.leave_dir()
                self.draw_ui()
            elif c == curses.KEY_RIGHT:
                self.enter_dir()
                self.draw_ui()
            elif c == curses.KEY_RESIZE:
                self.draw_ui()


def show_dir(dir_browser):
    for i in range(0, dir_browser.max_entries_on_level() - 1):
        print(dir_browser.get_friendly_name(i))


def test_dir():
    dir_browser = DirBrowse()
    print(dir_browser.path)
    show_dir(dir_browser)

    dir_browser.enter(1)
    print(dir_browser.path)
    show_dir(dir_browser)

    dir_browser.enter(4)
    print(dir_browser.path)
    show_dir(dir_browser)

    dir_browser.leave()
    print(dir_browser.path)
    show_dir(dir_browser)


def run_main():
    global returnString
    argv = sys.argv[1:]
    if len(argv) == 1:
        if argv[0] == 'test':
            test_dir()
            return
        if argv[0] == '--help':
            print("Usage:")
            print("--zonewithroom {room}")
            return
    with MainGui() as gui:
        inroom = None
        if len(argv) >= 1:
            index = 0
            if argv[0] == '--zonewithroom':
                gui.set_room(argv[1])
        returnString = gui.run_main_loop()


if __name__ == "__main__":
    run_main()

if returnString is not None:
    sys.stdout.write(returnString.decode('utf-8'))
    sys.stdout.write('\n')

