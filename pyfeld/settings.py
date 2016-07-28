from __future__ import unicode_literals

import os

class Settings:
    @staticmethod
    def home_directory():
        home = os.path.expanduser("~")
        p = home+"/.pyfeld"
        if not os.path.isdir(p):
            os.mkdir(p)
        return p

