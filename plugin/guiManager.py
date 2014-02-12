"""
guiManager

guiManager plug-in places widget created by other plug-ins on requests

Dependencies
guiManager doesn't have any dependencies.
"""

from threading import Thread

from gi.repository import Gtk, Gdk

import plugin.settings as settings
import plugins


class EntryDialog(Gtk.Dialog):

    def __init__(self, title, parent, text, entryText, guiManager):
        Gtk.Dialog.__init__(self, title, parent)
        self.guiManager = guiManager
        box = self.get_content_area()
        vbox0 = Gtk.Box()
        label = Gtk.Label(text)
        self.entry = Gtk.Entry()
        self.entry.set_text(entryText)
        vbox0.pack_start(label, False, False, 5)
        vbox0.pack_start(self.entry, True, True, 0)
        box.pack_start(vbox0, False, False, 5)
        vbox1 = Gtk.Box()
        cancelButton = Gtk.Button.new_from_stock(Gtk.STOCK_CANCEL)
        cancelButton.connect("clicked", self.cancel)
        okButton = Gtk.Button.new_from_stock(Gtk.STOCK_OK)
        okButton.connect("clicked", self.ok)
        vbox1.pack_end(okButton, False, False, 0)
        vbox1.pack_end(cancelButton, False, False, 5)
        box.pack_start(vbox1, False, False, 0)
        self.connect("key-press-event", self.on_key_press_event)
        self.set_size_request(400, -1)
        self.show_all()

    def cancel(self, button):
        self.destroy()
    
    def ok(self, button=None):
        self.guiManager.dialogInput = self.entry.get_text()
        self.destroy()
        
    def on_key_press_event(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == "Return" and self.entry.has_focus():
            self.ok()

class LeftPaneWidthSetting(settings.Setting):

    """Setting for left pane width."""

    def __init__(self):
        """Creates a LeftPaneWidthSetting object."""
        settings.Setting.__init__(self)
        self.setToDefault()

    def _is_valid_value(self, value):
        """Returns whether value is a valid width."""
        try:
            return (type(value) is int) and (0 < value < 60000)
        except:
            return False

    def setToDefault(self):
        """ Sets left pane width to default."""
        self.set(240)


class WindowGeoSetting(settings.Setting):

    """Setting for window size or position. Value is tuple (width, height)"""

    def __init__(self):
        """Creates a WindowSizeSetting object."""
        settings.Setting.__init__(self)
        self.setToDefault()

    def _is_valid_value(self, value):
        """Returns if value is a valid (width, height) tuple"""
        try:
            return ((0 <= value[0] < 60000) and
                    (0 <= value[1] < 60000))
        except:
            return False

    def setToDefault(self):
        """ Sets window size to default."""
        self.set((650, 480))


class guiManager(plugins.Plugin):

    """guiManager creates a Gtk.Main window with a left pane
       (Gtk.ScrolledWindow), center area (Gtk.Stack) and a Gtk.HeaderBar.
       On request, guiManager places Widgets created by other plug-ins
       in these areas.
       Signals:
       started: onStart
       request-place-left-pane: onLeftPanePlaceRequest
       request-place-header: onHeaderPlaceRequest
       request-place-center: onCenterPlaceRequest
       request-remove-left-pane: onLeftPaneRemoveRequest
       request-remove-center: onCenterRemoveRequest
       request-remove-header: onHeaderRemoveRequest
       request-scroll: onScrollRequest
       request-window: onRequestWindow
       request-create-entry-dialog: on_request_entry_dialog
       error: on_error
       """

    def __init__(self, manager):
        plugins.Plugin.__init__(self, manager)
        self.pname = "guiManager"
        self.dependencies.append("settings")
        self.add_response("started", self.onStart)
        self.add_response("request-place-left-pane",
                          self.onLeftPanePlaceRequest)
        self.add_response("request-place-center", self.onCenterPlaceRequest)
        self.add_response("request-place-header", self.onHeaderPlaceRequest)
        self.add_response("request-remove-left-pane",
                          self.onLeftPaneRemoveRequest)
        self.add_response("request-remove-center", self.onCenterRemoveRequest)
        self.add_response("request-remove-header",
                          self.onHeaderRemoveRequest)
        self.add_response("request-scroll", self.onScrollRequest)
        self.add_response("change-dir", self.onChangeDir)
        self.add_response("request-window", self.onRequestWindow)
        self.add_response("request-create-entry-dialog", 
                          self.on_request_entry_dialog)
        self.add_response("error", self.on_error)
        self.respondAfter["started"].append("settings")
        self.dialogInput = None

    def onStart(self, signal, *args, **kwargs):
        """Creates the gui"""
        self.settings = self.manager.raise_signal(
            "request-settings")["settings"]
        if "min_window_size" not in self.settings.keys():
            self.manager.raise_signal("set-new-setting",
                                      name="min_window_size",
                                      setting=WindowGeoSetting())
        if "window_size" not in self.settings.keys():
            self.manager.raise_signal("set-new-setting",
                                      name="window_size",
                                      setting=WindowGeoSetting())
        if "window_position" not in self.settings.keys():
            setting = WindowGeoSetting()
            setting.set((1,1))
            self.manager.raise_signal("set-new-setting",
                                      name="window_position",
                                      setting=setting)        
        if "pane_width" not in self.settings.keys():
            self.manager.raise_signal("set-new-setting",
                                      name="pane_width",
                                      setting=LeftPaneWidthSetting())
        (minWindowWidth, minWindowHeight) = self.settings[
            "min_window_size"].value
        (windowWidth, windowHeight) = self.settings["window_size"].value
        (windowPosX, windowPosY) = self.settings["window_position"].value
        leftPaneWidth = self.settings["pane_width"].value

        self.window = Gtk.Window()
        self.window.set_size_request(minWindowWidth, minWindowHeight)
        self.window.resize(windowWidth, windowHeight)
        self.window.move(windowPosX, windowPosY)
        self.window.connect("delete-event", self.quit)
        self.window.add_events(Gdk.EventMask.KEY_PRESS_MASK)
        self.window.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)

        self.headerBar = Gtk.HeaderBar()
        self.headerBar.props.show_close_button = True
        self.headerBar.set_title("File Browser")
        self.window.set_titlebar(self.headerBar)

        box = Gtk.Box(homogeneous=False)

        never = Gtk.PolicyType.NEVER
        self.leftPane = Gtk.ScrolledWindow(hscrollbar_policy=never)
        self.leftPane.set_size_request(leftPaneWidth, 0)
        self.leftPaneList = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.leftPaneList.modify_bg(0, Gdk.Color.parse("#f3f3f3")[1])
        self.leftPane.add(self.leftPaneList)

        self.centerStack = Gtk.Stack()
        self.centerStack.set_homogeneous(False)
        transition = Gtk.StackTransitionType.SLIDE_LEFT_RIGHT
        self.centerStack.set_transition_type(transition)
        self.centerStack.set_transition_duration(400)

        box.pack_start(self.leftPane, False, False, 0)
        box.pack_start(self.centerStack, True, True, 0)

        self.window.add(box)
        self.window.show_all()

    def onLeftPanePlaceRequest(self, signal, *args, **kwargs):
        """Places kwargs["widget"] on kwargs["side"] of leftPane,
        kwargs["side"] being "top" or "bottom" with "top" as default."""
        widget = kwargs["widget"]
        if "side" in kwargs.keys():
            side = kwargs["side"]
            if side == "top":
                self.leftPaneList.pack_start(widget, False, False, 0)
            elif side == "bottom":
                self.leftPaneList.pack_end(widget, False, False, 0)
            else:
                raise ValueError("side must be 'top' or 'bottom'")
        else:
            self.leftPaneList.pack_start(widget, False, False, 0)
        self.leftPaneList.show_all()

    def onCenterPlaceRequest(self, signal, *args, **kwargs):
        """Places kwargs["widget"] on kwargs["side"] of center,
        kwargs["side"] being "top" or "bottom" with "top" as default."""
        widget = kwargs["widget"]
        self.centerStack.add(widget)
        self.centerStack.show_all()
        self.centerStack.set_visible_child(widget)

    def onHeaderPlaceRequest(self, signal, *args, **kwargs):
        """Places kwargs["widget"] on kwargs["side"] of headerBar,
        kwargs["side"] being "left", "start", "right" or "end"."""
        widget = kwargs["widget"]
        if "side" in kwargs.keys():
            side = kwargs["side"]
            if side in ["start", "left"]:
                self.headerBar.pack_start(widget)
            elif side in ["end", "right"]:
                self.headerBar.pack_end(widget)
            else:
                raise ValueError("side must be 'left', 'start'"
                                 ", 'end' or 'right")
        else:
            raise ValueError("side must be 'left', 'start', 'end' or 'right")
        self.headerBar.show_all()

    def onLeftPaneRemoveRequest(self, signal, *args, **kwargs):
        """Removes kwargs["widget"] from leftPane."""
        widget = kwargs["widget"]
        self.leftPane.remove(widget)

    def onCenterRemoveRequest(self, signal, *args, **kwargs):
        """Removes kwargs["widget"] from center and sets last visible
        child visible again."""
        widget = kwargs["widget"]
        if self.centerStack.get_visible_child() == widget:
            children = self.centerStack.get_children()
            i = children.index(widget)
            if i > 0 or len(children) > 1:
                self.centerStack.set_visible_child(children[i - 1])
        self.centerStack.remove(widget)

    def onHeaderRemoveRequest(self, signal, *args, **kwargs):
        """Removes kwargs["widget"] from headerBar."""
        widget = kwargs["widget"]
        self.headerBar.remove(widget)

    def onChangeDir(self, signal, *args, **kwargs):
        """Sets subtitle to new path"""
        newPath = kwargs["newPath"]
        self.headerBar.set_subtitle(newPath)

    def onScrollRequest(self, signal, *args, **kwargs):
        """Scrolls to kwargs['widget'] or kwargs['y']"""
        if "y" in kwargs:
            y = kwargs["y"]
        else:
            widget = kwargs["widget"]
            (_, y) = widget.translate_coordinates(self.leftPaneList, 0, 0)
            if "offset" in kwargs:
                y += kwargs["offset"]
        self.leftPane.get_vadjustment().set_value(y)

    def onRequestWindow(self, signal, *args, **kwargs):
        """Return main window"""
        return self.window

    def on_request_entry_dialog(self, signal, *args, **kwargs):
        title = kwargs["title"]
        text = kwargs["text"]
        if "entryText" in kwargs:   
            entryText = kwargs["entryText"]
        else:
            entryText = ""
        d = EntryDialog(title, self.window, text, entryText, self)
        d.run()
        d.destroy()
        temp = self.dialogInput
        self.dialogInput = None
        return temp

    def on_error(self, signal, *args, **kwargs):
        """Create Error Dialog
        
        Kwargs:
            createDialog -- should be set to True if you want to show
            a dialog. Otherwise this function does nothing.
            errorCode -- used as title if no title argument is specified.
            title -- title of dialog. errorCode is used if not present.
            text -- (optional) explanation of the error.
            
        """
        createDialog = False
        if "createDialog" in kwargs:
            createDialog = kwargs["createDialog"]
        if not createDialog:
            return
        if "title" in kwargs:
            title = kwargs["title"]
        else:
            title = kwargs["errorCode"]
        dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR,
            Gtk.ButtonsType.OK, title)
        if "text" in kwargs:
            dialog.format_secondary_text(kwargs["text"])
        dialog.run()     
        dialog.destroy()        

    def quit(self, window=None, event=None):
        size = window.get_size()
        pos = window.get_position()
        self.manager.raise_signal("set-setting", setting="window_size",
                                  newValue=size)
        self.manager.raise_signal("set-setting", setting="window_position",
                                  newValue=pos)
        Gtk.main_quit()

def create_plugin(manager):
    """Creates an instance of guiManager"""
    return guiManager(manager)
