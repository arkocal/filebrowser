import plugins

class dummyPlugin(plugins.Plugin):
    def __init__(self, manager):
        plugins.Plugin.__init__(self, manager)
        self.pname = "dummy_arkocal"
        self.addResponse("started", self.onStart)
        self.addResponse("change-dir", self.onChangeDir)
        self.respondAfter["started"].append("dirTree")
    def onStart(self, signal, *args, **kwargs):
        self.manager.raiseSignal("change-dir", 
            newPath="/home/ali/Workspace/FileBrowser")

    def onChangeDir(self, signal, *args, **kwargs):
        pass

def createPlugin(manager):
    return dummyPlugin(manager)
