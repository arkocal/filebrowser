import os
import platform

import plugins


class FileManager(plugins.Plugin):

    def __init__(self, manager):
        plugins.Plugin.__init__(self, manager)
        self.pname = "fileManager"
        self.add_response("started", self.on_start)
        self.add_response("file-activated", self.on_file_activated)
        self.add_response("file-rename", self.on_file_rename)

    def on_start(self, signal, *args, **kwargs):
        self.system = platform.system()

    def on_file_activated(self, signal, *args, **kwargs):
        files = kwargs["files"]
        systemOpen = {
            "Linux": "xdg-open", "Windows": "open", "Darwin": "start"}
        if "app" in kwargs.keys():
            app = kwargs["app"]
        else:
            app = systemOpen[self.system]
        for f in files:
            os.system('{} "{}"'.format(app, f))

    def on_file_rename(self, signal, *args, **kwargs):
        files = kwargs["files"]
        newName = kwargs["newName"]
        newNamesGiven = []
        if "/" in newName:
            self.manager.raise_signal("error", errorCode="INVALID_FILENAME",
                                      createDialog=True, 
                                      title="Invalid file name",
                                      text="File names can not contain '/'")
        if len(files) == 1:
            filePath, fileName = os.path.split(files[0])
            filesInDir = os.listdir(filePath)
            newPath = os.path.join(filePath , newName)
            if newName in filesInDir:
                self.manager.raise_signal("error", errorCode="USED_FILENAME",
                                      createDialog=True, 
                                      title="Invalid file name",
                                      text="There is another file with the "
                                           "name {} in the directory".format(
                                                newName))
                newNamesGiven.append(fileName)
            else:
                os.rename(files[0], newPath)
                newNamesGiven.append(newName)
        else:
            for i, file_ in enumerate(files):
                filePath, fileName = os.path.split(file_)
                filesInDir = os.listdir(filePath)                
                if len(fileName.split(".")) > 1:                
                    ext = fileName.split(".")[-1]
                else:
                    ext = ""
                newNameWithoutPath = newName + "-" + str(i+1) + "." + ext                    
                n = os.path.join(filePath , newNameWithoutPath)
                if newNameWithoutPath in filesInDir:   
                    self.manager.raise_signal("error", errorCode="USED_FILENAME",
                                          createDialog=True, 
                                          title="Invalid file name",
                                          text="There is another file with the "
                                               "name {} in the directory".format(
                                                    newName))
                    newNamesGiven.append(fileName)                             
                else:
                    newNamesGiven.append(n)
                    os.rename(file_, n)
        return newNamesGiven

def create_plugin(manager):
    return FileManager(manager)
