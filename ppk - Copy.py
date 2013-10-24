import zipimport
import zipfile
import pickle
import sys
import os
import re

try:
    from PIL import Image
    from PIL import ImageTk
    image_ready = True
except ImportError:
    image_ready = False

try:
    from PySidez import QtGui
    qt_ready = True
except ImportError:
    qt_ready = False

class Pool(object):
    globs = []
    mount = {}
    cache = {}

    def __init__(self, echo=False):
        super().__init__()
        self.echo = echo

    def __getitem__(self, attr):
        match = re.match(r'([\w]*):', attr)
        if match:
            prefix = match.group(1)
            attr = attr[match.end(1) + 1:]
            if prefix == 'i':
                return self.image(attr)
            if prefix == 'f':
                return self.open(attr)
            if prefix == 'py':
                return self.pyimport(attr)
            if prefix == 'qt':
                qpix = QtGui.QPixmap()
                qpix.loadFromData(self.read(attr))
                qicon = QtGui.QIcon(qpix)
                return qicon
        return self.read(attr)

    def nameof(self, path):
        return os.path.splitext(os.path.basename(path))[0]

    def load(self, path):
        if self.echo: print('Loading', os.path.basename(path))

        arch = zipfile.ZipFile(path, allowZip64=True)
        names = []
        try:
            info = arch.getinfo('__name__')
            names = arch.open(info).read().decode().split('\n')
        except KeyError:
            names.append(self.nameof(path))

        if names[0] == '__global__':
            if arch in self.globs:
                arch.close()
            else:
                self.globs.append(arch)
        else:
            arch.names = names
            for name in names:
                if name in self.mount:
                    if self.echo: print(os.path.basename(path), 'already loaded at', name)
                else:
                    if self.echo: print(os.path.basename(path), 'loaded at', name)
                    self.mount[name] = arch

        return name

    def unload(self, name, ispath=False):
        if ispath:
            name = self.nameof(name)

        if name in self.mount:
            arch = self.mount.pop(name)
            arch.close()
            del arch
            if self.echo: print(name, 'unloaded')
            return True
        else:
            for (i, arch) in enumerate(self.globs):
                if self.nameof(arch.name) == name:
                    arch = self.globs.pop(i)
                    arch.close()
                    del arch
                    if self.echo: print(name, 'globally unloaded')
                    return True
        return False
    
    def include(self, path=os.getcwd(), walk=False):
        for filename in os.listdir(path):
            if filename.endswith('.ppk' ):
                filepath = os.path.join(path, filename)
                self.load(filepath)
    
    def split_path(self, split_path):
        split_path = os.path.normpath(split_path)
        pathSplit_lst   = []
        while os.path.basename(split_path):
            pathSplit_lst.append(os.path.basename(split_path) )
            split_path = os.path.dirname(split_path)
        pathSplit_lst.reverse()
        return pathSplit_lst

    def open(self, path):
        path = self.split_path(path)
        pathlocal = '/'.join(path[1:])
        pathglobal = '/'.join(path)
        name = path[0]

        if self.echo: print(name, pathlocal)

        arch = self.mount[name]
        #return arch.extractfile(pathlocal)
        return arch.open(pathlocal)

    def read(self, path, default=None):
        try:
            data = self.open(path).read()
            return data
        except KeyError as err:
            if default:
                return default
            raise err

    def image(self, path, default=None):
        if not image_ready:
            raise RuntimeError('PIL library not available' )

        key = '/'.join(self.split_path(path) )
        if key in self.cache:
            return self.cache[ key ]
        else:
            try:
                data = self.read(path)
                tkim = ImageTk.PhotoImage(data=data)
                self.cache[key] = tkim
                return tkim
            except KeyError as err:
                if default:
                    return default
                raise err

    def pyimport(self, path):
        path = self.split_path(path)
        zippath = self.mount[path[0]].filename
        importer = zipimport.zipimporter(zippath)
        return importer.load_module('/'.join(path[1:]))