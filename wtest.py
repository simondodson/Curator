import tkinter
import tkinter.ttk
from tkinter.constants import *

import yaml

import ppk
import tkprops

class Main(tkinter.Tk):
    def __init__(self):
        super().__init__()
        self.title('Widget testing')
        self.setup()
        self.mainloop()

    def setup(self):
        self.pool = pool = ppk.Pool(True)
        pool.include()

        self.props = reader = tkprops.Reader('wtest.props', yaml.load(open('./media~/props.yaml', 'r').read()) )

        but = tkinter.ttk.Button(self, image=pool['i:iconic/blue/cog_32x32.png'])
        but.pack(fill=X)
        but.bind('<Button>', lambda e: tkprops.ManagerWindow(self, reader))

        w = tkprops.Widget(self, reader, 'directories')
        w.pack(expand=True, fill=BOTH)

if __name__ == '__main__':
    Main()