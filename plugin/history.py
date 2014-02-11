from gi.repository import Gtk

import plugins


class History(plugins.Plugin):

    def __init__(self, manager):
        plugins.Plugin.__init__(self, manager)
        self.pname = "history"
        self.dependencies.append("settings")
        self.dependencies.append("dirTree")
        self.dependencies.append("guiManager")
        self.add_response("started", self.on_start)
        self.add_response("change-dir", self.on_change_dir)
        self.add_response("load-prev-dir", self._load_prev)
        self.respondBefore["started"].append("dirTree")

    def on_start(self, signal, *args, **kwargs):
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
        self.prevButton.connect("clicked", self._load_prev)
        self.nextButton.connect("clicked", self._load_next)
        self.widget = Gtk.Box()
        Gtk.StyleContext.add_class(self.widget.get_style_context(), "linked")
        self.widget.add(self.prevButton)
        self.widget.add(self.nextButton)
        self.widget.show()
        self.manager.raise_signal("request-place-header", widget=self.widget,
                                  side="left")

    def on_change_dir(self, signal, *args, **kwargs):
        if "raisedBy" in kwargs:
            raisedBy = kwargs["raisedBy"]
            if raisedBy == self:
                return
        newPath = kwargs["newPath"]
        self.pathsLogIndex += 1
        if len(self.pathsLog) > self.pathsLogIndex:
            self.pathsLog[self.pathsLogIndex] = newPath
            self.pathsLog = self.pathsLog[:self.pathsLogIndex + 1]
        else:
            self.pathsLog.append(newPath)
        if len(self.pathsLog) - 1 > self.pathsLogIndex:
            self.nextButton.set_state(Gtk.StateType.NORMAL)
        else:
            self.nextButton.set_state(Gtk.StateType.INSENSITIVE)
        if self.pathsLogIndex > 0:
            self.prevButton.set_state(Gtk.StateType.NORMAL)

    def _load_prev(self, _=None):
        if self.pathsLogIndex == 0:
            return
        self.pathsLogIndex -= 1
        newPath = self.pathsLog[self.pathsLogIndex]
        self.manager.raise_signal("change-dir", newPath=newPath, raisedBy=self)
        if self.pathsLogIndex == 0:
            self.prevButton.set_state(Gtk.StateType.INSENSITIVE)
        self.nextButton.set_state(Gtk.StateType.NORMAL)

    def _load_next(self, _):
        self.pathsLogIndex += 1
        newPath = self.pathsLog[self.pathsLogIndex]
        self.manager.raise_signal("change-dir", newPath=newPath, raisedBy=self)
        if self.pathsLogIndex >= len(self.pathsLog) - 1:
            self.nextButton.set_state(Gtk.StateType.INSENSITIVE)
        self.prevButton.set_state(Gtk.StateType.NORMAL)


def create_plugin(manager):
    """Creates an instance of History"""
    return History(manager)
