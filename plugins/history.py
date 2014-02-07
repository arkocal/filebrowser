from gi.repository import Gtk

import plugins

class History(plugins.Plugin):
    def __init__(self, manager):
        plugins.Plugin.__init__(self, manager)
        self.pname = "history"
        self.dependencies.append("settings")
        self.dependencies.append("dirTree")        
        self.dependencies.append("guiManager")
        self.addResponse("started", self.onStart)
        self.addResponse("change-dir", self.onChangeDir)
        self.respondBefore["started"].append("dirTree")
        
    def onStart(self, signal, *args, **kwargs):
        self.pathsLog = []
        self.pathsLogIndex = -1
        prev = Gtk.Image()
        prev.set_from_icon_name("go-previous-symbolic", Gtk.IconSize.MENU)
        next = Gtk.Image()
        next.set_from_icon_name("go-next-symbolic", Gtk.IconSize.MENU)
        self.prevButton = Gtk.Button(None, image=prev)
        self.nextButton = Gtk.Button(None, image=next)
        self.prevButton.set_state(Gtk.StateType.INSENSITIVE)
        self.nextButton.set_state(Gtk.StateType.INSENSITIVE)
        self.prevButton.connect("clicked", self.prev)
        self.nextButton.connect("clicked", self.next)
        self.widget = Gtk.Box()
        Gtk.StyleContext.add_class(self.widget.get_style_context(), "linked")
        self.widget.add(self.prevButton)
        self.widget.add(self.nextButton)
        self.widget.show()
        self.manager.raiseSignal("request-place-header", widget = self.widget,
                                 side="left")

    def onChangeDir(self, signal, *args, **kwargs):
        if "raisedBy" in kwargs:
            raisedBy = kwargs["raisedBy"]
            if raisedBy == self:
                return
        newPath = kwargs["newPath"]
        self.pathsLogIndex += 1
        if len(self.pathsLog) > self.pathsLogIndex:
            self.pathsLog[self.pathsLogIndex] = newPath
            self.pathsLog = self.pathsLog[:self.pathsLogIndex+1]
            print(self.pathsLogIndex, self.pathsLog)
        else:
            self.pathsLog.append(newPath)
        if len(self.pathsLog) -1 > self.pathsLogIndex:
            self.nextButton.set_state(Gtk.StateType.NORMAL)
        else:
            self.nextButton.set_state(Gtk.StateType.INSENSITIVE)
        if self.pathsLogIndex > 0:
            self.prevButton.set_state(Gtk.StateType.NORMAL)

    def prev(self, _):
        self.pathsLogIndex -= 1
        newPath = self.pathsLog[self.pathsLogIndex]
        self.manager.raiseSignal("change-dir", newPath=newPath, raisedBy=self)
        if self.pathsLogIndex == 0:
            self.prevButton.set_state(Gtk.StateType.INSENSITIVE)
        self.nextButton.set_state(Gtk.StateType.NORMAL)
            
    def next(self, _):
        self.pathsLogIndex += 1
        print(self.pathsLog)
        newPath = self.pathsLog[self.pathsLogIndex]
        self.manager.raiseSignal("change-dir", newPath=newPath, raisedBy=self)
        if self.pathsLogIndex >= len(self.pathsLog) - 1:
            self.nextButton.set_state(Gtk.StateType.INSENSITIVE)
        self.prevButton.set_state(Gtk.StateType.NORMAL)
        

def createPlugin(manager):
    return History(manager)
