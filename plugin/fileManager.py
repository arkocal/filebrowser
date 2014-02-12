import os
import platform

import plugins


class FileManager(plugins.Plugin):

    def __init__(self, manager):
        plugins.Plugin.__init__(self, manager)
        self.pname = "fileManager"
        self.add_response("started", self.on_start)
        self.add_response("file-activated", self.on_file_activated)

    def on_start(self, signal, *args, **kwargs):
        self.system = platform.system()

    def on_file_activated(self, signal, *args, **kwargs):
        files = kwargs["files"]
        systemOpen = {
            "Linux": "xdg-open", "Windows": "open", "Darwin": "start"}
        if "app" in kwargs.keys():
            app = kwargs["app"]
        else:
            app = systemOpen[self.system]
        for f in files:
            os.system('{} "{}"'.format(app, f))

    def on_file_rename(self, signal, *args, **kwargs):
        files = kwargs["files"]
        newName = kwargs["new_name"]

def create_plugin(manager):
    return FileManager(manager)
