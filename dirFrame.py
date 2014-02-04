import platform
import os
from os.path import join
import hashlib
import urllib

from gi.repository import Gtk, Gdk, GObject, Pango, GdkPixbuf
from gi.repository.GdkPixbuf import Pixbuf

import settings
import plugins

def chunks(l, n):
    """ Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i+n]

def isHidden(path):
    """Returns whether file at the given path is hidden."""
    (_, fname) = os.path.split(path)
    return (fname[0]=="." or fname[-1]=="~")

def pathToThumbnailPath(path, size):
    """Returns path to thumbnail of file at path (uses Gnome thumbnails)"""
    #PORT other platforms than gnome
    encodedUrl = ('file://' + path).encode()
    hashedUrl = hashlib.md5(encodedUrl).hexdigest()
    homeDir = (os.path.expanduser("~"))
    if size <= 128: sizeDir = "normal"
    else: sizeDir = "large"
    thumbnailsDir = "{home}/.cache/thumbnails/{size}/".format(home = homeDir,
                                                              size = sizeDir)
    return (thumbnailsDir + hashedUrl + ".png")

def getThumbnail(path, size):
    """Gets thumbnail for file at path. The function will try to create
    one if it is not found. Returns None if this fails."""
    thumbnailPath = pathToThumbnailPath(path, size)
    try: 
        return Pixbuf.new_from_file_at_size(thumbnailPath, size, size)
    except: 
        print("Thumbnail not found. Trying to create")
    if size>128:
        tsize = 256
    else:
        tsize = 128
    try:    
        pixbuf = Pixbuf.new_from_file_at_size(path, tsize, tsize)
    except:
        return Gtk.IconTheme.get_default().load_icon("gtk-file", size, 0)        
    pixbuf.savev(thumbnailPath, "png", [], [])
    width = pixbuf.get_width()
    height = pixbuf.get_height()
    if height > width:
        width = size * width / height
        height = size
    else:
        height = size * height / width
        width = size
    pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
    return pixbuf
    

def openFile(path):
    """Opens file at given path."""
    #TEST test on other platforms than Linux
    system = platform.system()
    if system == "Linux":
        os.system("""xdg-open "%s" """ % path)
    elif system == "Windows":
        os.system("""start "%s" """ % path)
    else:
        os.system("""open "%s" """ % path)

class ThumbnailSizeSetting(settings.Setting):
    "Setting for thumbnail sizes."""

    def __init__(self):
        "Creates ThumbnailSizeSetting object."""
        settings.Setting.__init__(self)
        self.setToDefault()

    def isValidValue(self, value):
        """Returns whether value is a valid size."""
        try:
            return (type(value) is int) and (0 < value < 60000) 
        except:
            return False
            
    def setToDefault(self):
        """Sets thumbnail size to the default value."""
        self.set(128)

class FileWidget(Gtk.Box):
    """Widget for showing files. Shows a thumbnail and file name.
    This also raises file-select and file-activate signals."""
    
    def __init__(self, path, size, margin):
        """Creates a FileWidget by loading/creating the thumbnail"""
        Gtk.Box.__init__(self, orientation = Gtk.Orientation.VERTICAL)
        self.pluginManager = None
        self.path = path
        (_, self.fname) = os.path.split(path)
        self.label = Gtk.Label(self.fname)
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.label.set_single_line_mode(False)
        self.label.set_line_wrap(True)
        #This somehow makes ellipsize work
        self.label.set_max_width_chars(1)      
        
        thumbnail = getThumbnail(self.path, size)
        self.image = Gtk.Image()
        self.label.set_margin_left(margin)
        self.label.set_margin_right(margin) 
        if thumbnail is not None:
            self.image.set_from_pixbuf(thumbnail)
        self.pack_start(self.image, True, True, 5)
        self.pack_start(self.label, False, False, 5)
    
