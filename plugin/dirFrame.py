import platform
import os
from os.path import join, isdir
import hashlib
import urllib
import re
from mimetypes import guess_type
import time

from gi.repository import Gtk, Gdk, GObject, Pango, GdkPixbuf
from gi.repository.GdkPixbuf import Pixbuf

import plugin.settings as settings
import plugins


def gtk_update():
    while Gtk.events_pending():
        Gtk.main_iteration()


def chunks(l, n):
    """ Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def isHidden(path):
    """Returns whether file at the given path is hidden."""
    (_, fname) = os.path.split(path)
    return (fname[0] == "." or fname[-1] == "~")


def pathToThumbnailPath(path, size):
    """Returns path to thumbnail of file at path (uses Gnome thumbnails)"""
    # PORT other platforms than gnome
    encodedUrl = ('file://' + path).encode()
    hashedUrl = hashlib.md5(encodedUrl).hexdigest()
    homeDir = (os.path.expanduser("~"))
    if size <= 128:
        sizeDir = "normal"
    else:
        sizeDir = "large"
    thumbnailsDir = "{home}/.cache/thumbnails/{size}/".format(home=homeDir,
                                                              size=sizeDir)
    return (thumbnailsDir + hashedUrl + ".png")


def loadThumbnailers():
    """Load thumbnailers
    thumbnailer files should be saved in thumbnailersDir and must be written
    in Gnome's thumbnailer entry format"""
    thumbnailers = {}
    # PORT make setting
    thumbnailersDir = "/usr/share/thumbnailers/"
    if isdir(thumbnailersDir):
        for filename in os.listdir(thumbnailersDir):
            command = ""
            tFile = open(join(thumbnailersDir, filename), "r").readlines()
            for line in tFile:
                if line[:5] == "Exec=":
                    command = line[5:]
                if line[:9] == "MimeType=":
                    for mime in line[9:].split(";"):
                        thumbnailers[mime] = command
    return thumbnailers


def getThumbnail(path, size):
    """Gets thumbnail for file at path. The function will try to create
    one if it is not found. Returns None if this fails."""
    defaultIcon = Gtk.IconTheme.get_default().load_icon("gtk-file", size, 0)
    thumbnailPath = pathToThumbnailPath(path, size)
    thumbnailers = loadThumbnailers()
    pixbuf = None
    try:
        return Pixbuf.new_from_file_at_size(thumbnailPath, size, size)
    except:
        pass
    if size > 128:
        tsize = 256
    else:
        tsize = 128
    try:
        pixbuf = Pixbuf.new_from_file_at_size(path, tsize, tsize)
    except:
        pass
    if pixbuf is None and guess_type(path)[0] in thumbnailers.keys():
        o = '"{}"'.format(thumbnailPath)
        u = '"file://{}"'.format(path)
        i = '"{}"'.format(path)
        s = str(tsize)
        command = thumbnailers[guess_type(path)[0]]
        for (pat, sub) in [("%o", o), ("%i", i), ("%u", u), ("%s", s)]:
            command = re.sub(pat, sub, command)
        os.system(command)
        try:
            pixbuf = Pixbuf.new_from_file_at_size(thumbnailPath, tsize, tsize)
        except:
            return defaultIcon
    if pixbuf is None:
        return defaultIcon
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
    # TEST test on other platforms than Linux
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

    def _is_valid_value(self, value):
        """Returns whether value is a valid size."""
        try:
            return (type(value) is int) and (0 < value < 60000)
        except:
            return False

    def setToDefault(self):
        """Sets thumbnail size to the default value."""
        self.set(156)


class FileWidget(Gtk.Box):

    """Widget for showing files. Shows a thumbnail and file name.
    This also raises file-select and file-activate signals."""

    def __init__(self, path, size, margin, showPixbuf):
        """Creates a FileWidget by loading/creating the thumbnail"""
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.pluginManager = None
        self.path = path
        (_, self.fname) = os.path.split(path)
        self.label = Gtk.Label(self.fname)
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.label.set_margin_left(margin)
        self.label.set_margin_right(margin)
        if showPixbuf:
            self.label.set_lines(3)
            self.label.set_single_line_mode(False)
            self.label.set_line_wrap(True)
            self.label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            self.label.set_justify(Gtk.Justification.CENTER)
            thumbnail = getThumbnail(self.path, size)
            self.image = Gtk.Image()
            if thumbnail is not None:
                self.image.set_from_pixbuf(thumbnail)
                height = thumbnail.get_height()
            self.pack_start(self.image, False, False, 5 + (size - height) / 2)
        else:
            self.label.set_alignment(0, 0.5)
        if showPixbuf:
            self.pack_start(self.label, False, False, 5)
        else:
            self.pack_start(self.label, False, False, 5)


