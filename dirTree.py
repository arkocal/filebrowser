import os
from os.path import join, split, expanduser, isdir
from gi.repository import Gtk, Gdk, Pango
import cairo

import settings
import plugins


def isHidden(path):
    """Returns whether file at the given path is hidden."""
    (_, fname) = os.path.split(path)
    return (fname[0]=="." or fname[-1]=="~")

def breakPath(path):
    """ Breaks path into an array. 
    Example: path= /home/anon/Documents returns:
    ["home", "anon", "Documents"].
    This is different from path.split("/") as it is cross platform"""    
    #TODO test on windows
    (head, tail) = os.path.split(path)
    if len(head) == 1:
        return [tail]
    else:
        return breakPath(head) + [tail]

class DirRowHeightSetting(settings.Setting):
    "Setting for height of DirRow's"""

    def __init__(self):
        "Creates DirRowHeightSetting object."""
        settings.Setting.__init__(self)
        self.setToDefault()

    def isValidValue(self, value):
        """Returns whether value is a valid height."""
        try:
            return (type(value) is int) and (0 < value < 60000) 
        except:
            return False
            
    def setToDefault(self):
        """Sets DirRow's height to the default value."""
        self.set(60)

class StartPathSetting(settings.DirPathSetting):
    """Setting for starting path. This is a normal DirPathSetting
    with default value of users home directory."""

    def __init__(self):
        """Creates a StartPathSetting object."""
        settings.DirPathSetting.__init__(self)
        self.setToDefault()
        
    def setToDefault(self):
        """Sets starting path to home directory of the user."""
        self.value = expanduser("~")

"""class DirRowNormalColorSetting(settings.GdkColorSetting):
    
    def __init__(self):
        settings.GdkColorSetting.__init__(self, "#d7dad7")

class DirNowActiveColorSetting(settings.GdkColorSetting):

    def __init__(self):
        settings.GdkColorSetting.__init__(self, "#d0d0d0")"""

class DirRow(Gtk.ListBoxRow):
    """ListBoxRow for showing directories and toggling children on and off"""

    def __init__(self, path, plugin, depth):
        """Creates DirRowObject
        Args
            path: Full path to directory DirRow shows.
            plugin: dirTree plugin DirRow belongs to. It is used for
            getting settings.
            depth: Relative indentation depth of directory"""
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
        if "show-hidden" not in self.plugin.settings.keys():
            self.plugin.manager.raiseSignal("set-new-setting",
                                            setting=settings.BooleanSetting(),
                                            name="show-hidden")
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
        """Deselects the row and reverts colors to normal."""
        normalColor = Gdk.Color.parse("#d7dad7")[1]
        activeColor = Gdk.Color.parse("#d0d0d0")[1]
        self.modify_bg(Gtk.StateType.NORMAL, normalColor)
        self.modify_bg(Gtk.StateType.ACTIVE, activeColor)
        self.modify_bg(Gtk.StateType.SELECTED, activeColor)
        self.set_state(Gtk.StateType.NORMAL)      

    def select(self):
        """Selects row and changes its color."""
        selectedColor = Gdk.Color.parse("#888a85")[1]
        self.modify_bg(Gtk.StateType.NORMAL, selectedColor)
        self.modify_bg(Gtk.StateType.ACTIVE, selectedColor)
        self.modify_bg(Gtk.StateType.SELECTED, selectedColor)

    def toggle(self):
        """Toggles row."""
        if self.isToggledOn:
            self.isToggledOn = False
            self.toggleOff()
        else:
            self.isToggledOn = True
            self.toggleOn()  
            
    def toggleOn(self):
        """Toggles on the row. This doesn't effect isToggledOn property,
        but only handles the gui changes. Children of the row will be
        added if not already."""
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
        """Toggles on the row. This doesn't effect isToggledOn property,
        but only handles the gui changes. Children of the row will be
        added if not already."""    
        for child in self.children:
            self.plugin.widget.remove(child)
            child.toggleOff()
        #self.children = []
        
    def populate(self):
        """Adds children to row. In order to update the row, use the
        repopulate function. """
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
    """dirTree provides a gui in the left pane to browser directories.
    One can toggle the subdirectories of a directory by space key or 
    a single click. Enter key or double click selects the directory 
    and raises "change-dir" signal."""

    def __init__(self, manager):
        """Creates a DirTree object."""
        plugins.Plugin.__init__(self, manager)
        self.pname = "dirTree"
        self.dependencies.append("settings")     
        self.dependencies.append("guiManager")   
        self.addResponse("started", self.onStart)
        self.addResponse("change-dir", self.onChangeDir)
        self.respondAfter["started"].append("settings")
        self.respondAfter["started"].append("guiManager")
        
    def onStart(self, signal, *args, **kwargs):
        """Creates the tree with start-path setting as root."""
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
        if "show-hidden " not in self.settings.keys():
            self.manager.raiseSignal("set-new-setting", name="show-hidden",
                                     setting = settings.BooleanSetting())
        startpath = self.settings["start-path"].value
        self.root = startpath
        row = DirRow(path=self.root, plugin=self, depth=0)
        self.widget.add(row)
        row.toggle()
        self.widget.show_all()  
        self.manager.raiseSignal("change-dir", newPath = startpath)
        
    def onMouseEvent(self, widget, event):
        """Responds to button press events.
        Single click: toggle directory
        Double click: select directory"""
        row = self.widget.get_row_at_y(event.y)
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            self.select(row)
        elif event.type == Gdk.EventType.BUTTON_PRESS:
            row.toggle()
     
    def onKeyEvent(self, row, event):
        """Responds to key press events.
        space: toggle directory.
        return: select directory.
        """
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == "Return":
            self.select(row)
        elif keyname == "space":
            row.toggle()

    def onChangeDir(self, signal, *args, **kwargs):
        """Selects kwargs[“newPath”] if it is in dirTree."""
        newPath = kwargs["newPath"]
        rows = self.widget.get_children()        
        if self.selectedRow is not None:
            if self.selectedRow.path == newPath: #nothing to do
                return            
            self.selectedRow.deselect()
            self.selectedRow = None   
        root = breakPath(self.root)
        target = breakPath(newPath)
        if (len(target) < len(root) or target[:len(root)] != root ):
            return #target not in tree, nothing to do
        if newPath == self.root:
            self.selectedRow = rows[0]
            self.selectedRow.select()
            return
        index = len(root)
        found = join(self.root, target[index])
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
            self.selectedRow = targetRow
            
    def select(self, row):
        """Selects row and deselects the old one."""
        if self.selectedRow is not None:
            self.selectedRow.deselect()
        self.selectedRow = row
        row.select()
        self.manager.raiseSignal("change-dir", newPath = row.path)
               
def createPlugin(manager):
    return DirTree(manager)
