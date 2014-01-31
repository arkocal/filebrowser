import os
from os.path import join, split, expanduser, isdir
from gi.repository import Gtk, Gdk, Pango
import cairo

import settings
import plugins


def isHidden(path):
    (_, fname) = os.path.split(path)
    return (fname[0]=="." or fname[-1]=="~")

def breakPath(path):
    #TODO test on windows
    (head, tail) = os.path.split(path)
    if len(head) == 1:
        return [tail]
    else:
        return breakPath(head) + [tail]

class DirRowHeightSetting(settings.Setting):

    def __init__(self):
        settings.Setting.__init__(self)
        self.setToDefault()

    def isValidValue(self, value):
        try:
            return (0 < value < 60000) and (type(value) is int)
        except:
            return False
            
    def setToDefault(self):
        self.set(60)

class StartPathSetting(settings.DirPathSetting):

    def __init__(self):
        settings.DirPathSetting.__init__(self)
        self.setToDefault()
        
    def setToDefault(self):
        self.value = expanduser("~")

"""class DirRowNormalColorSetting(settings.GdkColorSetting):
    
    def __init__(self):
        settings.GdkColorSetting.__init__(self, "#d7dad7")

class DirNowActiveColorSetting(settings.GdkColorSetting):

    def __init__(self):
        settings.GdkColorSetting.__init__(self, "#d0d0d0")"""

class DirRow(Gtk.ListBoxRow):

    def __init__(self, path, plugin, depth):
        Gtk.ListBoxRow.__init__(self)
        self.isSelected = False
        self.isToggledOn = False
        self.isPopulated = False
        self.children = []
        self.plugin = plugin
        self.path = path
        self.depth = depth
        (_, self.display) = os.path.split(path)
        self.display = self.depth*"  " + self.display
        if "dir-row-height" not in self.plugin.settings.keys():
            self.plugin.manager.raiseSignal("set-new-setting",
                                          setting = DirRowHeightSetting(),
                                          name="dir-row-height")
        height = self.plugin.settings["dir-row-height"].value
        self.set_size_request(-1, height)
        normalColor = Gdk.Color.parse("#d7dad7")[1]
        activeColor = Gdk.Color.parse("#d0d0d0")[1]
        self.modify_bg(Gtk.StateType.NORMAL, normalColor)
        self.modify_bg(Gtk.StateType.ACTIVE, activeColor)
        self.modify_bg(Gtk.StateType.SELECTED, activeColor)
        self.label = Gtk.Label(self.display)
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.label.set_alignment(0, 0.5)
        #This somehow makes ellipsize work
        self.label.set_max_width_chars(1)
        self.connect("key-press-event", self.plugin.onKeyEvent)
        self.add(self.label)
        self.show_all()

    def deselect(self):
        normalColor = Gdk.Color.parse("#d7dad7")[1]
        activeColor = Gdk.Color.parse("#d0d0d0")[1]
        self.modify_bg(Gtk.StateType.NORMAL, normalColor)
        self.modify_bg(Gtk.StateType.ACTIVE, activeColor)
        self.modify_bg(Gtk.StateType.SELECTED, activeColor)
        self.set_state(Gtk.StateType.NORMAL)      

    def select(self):
        selectedColor = Gdk.Color.parse("#888a85")[1]
        self.modify_bg(Gtk.StateType.NORMAL, selectedColor)
        self.modify_bg(Gtk.StateType.ACTIVE, selectedColor)
        self.modify_bg(Gtk.StateType.SELECTED, selectedColor)

    def toggle(self):
        if self.isToggledOn:
            self.isToggledOn = False
            self.toggleOff()
        else:
            self.isToggledOn = True
            self.toggleOn()  
            
    def toggleOn(self):
        if not self.isPopulated:
            self.populate()
        index = self.get_index() + 1            
        for child in self.children:
            self.plugin.widget.insert(child, index)
            if child.isToggledOn:
                index = child.toggleOn()
            index += 1
        return index-1          

    def toggleOff(self):
        for child in self.children:
            self.plugin.widget.remove(child)
            child.toggleOff()
        #self.children = []
        
    def populate(self):
        showHidden = self.plugin.settings["show-hidden"].value
        paths = [join(self.path, path) for path in os.listdir(self.path)]
        paths.sort()
        dirs = filter(os.path.isdir, paths)
        if not showHidden:
            dirs = filter(lambda f: not isHidden(f) , dirs)
        for path in dirs:
            row = DirRow(path=os.path.join(self.path, path), 
                         plugin=self.plugin, depth=self.depth+1)
            self.children.append(row)
        self.isPopulated = True      
        
