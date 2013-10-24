import tkinter
import tkinter.ttk
import tkinter.filedialog
import tkinter.messagebox
import tkinter.scrolledtext
from tkinter.constants import *

import os
import csv
import types
import pickle
from copy import copy

import tkscroll

import persist

class _BasePrompt(tkinter.Toplevel):
    __default__ = ''
    
    def __init__(self, root, reader, config, hull=None):
        tkinter.Toplevel.__init__(self, root)
        
        self.root = root
        self.reader = reader
        self.config = config
        self.key = config[ 'key' ]

        if hull:
            self.hull = hull
            self.setup()
            self.withdraw()
            return

        self.transient(root)
        self.focus_set()
        self.grab_set()
        self.title(self.__class__.__name__ + ': ' + self.key)

        self._setup()
        self.setup()
        self.postsetup()
    
    def _setup(self):
        tkinter.ttk.Button(self, text='Save', command=self._save).grid(column=0, row=0, sticky='WE')
        tkinter.ttk.Button(self, text='Revert', command=self.revert).grid(column=1, row=0, sticky='WE')
        tkinter.ttk.Button(self, text='Cancel', command=self.destroy).grid(column=2, row=0, sticky='WE')

        tkinter.ttk.Separator(self, orient=HORIZONTAL).grid(column=0, columnspan=3, row=1, sticky='WE')
        
        self.hull = tkinter.ttk.Frame(self)
        self.hull.grid(column=0, columnspan=3, row=2, sticky='WESN')
        
        if 'info' in self.config:
            tkinter.ttk.Separator(self, orient=HORIZONTAL).grid(column=0, columnspan=3, row=3, sticky='WE')
            info = tkscroll.ScrolledText(self, width=5, height=5, wrap=WORD)
            info.grid(column=0, columnspan=3, row=4, sticky='WESN')
            info.text.insert(0.0, self.config[ 'info' ])
            info.text.config(state=DISABLED)

        for i in range(3):
            self.columnconfigure(i, weight=1)
        for i in (2, 4):
            self.rowconfigure(i, weight=1)
        
        self.bind('<Escape>', lambda e: self.destroy())
    
    def setup(self):
        self.strvar = tkinter.StringVar(value=self.get()) #tkinter.StringVar(self, value=self.get())
        entry = tkinter.ttk.Entry(self.hull, textvariable=self.strvar)
        entry.pack(expand=True, fill=BOTH)
        entry.bind('<Return>', lambda e: self._save())

    def postsetup(self):
        self.geometry('+{0}+{1}'.format( self.root.winfo_rootx(), self.root.winfo_rooty()) )
        self.update()
        self.minsize(self.winfo_width(), self.winfo_height())
    
    def _save(self):
        self.save()
        self.destroy()
    
    def save(self):
        self.set(self.strvar.get())
    
    def revert(self):
        self.reader.revert(self.key)
        self.destroy()
        
    def set(self, data):
        self.reader.set(self.key, data)
    
    def get(self):
        return self.reader.get(self.key)

    def call(self):
        self.reader.call(self.key)

class IntPrompt(_BasePrompt):
    pass

class TextPrompt(_BasePrompt):
    def setup(self):
        textframe = tkscroll.ScrolledText(self.hull, width=50, height=20, wrap=NONE)
        textframe.grid(column=0, columnspan=2, row=0, sticky='WESN')
        textframe.grid(column=0, columnspan=2, row=0, sticky='WESN')
        textframe.text.insert(1.0, self.get())
        self.text = textframe.text
        
        tkinter.ttk.Button(self.hull, text='Import', compound=LEFT, command=self.imp).grid(column=0, row=1, sticky='WE')
        tkinter.ttk.Button(self.hull, text='Export', compound=RIGHT, command=self.exp).grid(column=1, row=1, sticky='WE')

        for i in range(2):
            self.hull.columnconfigure(i, weight=1)
        for i in range(1):
            self.hull.rowconfigure(i, weight=1)
    
    def save(self):
        self.set(self.text.get( 1.0, END)[:-1] )
    
    def imp(self):
        file = tkinter.filedialog.askopenfile('r')
        if file:
            data = file.read()
            file.close()
            self.text.delete(0.0, END)
            self.text.insert(0.0, data)
        self.lift()
    
    def exp(self):
        file = tkinter.filedialog.asksaveasfile('w')
        if file:
            data = self.text.get(1.0, END)[:-1]
            file.write(data)
            file.close()
        self.lift()