class FlexibleGrid(Gtk.Grid, Gtk.EventBox):

    """A subclass of Gtk.Grid that orders its children in a grid
    with a given column width. The number of columns is adjusted
    automatically."""

    def __init__(self, column_width=100):
        """ Creates a FlexibleGrid with given column_with."""
        Gtk.EventBox.__init__(self)
        Gtk.Grid.__init__(self)
        self.connect("draw", self.draw)
        self.connect("key-press-event", self.on_key_press_event)
        self.column_width = column_width
        # Number of columns to show
        self.columns = 1
        self.set_column_homogeneous(True)
        # Used to reorder children in the right order
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
        columns = int(width / (self.column_width + self.get_column_spacing()))
        if columns != self.columns:
        # Reorder if number of columns has changed.
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
        self.show_all()  # This is needed because the children are
                        # just added.

    def on_button_press_event(self, eventbox, event):
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
                self.selected = self.ordered_children[smaller:greater + 1]
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
                widget.set_can_focus(True)
                widget.grab_focus()
        elif widget not in self.selected:
            self.selected.append(widget)
            widget.set_can_focus(True)
            widget.grab_focus()
        self.update_selection(selected_old)
        if selected_old != self.selected:
            self.plugin.deselectAllBut(self)

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
               "Left": -1, "Right": 1}
        selected_old = self.selected[:]
        if ctrl:
            pass  # TODO implement
        elif shift and self.cursor_at is not None:
            if (0 <= self.secondary_cursor_at + dif[keyname]
                    < len(self.ordered_children)):
                self.secondary_cursor_at += dif[keyname]
                cursors = [self.secondary_cursor_at, self.cursor_at]
                cursors.sort()
                smaller = cursors[0]
                greater = cursors[1]
                self.selected = self.ordered_children[smaller:greater + 1]
                self.ordered_children[
                    self.secondary_cursor_at].set_can_focus(True)
                self.ordered_children[self.secondary_cursor_at].grab_focus()
                self.update_selection(selected_old)
        elif self.cursor_at is not None:
            if self.secondary_cursor_at is not None:
                self.cursor_at = self.secondary_cursor_at
            if 0 <= self.cursor_at + dif[keyname] < len(self.ordered_children):
                self.cursor_at += dif[keyname]
                self.secondary_cursor_at = self.cursor_at
                self.selected = [self.ordered_children[self.cursor_at]]
                self.ordered_children[self.cursor_at].set_can_focus(True)
                self.ordered_children[self.cursor_at].grab_focus()
                self.update_selection(selected_old)
            elif self.cursor_at + dif[keyname] >= len(self.ordered_children):
                self.plugin.moveSelectionToNextGrid(self)
                return True
            elif self.cursor_at + dif[keyname] < 0:
                self.plugin.moveSelectionToPrevGrid(self)
                return True
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

    def deselect_all(self):
        old = self.selected[:]
        self.selected = []
        self.cursor_at = None
        self.secondary_cursor_at = None
        self.update_selection(old)
        self.show_all()


