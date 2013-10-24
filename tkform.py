import tkinter
import tkinter.ttk
import tkinter.filedialog
from tkinter.constants import *

import yaml

import ppk
import tkmisc

class _BaseField(object):
    default = ''
    stretchy = True
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self._setup()
        self.setup()

    def _setup(self):
        pass

    def setup(self):
        pass

    def get(self):
        return self.var.get()

    def check(self):
        return bool(self.get())

class LabelField(_BaseField):
    stretchy = False
    def setup(self):
        tkinter.ttk.Label(self.root, text=self.config.get('text', '')).pack(expand=True)

    def get(self): return None
    def check(self): return True

class StringField(_BaseField):
    def setup(self):
        self.var = tkinter.StringVar(value=self.config['default'])
        #tkinter.ttk.Entry(self.root, textvariable=self.var).pack(expand=True, fill=BOTH)
        tkmisc.EntryWithPlaceholder(self.root, textvariable=self.var, placeholder=self.config.get('placeholder', '')).pack(expand=True, fill=BOTH)

class PasswordField(_BaseField):
    def setup(self):
        self.var = tkinter.StringVar(value=self.config['default'])
        tkmisc.EntryWithPlaceholder(self.root, textvariable=self.var, placeholder=self.config.get('placeholder', ''), show='*').pack(expand=True, fill=BOTH)

class RadioField(_BaseField):
    default = 0
    def setup(self):
        #print(self.config['default'])
        self.var = tkinter.IntVar(value=self.config['default'])
        self.buttons = []
        for i, option in enumerate(self.config.get('options', list())):
            button = tkinter.ttk.Radiobutton(self.root, text=option, variable=self.var, value=i)
            button.pack(expand=True, fill=BOTH)

    def check(self):
        return True

class CheckField(_BaseField):
    def setup(self):
        defaults = self.config.get('default', None)
        self.vars = []
        for i, option in enumerate(self.config.get('options', list())):
            var = tkinter.BooleanVar()
            self.vars.append(var)
            button = tkinter.ttk.Checkbutton(self.root, text=option, variable=var)
            button.pack(expand=True, fill=BOTH)
            if defaults:
                var.set(bool(defaults[i]))
            else:
                var.set(False)

    def get(self):
        return [bool(var.get()) for var in self.vars]

    def check(self):
        return True

class _FilesystemField(_BaseField):
    _dialog = None
    _text = ''
    def setup(self):
        self.var = tkinter.StringVar(value=self.config['default'])
        tkinter.ttk.Entry(self.root, textvariable=self.var).pack(expand=True, fill=BOTH)
        tkinter.ttk.Button(self.root, text=self._text, command=self.opendialog).pack(fill=X)

    def opendialog(self):
        result = getattr(tkinter.filedialog, self._dialog).__call__(
            parent=self.root
        )
        self.var.set(result)
        self.root.lift()

class FileOpenField(_FilesystemField):
    _dialog = 'askopenfilename'
    _text = 'Choose file to open'

class FileSaveField(_FilesystemField):
    _dialog = 'asksaveasfilename'
    _text = 'Choose file to save'

class DirectoryField(_FilesystemField):
    _dialog = 'askdirectory'
    _text = 'Choose directory'

class Form(tkinter.Toplevel):
    def __init__(self, master, config):
        super().__init__(master)
        self.master = master
        self.config = config
        self.complete = False
        self.cancelled = False
        self.setup()

    def setup(self):
        self.title('Form')
        self.transient(self.master)
        self.grab_set()

        self.fields = []

        for i, field_config in enumerate(self.config):
            config = {
                'label': '',
                'type': StringField,
                'required': False,
            }
            config.update(field_config)

            if isinstance(config['type'], str):
                config['type'] = globals()[config['type']]

            if not 'default' in config:
                config['default'] = config['type'].default

            if config['label']:
                frame = tkinter.LabelFrame(self, text=config['label'])
            else:
                frame = tkinter.Frame(self)

            frame.config(padx=2, pady=2)
            frame.grid(column=0, row=i, columnspan=2, sticky='NESW', padx=1, pady=1)

            field = config['type'](frame, config)
            self.fields.append(field)

            if field.stretchy:
                self.grid_rowconfigure(i, weight=1)

        for i in range(2):
            self.grid_columnconfigure(i, weight=1)

        tkinter.ttk.Button(self, text='Confirm', command=self.confirm).grid(column=0, row=len(self.config), sticky='WE')
        tkinter.ttk.Button(self, text='Cancel', command=self.cancel).grid(column=1, row=len(self.config), sticky='WE')

        self.geometry('+{0}+{1}'.format( self.master.winfo_rootx(), self.master.winfo_rooty()) )
        self.update()
        self.minsize(self.winfo_width(), self.winfo_height())

    def confirm(self):
        fail = False
        for field in self.fields:
            print(field, field.check(), field.config['required'])
            if field.config['required'] and not field.check():
                field.root.config(background='#C40233')
                fail = True
            else:
                field.root.config(background='SystemButtonFace')
        if fail: return
        self.complete = True
        self.destroy()

    def cancel(self):
        self.cancelled = True
        self.complete = True
        self.destroy()

    def get(self):
        return [field.get() for field in self.fields]

def form(master, config):
    root = Form(master, config)
    root.wait_window()
    return root.get()

def formtest(master):
    config = yaml.dump([
        {
            'type': LabelField,
            'text': 'Please login below'
        },
        {
            'type': StringField,
            'placeholder': 'Username / Email',
            'required': True
        },
        {
            'type': PasswordField,
            'placeholder': 'PasswordField',
            'required': True
        },
        {
            'type': CheckField,
            'options': [
                'Remember me?',
            ]
        },
        {
            'type': FileOpenField,
            'required': True
        },
        {
            'type': FileSaveField,
            'required': True
        },
        {
            'type': DirectoryField,
            'required': True
        },
    ])
    testobj = form(master, config)
    print('FORMOUTPUT', testobj)