class BoolPrompt(_BasePrompt):
    def setup(self):
        self.boolvar = tkinter.BooleanVar(self, value=self.get())
        tkinter.ttk.Checkbutton(self.hull, variable=self.boolvar).pack(expand=True, fill=BOTH)
    
    def save(self):
        self.set(self.boolvar.get())

class RadioPrompt(_BasePrompt):
    def setup(self):
        options = self.config[ 'options' ]
        self.intvar = tkinter.IntVar(self, value=self.get())
        for i, option in enumerate(options):
            tkinter.ttk.Radiobutton(self.hull, text=option, variable=self.intvar, value=i).grid(column=0, row=i, sticky='W')
            self.hull.rowconfigure(i, weight=1)
    
    def save(self):
        self.set(self.intvar.get())

class CheckPrompt(_BasePrompt):
    def setup(self):
        options = self.config[ 'options' ]
        values = self.get()
        self.boolvars = []
        for i, option in enumerate(options):
            value = values[ i ]
            boolvar = tkinter.BooleanVar(self, value=value)
            tkinter.ttk.Checkbutton(self.hull, text=option, variable=boolvar).grid(column=0, row=i, sticky='W')
            self.hull.rowconfigure(i, weight=1)
            self.boolvars.append(boolvar)
    
    def save(self):
        self.set([ bool( boolvar.get()) for boolvar in self.boolvars ] )

class OptionPrompt(_BasePrompt):
    def setup(self):
        options = self.config[ 'options' ]
        current = options[ self.get() ]
        self.strvar = tkinter.StringVar(self, value=current)
        tkinter.ttk.OptionMenu(self.hull, self.strvar, current, *options).pack(expand=True, fill=BOTH)#.grid(column=0, row=0, padx=10, pady=10, sticky='WE')
    
    def save(self):
        index = self.config[ 'options' ].index(self.strvar.get())
        self.set(index)

class ScalePrompt(_BasePrompt):
    def setup(self):
        self.scale = tkinter.Scale(self.hull, from_=self.config.get('from', 0), to=self.config.get('to', 100), orient=HORIZONTAL)#, length=70 )
        #self.scale.grid(column=0, row=0, pady=10, sticky='WE')
        self.scale.pack(expand=True, fill=BOTH)
        self.scale.set(self.get())
    
    def save(self):
        self.set(self.scale.get())

