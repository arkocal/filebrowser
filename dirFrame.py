import platform
import os
from os.path import join
import hashlib
import urllib

from gi.repository import Gtk, Gdk, GObject, Pango
from gi.repository.GdkPixbuf import Pixbuf

import plugins

def chunks(l, n):
    """ Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i+n]

def isHidden(path):
    """Returns whether file at the given path is hidden."""
    (_, fname) = os.path.split(path)
    return (fname[0]=="." or fname[-1]=="~")

def pathToThumbnailPath(path):
    """Returns path to thumbnail of file at path (uses Gnome thumbnails)"""
    #PORT other platforms than gnome
    encodedUrl = ('file://' + path).encode()
    hashedUrl = hashlib.md5(encodedUrl).hexdigest()
    homeDir = (os.path.expanduser("~"))
    thumbnailsDir = "%s/.cache/thumbnails/normal/" %homeDir
    return (thumbnailsDir + hashedUrl + ".png")

def getThumbnail(path, size):
    """Gets thumbnail for file at path. The function will try to create
    one if it is not found. Returns None if this fails."""
    thumbnailPath = pathToThumbnailPath(path)
    try: 
        return Pixbuf.new_from_file_at_size(thumbnailPath, size, size)
    except: 
        print("Thumbnail not found. Trying to create")
    try: 
        pixbuf = Pixbuf.new_from_file_at_size(path, size, size)
        pixbuf.savev(thumbnailPath, "png", [], [])
        return pixbuf        
    except: 
        return Gtk.IconTheme.get_default().load_icon("gtk-file", size, 0)
    

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

class FileWidget(Gtk.Box):
    """Widget for showing files. Shows a thumbnail and file name.
    This also raises file-select and file-activate signals."""
    
    def __init__(self, path):
        """Creates a FileWidget."""
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
        
        thumbnail = getThumbnail(self.path, 75)
        self.image = Gtk.Image()
        self.label.set_margin_left(10)
        self.label.set_margin_right(10) 
        if thumbnail is not None:
            self.image.set_from_pixbuf(thumbnail)
        self.pack_start(self.image, False, False, 5)
        self.pack_start(self.label, False, False, 5)
    
class FlexibleGrid(Gtk.Grid):
    """A subclass of Gtk.Grid that orders its children in a grid
    with a given column width. The number of columns is adjusted
    automatically."""
    
    def __init__(self, column_width = 100):
        """ Creates a FlexibleGrid with given column_with."""
        Gtk.Grid.__init__(self)
        self.connect("draw", self.draw) 
        self.column_width = column_width
        #Number of columns to show
        self.columns = 1
        self.set_column_homogeneous(True)
        #Used to reorder children in the right order
        self.ordered_children = []
        self.selected = []
        self.cursor_at = None
 
    def add(self, child):
        """Add child wrapped in an EventBox."""
        items = len(self.ordered_children)
        column = items % self.columns
        row = items // self.columns
        ebox = Gtk.EventBox()
        ebox.add(child)
        ebox.connect("button-press-event", self.on_button_click)
        self.ordered_children.append(child)  
        Gtk.Grid.attach(self, ebox, column, row, 1, 1)

    def remove(self, child):
        """Remove child."""
        self.ordered_children.remove(child)
        eventBox = None
        for ebox in self.get_children():
            if ebox.get_child() == child:
                eventBox = ebox
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
            for i in range(len(self.ordered_children)):
                child = self.ordered_children[i]
                ebox = Gtk.EventBox()
                ebox.add(child)
                ebox.connect("button-press-event", self.on_button_click)
                self.attach(ebox, column, row, 1, 1)
                column += 1
                if column == columns:
                    column = 0
                    row += 1
            Gtk.Grid.draw(self, cr)
            self.show_all()
        self.show_all() #This is needed because the children are
                        #just added.

    def on_button_click(self, eventbox, event):
        widget = eventbox.get_child()
        modifiers = Gtk.accelerator_get_default_mod_mask()
        ctrl = event.state & modifiers == Gdk.ModifierType.CONTROL_MASK
        shift = event.state & modifiers == Gdk.ModifierType.SHIFT_MASK
        selected_old = self.selected[:]
        cursor_was_at = self.cursor_at
        self.cursor_at = self.ordered_children.index(widget)
        if not ctrl:
            self.selected = []
        if shift:
            if cursor_was_at is not None:
                if self.cursor_at > cursor_was_at:
                    smaller, greater =  cursor_was_at, self.cursor_at
                else:
                    smaller, greater = self.cursor_at, cursor_was_at
                self.selected = self.ordered_children[smaller:greater+1]
                self.cursor_at = cursor_was_at
        if ctrl:
            if widget in self.selected:
                self.selected.remove(widget)
            else:
                self.selected.append(widget)
        elif widget not in self.selected:
            self.selected.append(widget)
        to_select = [i for i in self.selected if i not in selected_old]
        to_deselect = [i for i in selected_old if i not in self.selected]
        for item in to_select:
            item.set_state(Gtk.StateType.SELECTED)
        for item in to_deselect:
            item.set_state(Gtk.StateType.NORMAL)

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
        self.addResponse("file-select", self.onFileSelect)
        self.addResponse("file-activate", self.onFileActivate)
        self.addResponse("change-dir", self.onChangeDir)
        self.respondBefore["started"].append("dirTree")
        self.respondAfter["started"].append("guiManager")
        self.respondAfter["started"].append("settings")
        
    def onStart(self, signal, *args, **kwargs):
        """Create the frame unpopulated."""
        self.path = None
        never = Gtk.PolicyType.NEVER
        self.scroll = Gtk.ScrolledWindow(hscrollbar_policy=never)
        self.grid = FlexibleGrid(180)
        self.scroll.add(self.grid)
        self.manager.raiseSignal("request-settings", widget=self)
        self.manager.raiseSignal("request-place-center", widget=self.scroll)
        self.grid.show()

    def onChangeDir(self, signal, *args, **kwargs):
        newPath = kwargs["newPath"]
        toadd = []
        fullPaths = [os.path.join(newPath, f) for f in os.listdir(newPath)]
        files = list(filter(os.path.isfile, fullPaths))
        for child in self.grid.get_children():
            self.grid.remove(child.get_child())        
        # Loading thumbnails can take too long on  some directories
        # (like with lots of HD photos), so the process is divided
        # into chunks and after each chunk pending events are handled
        for chunk in chunks(files, 10):
            for f in chunk:
                w = FileWidget(f)
                self.grid.add(w)
                while Gtk.events_pending():
                    Gtk.main_iteration()

    def onFileSelect(self, signal, *args, **kwargs):
        print(kwargs)

    def onFileActivate(self, signal, *args, **kwargs):
        path = kwargs["path"]
        openFile(path)

def createPlugin(manager):
    return dirFrame(manager)    
