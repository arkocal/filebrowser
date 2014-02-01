import gtk

# Imports to get paths to thumbnails (GNOME)
import hashlib
import os
import platform
from os.path import isdir, isfile, join
import urlparse
import urllib

import re

from mimetypes import guess_type
# used to load and process images faster
from PIL import Image
import numpy
# used to load images simultaneously
import multiprocessing

"""Directory to look for thumbnails"""
# PORT thumnails only work on gnome
thumbnailsDir = "%s/.cache/thumbnails/large/" % (os.path.expanduser("~"))

LEFT_BUTTON = 1
RIGHT_BUTTON = 3
DOUBLE_CLICK = gtk.gdk._2BUTTON_PRESS


class PathClickZone:

    """ A helper class to find which file/directory has been clicked on """

    def __init__(self, x1, y1, x2, y2, path):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.path = path

    def collides(self, x, y):
        """ Returns whether the given point collides zone"""
        return (self.x1 < x < self.x2 and self.y1 < y < self.y2)


def pathToName(path):
    """ Converts path to a short string to show """
    if path == "/":
        return "/"
    else:
        return path.split("/")[-1]


def loadThumbnailers():
    """Load thumbnailers
    thumbnailer files should be saved in thumbnailersDir and must be written
    in Gnome's thumbnailer entry format"""
    thumbnailers = {}
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


def createPixbufThumbnail(pixbuf, size):
    """Creates a pixbuf thumbnail with given size and
    returns (thumbnail, width, height)"""
    height = float(pixbuf.get_height())
    width = float(pixbuf.get_width())
    if height > width:
        width = (width / height) * (size)
        height = size
    else:
        height = (height / width) * (size)
        width = size
    return (pixbuf.scale_simple(int(width), int(height), gtk.gdk.INTERP_TILES),
            width, height)


def path2url(path):
    """Returns url of given path"""
    return urlparse.urljoin('file:', urllib.pathname2url(path))


def path2thumbnail(path):
    """Returns path to thumbnail of file at path (uses Gnome thumbnails)"""
    return thumbnailsDir + hashlib.md5(path2url(path)).hexdigest() + ".png"


def createThumbnail(path):
    """Returns the thumbnail created for file at path (as numpy array,
    returna False if no thumbnail can be created"""
    fileName, ext = os.path.splitext(path)
    thumbnailers = loadThumbnailers()
    if ext.lower() in [".png", ".jpg", ".bmp", ".eps", ".gif", ".im", ".jpeg",
                       ".mps", ".pcx", ".ppm", ".tiff", ".webp", ".ico"]:
        try:
            image = Image.open(path)
        except:
            return False
        # If the image is big, scale down to 512x512 first using a faster
        # but lower quality scaling algorithm (Image.NEAREST)
        if image.size[0] > 512:
            image.thumbnail((512, 512), Image.NEAREST)
        image.thumbnail((256, 256), Image.ANTIALIAS)
        image.save(path2thumbnail(path))
    elif guess_type(path)[0] in thumbnailers.keys():
        o = path2thumbnail(path)
        u = path2url(path)
        s = "256"
        command = thumbnailers[guess_type(path)[0]]
        for (pat, sub) in [("%o", o), ("%i", path), ("%u", u), ("%s", s)]:
            command = re.sub(pat, sub, command)
        os.system(command)
        try:
            return Image.open(o)
        except:
            return False
    else:
        return False
    return image


def loadIcon(filename):
    """Load an icon for the file depending on the file extension"""
    iconsDir = "icons"
    fileName, ext = os.path.splitext(filename)
    try:
        ext = {".mp3": "audio"}[ext]
        iconPath = join(iconsDir, ext + ".png")
        print iconPath
        return Image.open(iconPath)
    except:
        #PORT icon path only valid with gnome
        fileIconPath = "/usr/share/icons/gnome/256x256/mimetypes/gtk-file.png"
        return Image.open(fileIconPath)


def loadImage(filename):
    """Load thumbnail for filename, create one if not found.
    Returns file name and tuple of loaded file (with resolution 256x256)
    saved as a numpy array"""
    thumbnailPath = path2thumbnail(filename)
    if not isfile(thumbnailPath):
        image = createThumbnail(filename)
        if not image:
            image = loadIcon(filename)
    else:
        try:
            image = Image.open(thumbnailPath)
        except:
            return None
    return(filename, numpy.array(image))


def openFile(path):
    # TEST test on other platforms than Linux
    system = platform.system()
    if system == "Linux":
        os.system("""xdg-open "%s" """ % path)
    elif system == "Windows":
        os.system("""start "%s" """ % path)
    else:
        os.system("""open "%s" """ % path)

def findFileIndexIn(path, dirs):
    """ Return dir, index where dir is the directory in which the file has
    been found and index is the index of the file in the directory """
    for d in dirs:
        try:
            index = d.index(path)
            foundIn = d
        except ValueError:
            continue
    return foundIn, index
