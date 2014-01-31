from os.path import isdir, isfile, join, dirname, abspath
import warnings
import pickle

#import globals
SOURCE_DIR = dirname(abspath(__file__))

class Plugin:
    """ A class that can communicate with other Plugins through
        plugin manager"""
    def __init__(self, manager):
        self.pname = "Plugin"
        self.manager = manager
        self.dependencies = []
        self.settingsUsed = []
        self.respondAfter = {}
        self.respondBefore = {}
        self.responses = {}
        self.id = -1
        self.responded = False
        
    def addResponse(self, signal, func):
        self.responses[signal] = func
        self.respondAfter[signal] = []
        self.respondBefore[signal] = [] 

    def __str__(self):
        return self.pname
        
class PluginManager:
    """ A helper class to manage plugins and signals"""
    def __init__(self):
        """ Initializes PluginManager"""
        self.getPluginsList()
        self.loadPlugins()
        self.raiseSignal("started")
        
    def getPluginsList(self):
        pluginsListFile = join(SOURCE_DIR, "plugins.list")
        if not isfile(pluginsListFile):
            warnings.warn("plugins.list not found, loading default values", 
                    Warning)
            self.pluginsList = self.getDefaultPluginsList()
        else:
            with open(pluginsListFile) as f:
                # comprehension ignores empty lines
                self.pluginsList = [p for p in f.read().splitlines() if p]
        
    def getDefaultPluginsList(self):
        return ["main_arkocal", "dirTree_arkocal", "dirFrame_arkocal"]
        
    def loadPlugins(self):
        self.plugins = []
        self.pluginNames = {}
        pluginId = 0
        for pluginName in self.pluginsList:
            pluginPath = join(SOURCE_DIR, pluginName + ".py")
            if isfile(pluginPath ):
                module = __import__(pluginName)
                newPlugin = module.createPlugin(self)
                newPlugin.id = pluginId
                pluginId += 1
                self.plugins.append(newPlugin)
                self.pluginNames[newPlugin.pname] = newPlugin
                print ("Plug-in loaded: {}".format(pluginName))
            else:
                warnings.warn("Failed to load plug-in %s" %pluginName, Warning)
            
    def raiseSignal(self, signal, *args, **kwargs):
        raiseTo = self.getPluginsToRaiseSignal(signal)
        for target in raiseTo:
            target.responses[signal](signal, *args, **kwargs)
        
    def getPluginsToRaiseSignal(self, signal):
        result = [] #TODO check if it is possible
        # O(n*m) get plugins that respond to signal
        candidates = [c for c in self.plugins if signal in c.responses.keys()]
        n = len(self.plugins)
        # O(n^2) create a nxm matrix for faster comprasion,
        # compMap[i][j] == True means plugins with id i responds after j
        compMap = [[False for i in range(n)] for j in range(n)]
        for c1 in candidates:
            for earlyPluginName in c1.respondAfter[signal]:
                earlyPlugin = self.pluginNames[earlyPluginName]
                compMap[c1.id][earlyPlugin.id] = True
            for latePluginName in c1.respondBefore[signal]:
                latePlugin = self.pluginNames[latePluginName]
                compMap[latePlugin.id][c1.id] = True
        # O(n) Clear respondAfter and respondBefore to merge both using
        # compMap
        for candidate in candidates:
            candidate.responded = False  
            candidate.respondAfter[signal] = []
            candidate.respondBefore[signal] = []
        # O(n^2) recreate respondAfter
        for i in range(n):
            for j in range(n):
                if compMap[i][j]:
                    name = self.plugins[j].pname
                    self.plugins[i].respondAfter[signal].append(name)
        # o (n^2) create plugins list in order they respond
        i = 0
        while i < len(candidates):
            plugin = candidates[i]
            if plugin.responded:
                i += 1
                continue
            found = True
            while found:
                found = False
                for upperName in  plugin.respondAfter[signal]:
                    upper = self.pluginNames[upperName]
                    if not upper.responded:
                        plugin = upper
                        found = True
                        break
            plugin.responded = True                        
            result.append(plugin)
        return result
