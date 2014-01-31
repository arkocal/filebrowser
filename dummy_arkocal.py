import plugins

class dummyPlugin(plugins.Plugin):
    def __init__(self, manager):
        plugins.Plugin.__init__(self, manager)
        self.pname = "dummy_arkocal"
        self.addResponse("started", self.onStart)
        
    def onStart(self, signal, *args, **kwargs):
        pass

def createPlugin(manager):
    return dummyPlugin(manager)
