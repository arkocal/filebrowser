import os
from os.path import join

from gi.repository import Gtk
from gi.repository.GdkPixbuf import Pixbuf

import plugins

def isHidden(path):
    """Returns whether file at the given path is hidden."""
    (_, fname) = os.path.split(path)
    return (fname[0]=="." or fname[-1]=="~")

class dirFrame(plugins.Plugin):
    """dirFrame shows the content of a directory in the center area.
    It is also responsible for creating signals for opening/
    previewing a file."""
    
    def __init__(self, manager):
        """Create a dirFrame object"""
        plugins.Plugin.__init__(self, manager)
        self.dependencies.append("dirTree")
        self.dependencies.append("guiManager")
        self.dependencies.append("settings")
        self.addResponse("started", self.onStart)
        self.addResponse("change-dir", self.onChangeDir)
        self.respondBefore["started"].append("dirTree")
        self.respondAfter["started"].append("guiManager")
        self.respondAfter["started"].append("settings")
        
    def onStart(self, signal, *args, **kwargs):
        """Create the frame unpopulated."""
        self.path = None
        self.liststore = Gtk.ListStore(Pixbuf, str)
        never = Gtk.PolicyType.NEVER
        self.scroll = Gtk.ScrolledWindow(hscrollbar_policy=never)
        self.widget = Gtk.IconView(self.liststore)
        self.widget.set_pixbuf_column(0)
        self.widget.set_text_column(1)
        self.scroll.add(self.widget)
        self.scroll.show_all()
        self.manager.raiseSignal("request-settings", widget=self)
        self.manager.raiseSignal("request-place-center", widget=self.scroll)
        
    def onChangeDir(self, signal, *args, **kwargs):
        self.path = kwargs["newPath"]
        self.liststore = Gtk.ListStore(Pixbuf, str)
        showHidden = self.settings["show-hidden"].value
        paths = [join(self.path, path) for path in os.listdir(self.path)]
        paths.sort()
        files = filter(os.path.isfile, paths)
        if not showHidden:
            files = filter(lambda f: not isHidden(f) , files)
        for f in files:
            (_, fname) = os.path.split(f)
            self.liststore.append([None, fname])
        self.widget.set_model(self.liststore)
        
def createPlugin(manager):
    return dirFrame(manager)    
