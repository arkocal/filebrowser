import os
import platform

import plugins

class FileManager(plugins.Plugin):
    
    def __init__(self, manager):
        plugins.Plugin.__init__(self, manager)
        self.pname = "fileManager"
        self.addResponse("started", self.onStart)
        self.addResponse("file-activated", self.onFileActivated)
    
    def onStart(self, signal, *args, **kwargs):
        self.system = platform.system()    
    
    def onFileActivated(self, signal, *args, **kwargs):
        files = kwargs["files"]
        systemOpen = {"Linux":"xdg-open", "Windows":"open", "Darwin":"start"}
        if "app"  in kwargs.keys():
            app = kwargs["app"]
        else:
            app = systemOpen[self.system]
        for f in files:
            os.system("{} '{}'".format(app, f))
    
    
def createPlugin(manager):
    return FileManager(manager)