class ListPrompt(_BasePrompt):
    def setup(self):
        listbfrm = tkscroll.ScrolledListbox(self.hull, width=50, selectmode=EXTENDED)
        listbfrm.grid(column=0, row=0, columnspan=4, sticky='WESN')
        self.listb = listb = listbfrm.listbox
        listb.insert(END, *self.get())

        listb.bind('<Delete>', self.remove)
        listb.bind('<Double-Button-1>', self.edit)
        
        tkinter.ttk.Button(self.hull, text='Up', command=self.moveUp).grid(column=0, row=1, sticky='WESN')
        tkinter.ttk.Button(self.hull, text='Down', command=self.moveDown).grid(column=0, row=2, sticky='WESN')
        
        tkinter.ttk.Button(self.hull, text='Add', command=self.add).grid(column=1, row=1, rowspan=2, sticky='WESN')
        tkinter.ttk.Button(self.hull, text='Remove', command=self.remove).grid(column=2, row=1, rowspan=2, sticky='WESN')
        tkinter.ttk.Button(self.hull, text='Edit', command=self.edit).grid(column=3, row=1, rowspan=2, sticky='WESN')

        for i in range(4)[1:]:
            self.hull.columnconfigure(i, weight=2)
        self.hull.columnconfigure(0, weight=1)
        self.hull.rowconfigure(0, weight=1)
    
    def add(self, event=None):
        root = tkinter.Toplevel(self)
        root.resizable(0, 0)
        root.transient(self)
        root.grab_set()
        root.geometry('+{0}+{1}'.format( self.winfo_rootx(), self.winfo_rooty()) )
        root.title('Add Entry')
        
        strvar = tkinter.StringVar(self)
        entry = tkinter.ttk.Entry(root, textvariable=strvar, width=self.listb[ 'width' ])
        entry.grid(column=0, row=0, sticky='WESN')
        #entry.pack(side=LEFT)
        entry.focus_set()
        
        def accept():
            if not strvar.get() == '':
                self.listb.insert(END, strvar.get())
            root.destroy()
        
        entry.bind('<Return>', lambda e: accept())
        tkinter.ttk.Button(root, text='Save', command=accept).grid(column=1, row=0, sticky='WESN')#.pack(side=LEFT)
    
    def remove(self, event=None):
        items = self.listb.curselection()
        if items:
            #item = items[0]
            for item in reversed(items):
                self.listb.delete(item)
    
    def edit(self, event=None):
        items = self.listb.curselection()
        if items:
            item = items[0]
            current = self.listb.get(item)
            
            root = tkinter.Toplevel(self)
            root.resizable(0, 0)
            root.transient(self)
            root.grab_set()
            root.geometry('+{0}+{1}'.format( self.winfo_rootx(), self.winfo_rooty()) )
            root.title('Edit Entry')
            
            strvar = tkinter.StringVar(self, value=current)
            entry = tkinter.ttk.Entry(root, textvariable=strvar, width=self.listb[ 'width' ])
            entry.grid(column=0, row=0, sticky='WESN')
            entry.focus_set()
            entry.icursor(END)
            
            def accept():
                #self.listb.insert(END, strvar.get())
                if not strvar.get() == '':
                    self.listb.delete(item)
                    self.listb.insert(item, strvar.get())
                root.destroy()
            
            entry.bind('<Return>', lambda e: accept())
            tkinter.ttk.Button(root, text='Save', command=accept).grid(column=1, row=0, sticky='WESN')
    
    def moveUp(self):
        items = self.listb.curselection()
        if items:
            for item in items:
                item = int(item)
                if item > 0:
                    data = self.listb.get(item)
                    self.listb.delete(item)
                    self.listb.insert(item - 1, data)
                    self.listb.select_set(item - 1)
                else:
                    self.listb.select_set(0)
    
    def moveDown(self):
        items = self.listb.curselection()
        if items:
            for item in items:
                item = int(item)
                data = self.listb.get(item)
                self.listb.delete(item)
                self.listb.insert(item + 1, data)
                self.listb.select_set(item + 1)
    
    def save(self):
        self.set(list( self.listb.get( 0, END) ) )
    
class FileOpenPrompt(_BasePrompt):
    def setup(self):
        _BasePrompt.setup(self)
        tkinter.ttk.Button(self.hull, text='Choose', command=self.choose).pack(fill=X)
    
    def choose(self):
        path = tkinter.filedialog.askopenfilename()
        if path:
            self.strvar.set(path)
        self.root.lift()
        self.lift()

class FileSavePrompt(FileOpenPrompt):
    def choose(self):
        path = tkinter.filedialog.asksaveasfilename()
        if path:
            self.strvar.set(path)
        self.root.lift()
        self.lift()

class FolderPrompt(FileOpenPrompt):
    def choose(self):
        path = tkinter.filedialog.askdirectory()
        if path:
            self.strvar.set(path)
        self.root.lift()
        self.lift()

class FunctionBlind(_BasePrompt):
    __default__ = '#function call'
    def _setup(self):
        pass

    def setup(self):
        self.call()

class FunctionButton(FunctionBlind):
    _setup = _BasePrompt._setup

    def setup(self):
        if not 'persist' in self.config:
            self.config['persist'] = False
        self.top.destroy()
        tkinter.ttk.Button(self.hull, text='\nExecute\n', command=self.buttoncall).pack(expand=True, fill=BOTH)

    def buttoncall(self):
        self.call()
        if not self.config['persist']:
            self.destroy()