class DirGrid(FlexibleGrid):

    def __init__(self, plugin, columnWidth=100, showPixbuf=True):
        FlexibleGrid.__init__(self, columnWidth)       
        self.plugin = plugin
        self.settings = plugin.settings
        self.manager = plugin.manager
        self.path = None
        self.showPixbuf = showPixbuf
        self.set_can_focus(True)
        self.modify_bg(0, Gdk.Color.parse("#fafafa")[1])

    def on_button_press_event(self, widget, event):
        oldSelection = self.selected[:]
        if event.type == Gdk.EventType.BUTTON_PRESS:
            FlexibleGrid.on_button_press_event(self, widget, event)
            if self.selected[:] != oldSelection:
                self.manager.raise_signal("file-selected",
                                          files=[f.path for f in self.selected])
        elif event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            self.manager.raise_signal("file-activated",
                                      files=[f.path for f in self.selected])
        return True

    def change_dir(self, new_path):
        self.selected = []
        self.path = new_path
        showHidden = self.settings["show-hidden"].value
        thumbnail_size = self.settings["thumbnail-size"].value
        for child in self.get_children():
            self.remove(child.get_child())
        toadd = []
        toShow = os.listdir(new_path)
        if not showHidden:
            toShow = filter(lambda f: not isHidden(f), toShow)
        fullPaths = [os.path.join(new_path, f) for f in toShow]
        files = list(filter(os.path.isfile, fullPaths))
        files.sort()
        for chunk in chunks(files, 10):
            for f in chunk:
                if self.path != new_path:
                # This means directory has been changed while loading this one
                # and operation should be cancelled.
                    return
                w = FileWidget(f, thumbnail_size, 10, self.showPixbuf)
                self.add(w)
                self.show_all()
                gtk_update()

    def on_key_press_event(self, widget, event):
        oldSelection = self.selected[:]
        FlexibleGrid.on_key_press_event(self, widget, event)
        if self.selected[:] != oldSelection:
            self.manager.raise_signal("file-selected",
                                      files=[f.path for f in self.selected])
        if Gdk.keyval_name(event.keyval) == "Return":
            self.manager.raise_signal("file-activated",
                                      files=[f.path for f in self.selected])
        elif Gdk.keyval_name(event.keyval) == "BackSpace":
            self.manager.raise_signal("load-prev-dir")
        elif Gdk.keyval_name(event.keyval) == "F2":
            self.rename_files()
        return True

    def rename_files(self):
        if self.selected:
            if len(self.selected) > 1:
                entryText = ""
                title = "Renaming multiple files"
            else:
                entryText = os.path.split(self.selected[0].path)[1]        
                title = """Renaming file "{}" """.format(entryText)
            newName = self.manager.raise_signal("request-create-entry-dialog",
                title=title,
                text="New name:",
                entryText=entryText)["guiManager"]
            if newName is not None:
                self.manager.raise_signal("file-rename", newName=newName,
                                         files=[f.path for f in self.selected])
            if len(self.selected) == 1:
                self.selected[0].path = newName
                _, fname = os.path.split(newName)
                self.selected[0].label.set_text(fname)

class DirFrame(plugins.Plugin):

    """dirFrame shows the content of a directory in the center area.
    It is also responsible for creating signals for opening/
    previewing a file."""

    def __init__(self, manager):
        """Create a dirFrame object"""
        plugins.Plugin.__init__(self, manager)
        self.pname = "dirFrame"
        self.dependencies.append("dirTree")
        self.dependencies.append("guiManager")
        self.dependencies.append("settings")
        self.add_response("started", self.onStart)
        self.add_response("change-dir", self.onChangeDir)
        self.add_response("zoom", self.on_zoom)
        self.respondBefore["started"].append("dirTree")
        self.respondAfter["started"].append("guiManager")
        self.respondAfter["started"].append("settings")

    def onStart(self, signal, *args, **kwargs):
        """Create the frame unpopulated."""
        self.settings = self.manager.raise_signal(
            "request-settings")["settings"]
        if "thumbnail-size" not in self.settings.keys():
            self.manager.raise_signal("set-new-setting", name="thumbnail-size",
                                      setting=ThumbnailSizeSetting())
        self.thumbnailSize = self.settings["thumbnail-size"].value
        self.spacing = 30
        self.path = None
        self.zooming = False
        self.subdirWidgets = []        
        never = Gtk.PolicyType.NEVER
        self.scroll = Gtk.ScrolledWindow(hscrollbar_policy=never)
        self.holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.holder.modify_bg(0, Gdk.Color.parse("#fafafa")[1])
        self.titleBox = Gtk.Box()
        self.titleBox.modify_bg(0, Gdk.Color.parse("#f3f3f3")[1])
        self.mainDirTitle = Gtk.Label()
        self.mainDirTitle.set_margin_left(self.spacing)
        self.mainDirTitle.set_margin_top(20)
        self.mainDirTitle.set_margin_bottom(10)
        self.mainDirTitle.set_alignment(0, 1)
        separator = Gtk.HSeparator()
        self.grid = DirGrid(self, self.thumbnailSize + self.spacing)
        self.grid.set_column_spacing(self.spacing)
        self.grid.set_can_focus(True)
        self.titleBox.pack_start(self.mainDirTitle, False, False, 0)
        self.holder.add(self.titleBox)
        self.holder.add(separator)
        self.holder.add(self.grid)
        self.scroll.add(self.holder)
        self.scroll.connect("scroll-child", test)
        self.manager.raise_signal("request-place-center", widget=self.scroll)
        self.grid.show()

    def onChangeDir(self, signal, *args, **kwargs):
        showHidden = self.settings["show-hidden"].value
        newPath = kwargs["newPath"]
        self.path = newPath
        try:
            title = newPath.split("/")[-1]
        except:
            title = "Root directory"
        self.mainDirTitle.set_markup("<big>{}</big>".format(title))
        self.cursor_at = None
        self.secondary_cursor_at = None
        self.selected = []
        for subdirWidget in self.subdirWidgets:
            self.holder.remove(subdirWidget)
        try:
            self.titleBox.remove(self.spinner)
        except AttributeError:
            pass
        self.spinner = Gtk.Spinner(active=True)
        self.titleBox.pack_end(self.spinner, False, False, 20)
        self.titleBox.show_all()
        gtk_update()
        self.grid.change_dir(newPath)
        if self.path != newPath:
        # This means directory has been changed while loading this one
        # and operation should be cancelled.
            return
        self.grids = [self.grid]
        self.subdirWidgets = []
        toShow = os.listdir(newPath)
        if not showHidden:
            toShow = filter(lambda f: not isHidden(f), toShow)
        fullPaths = [os.path.join(newPath, f) for f in toShow]
        subdirs = list(filter(os.path.isdir, fullPaths))
        subdirs.sort()
        for subdir in subdirs:
            self.addSubdirTitle(subdir)
            self.addSubdirContent(subdir)
        self.holder.show_all()
        self.titleBox.remove(self.spinner)

    def on_zoom(self, signal, *args, **kwargs):
        if self.zooming: #zoom events shouldn't overlap
            return
        self.zooming = True
        direction = kwargs["direction"]
        if direction == "up":
            size = self.settings["thumbnail-size"].value * 7/6
        else:
            size = self.settings["thumbnail-size"].value * 6/7
        if 80 < size < 500:
            print ("Valid")
            self.manager.raise_signal("set-setting", setting="thumbnail-size",
                                      newValue = int(size))
            self.grid.column_width = int(size)
            self.grid.columns = int(self.grid.get_allocated_width() / (self.grid.column_width + self.grid.get_column_spacing()) )
            print(self.grid.columns, " columns of width ", self.grid.column_width)
            self.grid.change_dir(self.grid.path)
        self.zooming = False
            
    def addSubdirTitle(self, subdir):
        label = Gtk.Label()
        (_, subdir) = os.path.split(subdir)
        label.set_markup("<big>{}</big>".format(subdir))
        label.set_margin_left(self.spacing)
        label.set_alignment(0, 1)
        separator = Gtk.HSeparator()
