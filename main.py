import optparse
import sys
from gi.repository import Gtk, Gio
import os

import plugins

class FileBrowserOptionParser(optparse.OptionParser):

    def __init__(self):
        optparse.OptionParser.__init__(self)
        

class FileBrowserApplication(Gtk.Application):

    def __init__(self):
        Gtk.Application.__init__(self)
        self.set_flags(Gio.ApplicationFlags.HANDLES_OPEN)
        self.pluginManager = plugins.PluginManager()
        self.connect("open", self.on_open)
        self.connect("activate", self.on_activate)

    def on_open(self, app, files, *hint):
        self.on_activate(app)

    def on_activate(self, app):       
        window = self.pluginManager.raise_signal(
            "request-window")["guiManager"]
        parser = FileBrowserOptionParser()
        (options, args) = parser.parse_args()
        for arg in args:
            if os.path.isdir(arg):
                self.pluginManager.raise_signal("change-dir", newPath=arg)
                break
        self.add_window(window)

if __name__ == "__main__":
    application = FileBrowserApplication()
    application.run(sys.argv)