class TablePrompt(_BasePrompt):
    __default__ = [[],]

    def setup(self):
        self.width = width = self.config.get('width', 5)
        self.height = height = self.config.get('height', 5)

        #xoffset = 1
        #yoffset = 1

        for i in range(width):
            tkinter.ttk.Label(self.hull, text=str(i + 1), anchor=CENTER, relief=SUNKEN).grid(column=i + 1, row=0, ipadx=2, ipady=2, sticky='WESN')
            self.hull.columnconfigure(i + 1, weight=1)

        for i in range(height):
            tkinter.ttk.Label(self.hull, text=str(i + 1), anchor=CENTER, relief=SUNKEN).grid(column=0, row=i + 1, ipadx=2, ipady=2, sticky='WESN')
            self.hull.rowconfigure(i + 1, weight=1)

        data = self.get()
        self.grid = []

        for y in range(height):
            row = []
            for x in range(width):
                entry = tkinter.ttk.Entry(self.hull)
                entry.grid(column=x + 1, row=y + 1, sticky='WESN')
                if len(data) > y:
                    if len(data[y]) > x:
                        entry.insert(0, data[y][x])
                row.append(entry)
            self.grid.append(row)

        frame = tkinter.ttk.Frame(self.hull)
        frame.grid(column=0, columnspan=width + 1, row=height + 2, sticky='WESN')
        tkinter.ttk.Button(frame, text='Import', command=self.imp).pack(side=LEFT, expand=True, fill=X)
        tkinter.ttk.Button(frame, text='Export', command=self.exp).pack(side=LEFT, expand=True, fill=X)

    def iterrow(self):
        for y in range(self.height):
            row = []
            for x in range(self.width):
                row.append(self.grid[y][x].get())
            yield row

    def imp(self):
        file = tkinter.filedialog.askopenfile(parent=self, mode='r', filetypes=[('CSV Spreadsheet', '.csv'),])
        if file:
            reader = csv.reader(file)
            y = 0
            for row in reader:
                for x in range(self.width):
                    self.grid[y][x].delete(0, END)
                    if len(row) <= x: continue
                    self.grid[y][x].insert(0, row[x])
                if y == self.height: break
                y += 1
            file.close()


    def exp(self):
        file = tkinter.filedialog.asksaveasfile(parent=self, mode='w', defaultextension='.csv', filetypes=[('CSV Spreadsheet', '.csv'),])
        if file:
            writer = csv.writer(file, lineterminator='\n')
            for row in self.iterrow():
                writer.writerow(row)
            file.close()

    def save(self):
        data = []
        for row in self.iterrow():
            data.append(row)
        self.set(data)

class Widget(tkinter.ttk.Frame):
    """This is still under development. I wouldn't suggest using it."""
    def __init__(self, master, reader, key, **kwargs):
        super().__init__(master, **kwargs)
        promptclass = reader.kvconfig[key]['prompt']
        promptclass(master, reader, reader.kvconfig[key], hull=self)

class Reader:
    
    def __init__(self, path, kvdict=None, kvpickle=None, kvyaml=None):
        if isinstance(path, persist.PersistentDict):
            self.shelf = path
        else:
            self.shelf = persist.PersistentDict(path)
        if isinstance(kvdict, dict):
            self.kvconfig = kvdict
        elif kvpickle:
            self.kvconfig = pickle.load(open(kvpickle, 'rb'))
        elif kvyaml:
            import yaml
            self.kvconfig = yaml.load(open(kvyaml, 'r').read())
        else:
            raise ValueError('No valid form of key/value configuration provided')

        self.bindings = {}
        
        for key in self.kvconfig:
            config = self.kvconfig[key]
            config['key'] = key
            if 'prompt' not in config:
                config['prompt'] = _BasePrompt
                
            if 'default' not in config:
                config['default'] = copy(config['prompt'].__default__)

            self.bindings[key] = []
            if 'handle' in config:
                handle = config['handle']
                self.bind(key, handle)
            
            if key not in self.shelf:
                self.shelf[ key ] = config[ 'default' ]
        
        self.keys = self.kvconfig.keys
    
    def __getitem__(self, attr):
        return self.get(attr)
    
    def __setitem__(self, attr, value):
        self.set(attr, value)
    
    def close(self):
        self.shelf.sync()
        self.shelf.close()
    
    def changed(self, key):
        default = self.kvconfig[ key ][ 'default' ]
        return self.shelf[ key ] != default
    
    def required(self, key):
        try:
            return bool(self.kvconfig[ key ][ 'required' ])
        except KeyError:
            return False
    
    def revert(self, key):
        default = self.kvconfig[key]['default']
        self.set(key, default)
    
    def set(self, key, data, call=True):
        self.shelf[ key ] = data
        self.shelf.sync()
        if call: self.call(key)
        #More deprecated callback shit :V
        """if 'callback' in self.kvconfig[ key ]:
            self.kvconfig[ key ][ 'callback' ].__call__()"""
    
    def get(self, key, call=False):
        if call: self.call(key)
        return self.shelf[ key ]

    def call(self, key):
        for bind in self.bindings[key]:
            bind.__call__()

    def bind(self, key, handle, add=False):
        if isinstance(handle, type):
            handle = lambda: handle()
        if not hasattr(handle, '__call__'):
            raise TypeError('The only valid object for a handle is a function, lambda, or class')

        if add or len(self.bindings[key]) == 0:
            self.bindings[key].append(handle)
        else:
            self.bindings[key][-1] = handle

    def unbind(self, key, all=False):
        if all:
            self.bindings[key] = list()
        elif len(self.bindings[key]) > 0:
            self.bindings[key].pop()

    """def __getitem__(self, attr):
        return self.get(attr)

    def __setitem__(self, attr, value):
        self.set(attr, value)"""

