import pickle
from os.path import join, dirname, abspath, isdir
from gi.repository import Gdk

import plugins

SOURCE_DIR = dirname(abspath(__file__))


class Setting(object):

    """Base class for settings"""

    def __init__(self, value=None):
        """Assigns value if not None, does nothing otherwise."""
        if value is not None:
            self.set(value)

    def _is_valid_value(self, value):
        """Returns wheter value is valid."""
        return True

    def set(self, value):
        """Sets value if it is valid."""
        if self._is_valid_value(value):
            self.value = value
        else:
            raise ValueError("Invalid value {}".format(value))

    def set_default(self):
        """Sets value to its default."""
        pass


class DirPathSetting(Setting):

    """Setting class for directory paths"""

    def _is_valid_value(self, value):
        """Returns whether the path is a directory."""
        return os.path.isdir(value)


class BooleanSetting(Setting):

    """Setting class for boolean properities defaulting False"""

    def __init__(self):
        """Creates Setting object with value False."""
        Setting.__init__(self, False)
        self.value = False

    def _is_valid_value(self, value):
        """Returns True if value is boolean, false otherwise."""
        return type(value) is bool

    def set_default(self):
        """Sets value to false."""
        self.value = False


class Settings(plugins.Plugin):

    """The settings plug-in load the settings from disk, sends
    to other plug-ins or changes on request."""

    def __init__(self, manager):
        """Creates Settings plug-in."""
        plugins.Plugin.__init__(self, manager)
        self.pname = "settings"
        self.add_response("started", self.on_start)
        self.add_response("request-settings", self.on_request_settings)
        self.add_response("set-setting", self.on_set_setting)
        self.add_response("revert-to-defaults", self.on_revert_default)
        self.add_response("revert-default-settings", self.on_revert_default)
        self.add_response("set-new-setting", self.on_set_new_setting)

    def on_start(self, signal, *args, **kwargs):
        """Loads settings from disk."""
        settingsPath = join(SOURCE_DIR, "settings", "settings")
        try:
            with open(settingsPath, "rb") as f:
                self.settings = pickle.load(f)
        except:
            self.settings = {}

    def on_request_settings(self, signal, *args, **kwargs):
        """Returns an array of settings"""
        return self.settings

    def on_set_setting(self, signal, *args, **kwargs):
        """Sets kwargs["setting"] to kwargs["newValue"]
        if kwargs["newValue"] is valid. Saves changes to disk."""
        setting = self.settings[kwargs["setting"]]
        newValue = kwargs["newValue"]
        setting.set(newValue)
        self._save()

    def on_revert_default(self, signal, *args, **kwargs):
        """Loads default settings and saves changes to disk."""
        for setting in self.settings:
            setting.set_default()
        self._save()

    def on_set_new_setting(self, signal, *args, **kwargs):
        """Adds kwargs["setting"], which is an instance of Setting,
        to settings and saves changes to disk. This can also be used
        to override an old setting with a new Setting object."""
        name = kwargs["name"]
        setting = kwargs["setting"]
        self.settings[name] = setting
        self._save()

    def _save(self):
        """Saves settings to disk"""
        settingsPath = join(SOURCE_DIR, "settings", "settings")
        with open(settingsPath, "wb") as f:
            pickle.dump(self.settings, f)


def create_plugin(manager):
    return Settings(manager)
