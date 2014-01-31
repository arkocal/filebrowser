#Imports for GUI
import gtk
import pango

#Imports for file operations
import os
from os.path import isdir, isfile, join
import shutil

KEYCODES = {65361: "left", 65362: "up", 65363: "right", 65364: "down",
            65535: "Del", 99: "C", 118: "V", 65293: "Enter",
            104: "H", 114: "R", 109: "M", 120: "X"}

ARROWKEYS = ["left", "up", "right", "down"]

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))

DARK = gtk.gdk.Color("#333")
LIGHT = gtk.gdk.Color("#D7D7D7")
BACKGROUND = gtk.gdk.Color("#EDEDED")