#        self.subdirWidgets.append(label)
#        self.subdirWidgets.append(separator)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add(label)
        box.add(separator)
        box.modify_bg(0, Gdk.Color.parse("#f3f3f3")[1])        
        self.subdirWidgets.append(box)        
        self.holder.add(box)
        self.holder.show_all()
        gtk_update()

    def addSubdirContent(self, subdir):
        # TODO make settings
        grid = DirGrid(self, 300, False)
        grid.change_dir(subdir)
        grid.set_column_spacing(self.spacing * 2)
        #grid.set_border_width(self.spacing)
        grid.set_margin_top(-self.spacing / 2)
        grid.set_can_focus(True)
        self.holder.add(grid)
        self.grids.append(grid)
        self.subdirWidgets.append(grid)

    def moveSelectionToNextGrid(self, grid):
        index = self.grids.index(grid)
        if index < len(self.grids) - 1:
            nextGrid = self.grids[index + 1]
            nextGrid.grab_focus()
            grid.deselect_all()
            nextGrid.selected = [nextGrid.ordered_children[0]]
            nextGrid.update_selection([])
            nextGrid.cursor_at = 0

    def moveSelectionToPrevGrid(self, grid):
        index = self.grids.index(grid)
        if index > 0:
            nextGrid = self.grids[index - 1]
            nextGrid.grab_focus()
            grid.deselect_all()
            while not nextGrid.ordered_children:
                index -= 1
                if index == 0:
                    return
                nextGrid = self.grids[index]
                nextGrid.grab_focus()
                grid.deselect_all()            
            nextGrid.selected = [nextGrid.ordered_children[-1]]
            nextGrid.update_selection([])
            nextGrid.cursor_at = len(nextGrid.ordered_children) - 1

    def deselectAllBut(self, activeGrid):
        for grid in self.grids:
            if grid != activeGrid:
                grid.deselect_all()


def create_plugin(manager):
    return DirFrame(manager)
    
def test(e=None, b=None):
    print("Test ", e, b)