class DirTree(plugins.Plugin):

    def __init__(self, manager):
        plugins.Plugin.__init__(self, manager)
        self.pname = "dirTree"
        self.dependencies.append("settings")        
        self.addResponse("started", self.onStart)
        self.addResponse("change-dir", self.onChangeDir)
        self.respondAfter["started"].append("settings")
        
    def onStart(self, signal, *args, **kwargs):
        self.manager.raiseSignal("request-settings", widget=self)    
        self.widget = Gtk.ListBox()
        self.widget.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.widget.set_activate_on_single_click(False)
        self.widget.connect("button-press-event", self.onMouseEvent)
        self.selectedRow = None
        self.manager.raiseSignal("request-place-left-pane", widget=self.widget)
        if "start-path" not in self.settings.keys():
            self.manager.raiseSignal("set-new-setting", name="start-path",
                                     setting = StartPathSetting())
        startpath = self.settings["start-path"].value
        self.root = startpath
        row = DirRow(path=self.root, plugin=self, depth=0)
        self.widget.add(row)
        row.toggle()
        """if "show-hidden" not in self.settings.keys():
            self.manager.raiseSignal("set-new-setting", name="show-hidden",
                                     setting = settings.BooleanSetting())
        showHidden = self.settings["show-hidden"].value
        paths = [join(startpath, path) for path in os.listdir(startpath)]
        paths.sort()
        dirs = filter(os.path.isdir, paths)
        if not showHidden:
            dirs = filter(lambda f: not isHidden(f) , dirs)
        for path in dirs:
            row = DirRow(path=os.path.join(startpath, path), plugin=self,
                         depth=1)
            self.widget.add(row)"""
        self.widget.show_all()  
        
    def onMouseEvent(self, widget, event):
        row = self.widget.get_row_at_y(event.y)
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            self.select(row)
        elif event.type == Gdk.EventType.BUTTON_PRESS:
            row.toggle()
     
    def onKeyEvent(self, row, event): 
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == "Return":
            self.select(row)
        elif keyname == "space":
            row.toggle()

    def onChangeDir(self, signal, *args, **kwargs):
        newPath = kwargs["newPath"]
        if self.selectedRow is not None:
            if self.selectedRow.path == newPath: #nothing to do
                return
            self.selectedRow.deselect()
            self.selectedRow = None   
        root = breakPath(self.root)
        target = breakPath(newPath)
        if (len(target) < len(root) or target[:len(root)] != root 
                or newPath == self.root):
            return #target not in tree, nothing to do
        index = len(root)
        found = join(self.root, target[index])
        rows = self.widget.get_children()
        try:
            targetRow = list(filter(lambda row: row.path == found, rows))[0]
        except:
            return
        index += 1
        while index < len(target):
            found = join(found, target[index])
            if not targetRow.isToggledOn:
                targetRow.toggle()
            for child in targetRow.children:
                if child.path == found:
                    targetRow = child
                    break
            index += 1
        if targetRow.path == newPath:
            targetRow.select()
            self.selected = targetRow
            
    def select(self, row):
        if self.selectedRow is not None:
            self.selectedRow.deselect()
        self.selectedRow = row
        row.select()
        self.manager.raiseSignal("change-dir", newPath = row.path)
               
def createPlugin(manager):
    return DirTree(manager)