class FlexibleGrid(Gtk.Grid, Gtk.EventBox):
    """A subclass of Gtk.Grid that orders its children in a grid
    with a given column width. The number of columns is adjusted
    automatically."""
    
    def __init__(self, column_width = 100):
        """ Creates a FlexibleGrid with given column_with."""
        Gtk.EventBox.__init__(self)        
        Gtk.Grid.__init__(self)
        self.connect("draw", self.draw)
        self.connect("key-press-event", self.on_key_press_event)
        self.column_width = column_width
        #Number of columns to show
        self.columns = 1
        self.set_column_homogeneous(True)
        #Used to reorder children in the right order
        self.ordered_children = []
        self.selected = []
        self.cursor_at = None
        self.secondary_cursor_at = None
 
    def add(self, child):
        """Add child wrapped in an EventBox."""
        items = len(self.ordered_children)
        column = items % self.columns
        row = items // self.columns
        ebox = Gtk.EventBox()
        ebox.add(child)
        ebox.connect("button-press-event", self.on_button_press_event)
        self.ordered_children.append(child)  
        Gtk.Grid.attach(self, ebox, column, row, 1, 1)

    def remove(self, child):
        """Removes child."""
        self.ordered_children.remove(child)
        eventBox = child.get_parent()
        Gtk.Grid.remove(self, eventBox)
        
    def draw(self, event, cr):
        """Orders children in rows and columns and calls
        Gtk.Grid.draw. This doesn't work right if there is a children
        with a width greater than self.column_width."""
        width = self.get_allocated_width()
        columns = int(width / self.column_width)
        if columns != self.columns:
        #Reorder if number of columns has changed.
            self.columns = columns
            for ebox in self.get_children():
                ebox.remove(ebox.get_child())
                Gtk.Grid.remove(self, ebox)
            row = 0
            column = 0
            for child in self.ordered_children:
                ebox = Gtk.EventBox()
                ebox.add(child)
                ebox.connect("button-press-event", self.on_button_press_event)
                self.attach(ebox, column, row, 1, 1)
                column += 1
                if column == columns:
                    column = 0
                    row += 1
            Gtk.Grid.draw(self, cr)
            self.show_all()
        self.show_all() #This is needed because the children are
                        #just added.
                        
    def on_button_press_event(self, eventbox, event):
        self.grab_focus()
        widget = eventbox.get_child()
        modifiers = Gtk.accelerator_get_default_mod_mask()
        ctrl = event.state & modifiers == Gdk.ModifierType.CONTROL_MASK
        shift = event.state & modifiers == Gdk.ModifierType.SHIFT_MASK
        selected_old = self.selected[:]
        self.secondary_cursor_at = self.cursor_at
        self.cursor_at = self.ordered_children.index(widget)
        if not ctrl:
            self.selected = []
        if shift:
            if self.secondary_cursor_at is not None:
                cursors = [self.secondary_cursor_at, self.cursor_at]
                cursors.sort()
                smaller = cursors[0]
                greater = cursors[1]
                self.selected = self.ordered_children[smaller:greater+1]
                # When using shift, cursor should remain the same
                self.cursor_at, self.secondary_cursor_at = \
                    self.secondary_cursor_at, self.cursor_at
        else:
            self.secondary_cursor_at = self.cursor_at
        if ctrl:
            if widget in self.selected:
                self.selected.remove(widget)
            else:
                self.selected.append(widget)
        elif widget not in self.selected:
            self.selected.append(widget)
        self.update_selection(selected_old)
 
    def on_key_press_event(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname in ["Left", "Right", "Up", "Down"]:
            return self.move_selection_by_key(event)
            
    def move_selection_by_key(self, event):
        keyname = Gdk.keyval_name(event.keyval)
        modifiers = Gtk.accelerator_get_default_mod_mask()
        ctrl = event.state & modifiers == Gdk.ModifierType.CONTROL_MASK
        shift = event.state & modifiers == Gdk.ModifierType.SHIFT_MASK
        dif = {"Up": -self.columns, "Down": self.columns,
              "Left": -1, "Right":1}
        selected_old = self.selected[:]
        if ctrl:
            pass #TODO implement
        elif shift and self.cursor_at is not None:
            if (0 <= self.secondary_cursor_at + dif[keyname] 
                    < len(self.ordered_children)):
                self.secondary_cursor_at += dif[keyname]
                cursors = [self.secondary_cursor_at, self.cursor_at]
                cursors.sort()
                smaller = cursors[0]
                greater = cursors[1]
                self.selected = self.ordered_children[smaller:greater+1]
                self.update_selection(selected_old)
        elif self.cursor_at is not None:
            if self.secondary_cursor_at is not None:
                self.cursor_at = self.secondary_cursor_at
            if 0 <= self.cursor_at + dif[keyname] < len(self.ordered_children):    
                self.cursor_at += dif[keyname]
                self.secondary_cursor_at = self.cursor_at
                self.selected = [self.ordered_children[self.cursor_at]]
                self.update_selection(selected_old)
        if self.cursor_at is None:
            self.cursor_at = 0
            self.selected = [self.ordered_children[self.cursor_at]]
            self.update_selection([])
        return True    

    def update_selection(self, selected_old):
        to_select = [i for i in self.selected if i not in selected_old]
        to_deselect = [i for i in selected_old if i not in self.selected]
        for item in to_select:
            item.set_state(Gtk.StateType.SELECTED)
        for item in to_deselect:
            item.set_state(Gtk.StateType.NORMAL) 

class MainDirGrid(FlexibleGrid):

    def __init__(self, settings, manager, columnWidth=100):
        FlexibleGrid.__init__(self, columnWidth)
        self.settings = settings
        self.manager = manager
        
    def on_button_press_event(self, widget, event):
        oldSelection = self.selected[:]
        if event.type == Gdk.EventType.BUTTON_PRESS:
            FlexibleGrid.on_button_press_event(self, widget, event)
            if self.selected[:] != oldSelection:
                self.manager.raiseSignal("file-selected",
                                         files=[f.path for f in self.selected])
        elif event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            self.manager.raiseSignal("file-activated",
                                     files=[f.path for f in self.selected])
        return True
        
    def on_key_press_event(self, widget, event):
        oldSelection = self.selected[:]
        FlexibleGrid.on_key_press_event(self, widget, event)
        if self.selected[:] != oldSelection:
            self.manager.raiseSignal("file-selected", 
                                     files=[f.path for f in self.selected])
        if Gdk.keyval_name(event.keyval) == "Return":
            self.manager.raiseSignal("file-activated",
                                     files=[f.path for f in self.selected])
        return True
        
class DirFrame(plugins.Plugin):
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
       # self.addResponse("file-select", self.onFileSelect)
       # self.addResponse("file-activate", self.onFileActivate)
        self.addResponse("change-dir", self.onChangeDir)
        self.respondBefore["started"].append("dirTree")
        self.respondAfter["started"].append("guiManager")
        self.respondAfter["started"].append("settings")
        
    def onStart(self, signal, *args, **kwargs):
        """Create the frame unpopulated."""
        self.manager.raiseSignal("request-settings", widget=self)
        if "thumbnail-size" not in self.settings.keys():
            self.manager.raiseSignal("set-new-setting", name="thumbnail-size",
                                     setting = ThumbnailSizeSetting() )
        self.thumbnailSize = self.settings["thumbnail-size"].value
        self.spacing = 30
        self.path = None
        never = Gtk.PolicyType.NEVER
        self.scroll = Gtk.ScrolledWindow(hscrollbar_policy=never)
        self.holder = Gtk.Box(orientation = Gtk.Orientation.VERTICAL)
        self.mainDirTitle = Gtk.Label()
        self.mainDirTitle.set_margin_left(self.spacing)
        self.mainDirTitle.set_margin_top(20)
        self.mainDirTitle.set_margin_bottom(10)
        self.mainDirTitle.set_alignment(0, 1)
        separator = Gtk.HSeparator()
        self.grid = MainDirGrid(self.settings, self.manager,
                                self.thumbnailSize + self.spacing)
        self.grid.set_column_spacing(self.spacing)
        self.grid.set_can_focus(True)
        self.holder.pack_start(self.mainDirTitle, False, False, 0)
        self.holder.add(separator)        
        self.holder.add(self.grid)
        self.scroll.add(self.holder)
        self.manager.raiseSignal("request-place-center", widget=self.scroll)
        self.grid.show()

    def onChangeDir(self, signal, *args, **kwargs):
        newPath = kwargs["newPath"]
        try:
            title = newPath.split("/")[-1]
        except:
            title = "Root directory"
        self.mainDirTitle.set_markup("<big>{}</big>".format(title))
        toadd = []
        
        fullPaths = [os.path.join(newPath, f) for f in os.listdir(newPath)]
        files = list(filter(os.path.isfile, fullPaths))
        self.cursor_at = None
        self.secondary_cursor_at = None
        self.selected = []
        for child in self.grid.get_children():
            self.grid.remove(child.get_child())        
        # Loading thumbnails can take too long on  some directories
        # (like with lots of HD photos), so the process is divided
        # into chunks and after each chunk pending events are handled
        for chunk in chunks(files, 10):
            for f in chunk:
                w = FileWidget(f, self.thumbnailSize, 10)
                self.grid.add(w)
                while Gtk.events_pending():
                    Gtk.main_iteration()

def createPlugin(manager):
    return DirFrame(manager)    
