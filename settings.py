import plugins
import pickle
from os.path import join, dirname, abspath, isdir
from gi.repository import Gdk

SOURCE_DIR = dirname(abspath(__file__))

class Setting(object):
    """Basic class for settings"""
    
    def __init__(self, value=None):
        """Assigns value if not None, does nothing otherwise."""
        if value is not None:
            self.set(value)
        
    def isValidValue(self, value):
        """Returns wheter value is valid."""
        return True

    def set(self, value):
        """Sets value if it is valid."""
        if self.isValidValue(value):
            self.value = value
        else:
            raise ValueError("Invalid value {}".format(value))
            
    def setDefault(self):
        """Sets value to its default."""
        pass


class DirPathSetting(Setting):
    """Setting class for directory paths"""  
      
    def isValidValue(self, value):
        """Returns whether the path is a directory."""
        return os.path.isdir(value)
        
class BooleanSetting(Setting):
    """Setting class for boolean properities defaulting False"""

    def __init__(self):
        """Creates Setting object with value False."""
        Setting.__init__(False)
        self.value = False
        
    def isValidValue(self, value):
        """Returns True if value is boolean, false otherwise."""
        return type(value) is bool
        
    def setDefault(self):
        """Sets value to false."""
        self.value = False

"""class GdkColorSetting(object):
    
    def __init__(self, default):
        if self.isValidValue(default):
            Setting.__init__(self)
            self.setDefault = lambda: self.set(default)
            self.setDefault()
        else:
            raise ValueError("Invalid HTML color {}".format(default))
    
    def isValidValue(self, value):
        return Gdk.Color.parse(value)[0]

    def set(self, value):
        if self.isValidValue(value):
            self.value = Gdk.Color.parse(value)[1]
        else:
            raise ValueError("Invalid value {}".format(value))"""
        
class Settings(plugins.Plugin):
     """The settings plug-in load the settings from disk, sends 
     to other plug-ins or changes on request."""

    def __init__(self, manager):
        """Creates Settings plug-in."""
        plugins.Plugin.__init__(self, manager)
        self.pname = "settings"
        self.addResponse("started", self.onStart)
        self.addResponse("request-settings", self.onRequestSettings)
        self.addResponse("set-setting", self.onSetSetting)
        self.addResponse("revert-to-defaults", self.onRevertDefault)
        self.addResponse("revert-default-settings", self.onRevertDefault)
        self.addResponse("set-new-setting", self.onSetNewSetting)
        
    def onStart(self, signal, *args, **kwargs):
        """Loads settings from disk."""
        settingsPath = join(SOURCE_DIR, "settings")
        try:
            with open(settingsPath, "rb") as f:
                self.settings = pickle.load(f)
        except:
            self.settings = {} 
        
    def onRequestSettings(self, signal, *args, **kwargs):
        """Sets kwargs[“widget”].settings to self."""
        widget = kwargs["widget"]
        widget.settings = self.settings

    def onSetSetting(self, signal, *args, **kwargs):
        """Sets kwargs[“setting”] to kwargs[“newValue”]
        if kwargs[“newValue”] is valid. Saves changes to disk."""
        setting = kwargs["setting"]
        newValue = kwargs["newValue"]
        setting.set(newValue)
        self.save()      
        
    def onRevertDefault(self, signal, *args, **kwargs):
        """Loads default settings and saves changes to disk."""
        for setting in self.settings:
            setting.setDefault()
        self.save()
        
    def onSetNewSetting(self, signal, *args, **kwargs):
        """Adds kwargs[“setting”], which is an instance of Setting,
        to settings and saves changes to disk. This can also be used
        to override an old setting with a new Setting object."""
        name = kwargs["name"]
        setting = kwargs["setting"]
        self.settings[name] = setting
        self.save()

    def save(self):
        """Saves settings to disk"""
        settingsPath = join(SOURCE_DIR, "settings")    
        with open(settingsPath, "wb") as f:
            pickle.dump(self.settings, f)    

def createPlugin(manager):
    return Settings(manager)