class ManagerFrame(tkinter.ttk.Frame):
    
    def __init__(self, root, reader):
        if not isinstance(reader, Reader):
            raise TypeError('"reader" argument must be instance of Reader class.')

        super().__init__(root)
        
        self.root = root
        self.reader = reader
        self.shelf = reader.shelf
        self.kvconfig = reader.kvconfig
        
        self._setup()
    
    def _setup(self):
        treefrm = tkscroll.ScrolledTree(self, columns=[ 0 ])
        treefrm.pack(expand=True, fill=BOTH)
        self.tree = tree = treefrm.tree
        tree.column('#0', width=125)
        tree.heading('#0', text='Key')
        tree.heading(0, text='Value')
        tree.bind('<Double-Button-1>', self._modify)
        
        hull = tkinter.ttk.Frame(self)
        hull.pack(fill=X)

        tkinter.ttk.Button(hull, text='Modify', compound=LEFT, command=self._modify).pack(side=LEFT, expand=True, fill=X)
        tkinter.ttk.Button(hull, text='Refresh', compound=LEFT, command=self.refresh).pack(side=LEFT, expand=True, fill=X)
        
        self.after(100, self.refresh)
    
    def refresh(self):
        for child in self.tree.get_children():
            self.tree.delete(child)
        
        #keys = [ key[0] for key in self.db.execute('SELECT key FROM tkprop ORDER BY key ASC').fetchall() ]
        keys = list(self.shelf.keys())
        keys.sort()
        for key in keys:
            if key in self.kvconfig:
                leaf = self.tree.insert('', END, text=key, values=[ repr( self.reader.get( key) ).replace('\n', ' '), ] )
                
                '''image = self.pool[ 'i:fugue/status-away.png' ]
                if not self.reader.changed(key):
                    if self.reader.required(key):
                        image=self.pool[ 'i:fugue/status-busy.png' ]
                    else:
                        image=self.pool[ 'i:fugue/status-offline.png' ]'''
                self.tree.item(leaf)#, image=image)
            else:
                del self.shelf[ key ]
    
    def _modify(self, event=None):
        leaf = self.tree.focus()
        if leaf:
            key = self.tree.item(leaf)[ 'text' ]
            config = self.kvconfig[ key ]
            prompt = config[ 'prompt' ]
            prompt( self, self.reader, config).wait_window()
            
            self.refresh()

class ManagerWindow(tkinter.Toplevel):
    def __init__(self, root, reader):
        super().__init__(root)
        self.root = root

        self.manager = ManagerFrame(self, reader)
        self.manager.pack(expand=True, fill=BOTH)

        self.transient(root)
        self.grab_set()
        self.focus_set()

        self.update_idletasks()
        self.minsize(self.winfo_width(), self.winfo_height())
        self.geometry('+{0}+{1}'.format(root.winfo_rootx(), root.winfo_rooty()))

        self.wait_window()

class Modify:
    def __init__(self, root, reader, key):
        if not root:
            root = tkinter.Tk()
            root.title('Property Manager')
            root.withdraw()
        config = reader.kvconfig[ key ]
        prompt = config[ 'prompt' ]
        prompt(root, reader.shelf, config).wait_window()