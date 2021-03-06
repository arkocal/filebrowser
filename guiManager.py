"""
guiManager

guiManager plug-in places widget created by other plug-ins on requests

Dependencies
guiManager doesn't have any dependencies.
"""

from threading import Thread

from gi.repository import Gtk, Gdk

import settings
import plugins

class LeftPaneWidthSetting(settings.Setting):
    """Setting for left pane width."""
    
    def __init__(self):
        """Creates a LeftPaneWidthSetting object."""
        settings.Setting.__init__(self)
        self.setToDefault()

    def isValidValue(self, value):
        """Returns whether value is a valid width."""
        try:
            return (type(value) is int) and (0 < value < 60000)
        except:
            return False
            
    def setToDefault(self):
        """ Sets left pane width to default."""
        self.set(240)

class WindowSizeSetting(settings.Setting):
    """Setting for window size. Value is tuple (width, height)"""

    def __init__(self):
        """Creates a WindowSizeSetting object."""
        settings.Setting.__init__(self)
        self.setToDefault()

    def isValidValue(self, value):
        """Returns if value is a valid (width, height) tuple"""
        try:
            return ((0 < value[0] < 60000) and
                    (0 < value[1] < 60000))
        except:
           return False
            
    def setToDefault(self):
        """ Sets window size to default."""
        self.set((650,480))

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
       """

    def __init__(self, manager):
        plugins.Plugin.__init__(self, manager)
        self.pname = "guiManager"
        self.dependencies.append("settings")
        self.addResponse("started", self.onStart)
        self.addResponse("request-place-left-pane",
                         self.onLeftPanePlaceRequest)
        self.addResponse("request-place-center", self.onCenterPlaceRequest)
        self.addResponse("request-place-header", self.onHeaderPlaceRequest)
        self.addResponse("request-remove-left-pane",
                         self.onLeftPaneRemoveRequest)
        self.addResponse("request-remove-center", self.onCenterRemoveRequest)
        self.addResponse("request-remove-header", 
                         self.onHeaderRemoveRequest)
        self.addResponse("change-dir", self.onChangeDir)
        self.respondAfter["started"].append("settings")

    def onStart(self, signal, *args, **kwargs):
        """Creates the gui"""
        self.settings = None
        self.manager.raiseSignal("request-settings", widget=self)
        if "min_window_size" not in self.settings.keys():
            self.manager.raiseSignal("set-new-setting", 
                                     name="min_window_size",
                                     setting = WindowSizeSetting())
        if "pane_width" not in self.settings.keys():
            self.manager.raiseSignal("set-new-setting", 
                                     name="pane_width",
                                     setting = LeftPaneWidthSetting())        
        (MIN_WIDTH, MIN_HEIGHT) = self.settings["min_window_size"].value
        LEFT_PANE_WIDTH = self.settings["pane_width"].value
            
        
        self.window = Gtk.Window()
        self.window.set_size_request(MIN_WIDTH, MIN_HEIGHT)
        self.window.connect("delete-event", Gtk.main_quit)
        self.window.add_events(Gdk.EventMask.KEY_PRESS_MASK)        
        self.window.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)        
        
        self.headerBar = Gtk.HeaderBar()
        self.headerBar.props.show_close_button = True
        self.headerBar.set_title("File Browser")
        self.window.set_titlebar(self.headerBar)
        
        box = Gtk.Box(homogeneous=False)
        
        never = Gtk.PolicyType.NEVER
        self.leftPane = Gtk.ScrolledWindow(hscrollbar_policy = never)
        self.leftPane.set_size_request(LEFT_PANE_WIDTH, 0)
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
                self.centerStack.set_visible_child(children[i-1])
        self.centerStack.remove(widget)
        
    def onHeaderRemoveRequest(self, signal, *args, **kwargs):
        """Removes kwargs["widget"] from headerBar."""
        widget = kwargs["widget"]
        self.headerBar.remove(widget)

    def onChangeDir(self, signal, *args, **kwargs):
        """Sets subtitle to new path"""
        newPath = kwargs["newPath"]
        self.headerBar.set_subtitle(newPath)

def createPlugin(manager):
    """Creates an instance of guiManager"""
    return guiManager(manager)
