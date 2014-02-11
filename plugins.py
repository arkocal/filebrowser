from os.path import isdir, isfile, join, dirname, abspath
import importlib
import pkgutil
import warnings
import pickle

SOURCE_DIR = dirname(abspath(__file__))


class Plugin:

    """ A class that can communicate with other Plugins through
        plugin manager"""

    def __init__(self, manager):
        """Create plugin object."""
        self.pname = "Plugin"
        self.manager = manager
        self.dependencies = []
        self.settingsUsed = []
        self.respondAfter = {}
        self.respondBefore = {}
        self.responses = {}
        self.id = -1
        self.responded = False

    def add_response(self, signal, func):
        """Add response to signal.
        
        Args
            signal: signal to respond to.
            func: function to respond with. Should take signal (str), 
            *args, **kwargs as args
        
        """
        self.responses[signal] = func
        self.respondAfter[signal] = []
        self.respondBefore[signal] = []

    def __str__(self):
        """Return plugin name."""
        return self.pname


class PluginManager:

    """ A helper class to manage plugins and signals"""

    def __init__(self):
        """ Initializes PluginManager"""
        self._load_plugins()
        self.raise_signal("started")

    def _load_plugins(self):
        """Imports modules containing the plug-ins."""
        self.plugins = []
        self.pluginNames = {}
        pluginId = 0   
        pluginsPackage = importlib.import_module("plugin")
        for _, pluginName, __ in pkgutil.iter_modules(pluginsPackage.__path__):
            module = importlib.import_module("plugin.{}".format(pluginName))
            newPlugin = module.create_plugin(self)
            newPlugin.id = pluginId
            pluginId += 1
            self.plugins.append(newPlugin)
            self.pluginNames[newPlugin.pname] = newPlugin
            print("Plug-in loaded: {}".format(pluginName))
        else:
            warnings.warn("Failed to load plug-in %s" %
                          pluginName, Warning)

    def raise_signal(self, signal, *args, **kwargs):
        """Raise signal with given args
        
        Returns:
            A dictionary with plugin names as keys
            and return values of response functions as values.
            
        """
        raiseTo = self._get_plugins_to_raise_signal(signal)
        results = {}
        for target in raiseTo:
            results[target.pname] = target.responses[signal](signal,
                                                             *args, **kwargs)
                                                             
    def _get_plugins_to_raise_signal(self, signal):
        """Returns a list of plug-ins in the order they can respond
        to signal."""
        result = []  # TODO check if it is possible
        # Get plugins that respond to signal
        candidates = [c for c in self.plugins if signal in c.responses.keys()]
        numberOfPlugins = len(self.plugins)
        # O(numberOfPlugins^2) create a nxm matrix for faster comprasion,
        # compMap[i][j] == True means plugins with id i responds after j
        compMap = [[False for i in range(numberOfPlugins)] 
                for j in range(numberOfPlugins)]
        for c1 in candidates:
            for earlyPluginName in c1.respondAfter[signal]:
                earlyPlugin = self.pluginNames[earlyPluginName]
                compMap[c1.id][earlyPlugin.id] = True
            for latePluginName in c1.respondBefore[signal]:
                latePlugin = self.pluginNames[latePluginName]
                compMap[latePlugin.id][c1.id] = True
        #Clear respondAfter and respondBefore before merging them.
        for candidate in candidates:
            candidate.responded = False
            candidate.respondAfter[signal] = []
            candidate.respondBefore[signal] = []
        #recreate respondAfter
        for i in range(numberOfPlugins):
            for j in range(numberOfPlugins):
                if compMap[i][j]:
                    name = self.plugins[j].pname
                    self.plugins[i].respondAfter[signal].append(name)
        #create plugins list in order they respond
        i = 0
        while i < len(candidates):
            plugin = candidates[i]
            if plugin.responded:
                i += 1
                continue
            found = True
            while found:
                found = False
                for upperName in plugin.respondAfter[signal]:
                    upper = self.pluginNames[upperName]
                    if not upper.responded:
                        plugin = upper
                        found = True
                        break
            plugin.responded = True
            result.append(plugin)
        return result
