import tkinter
import tkinter.ttk
from tkinter.constants import *

class ScrolledListbox( tkinter.ttk.Frame ):
    
    def __init__( self, master, **kwargs ):
        tkinter.ttk.Frame.__init__( self, master )
        
        scrollbar = tkinter.ttk.Scrollbar( self, orient=VERTICAL )
        self.listbox = listbox = tkinter.Listbox( self, yscrollcommand=scrollbar.set, **kwargs )
        scrollbar.config( command=listbox.yview )
        scrollbar.pack( side=RIGHT, fill=Y )
        listbox.pack( side=LEFT, fill=BOTH, expand=1 )

class ScrolledTree( tkinter.ttk.Frame ):
    
    def __init__( self, master, **kwargs ):
        #tkinter.ttk.Frame.__init__( self, master )
        super().__init__(master)
        
        scrollbar = tkinter.ttk.Scrollbar( self, orient=VERTICAL )
        self.tree = tree = tkinter.ttk.Treeview( self, yscrollcommand=scrollbar.set, **kwargs )
        scrollbar.config( command=tree.yview )
        scrollbar.pack( side=RIGHT, fill=Y )
        tree.pack( side=LEFT, fill=BOTH, expand=1 )

class ScrolledText( tkinter.ttk.Frame ):
    
    def __init__( self, master, **kwargs ):
        tkinter.ttk.Frame.__init__( self, master )
        top = tkinter.ttk.Frame( self )
        btm = tkinter.ttk.Frame( self )
        top.pack( expand=True, fill=BOTH )
        btm.pack( fill=X )
        
        self.xscroll = xscroll = tkinter.ttk.Scrollbar( btm, orient=HORIZONTAL )
        self.yscroll = yscroll = tkinter.ttk.Scrollbar( top, orient=VERTICAL )
        self.text = text = tkinter.Text( top, yscrollcommand=yscroll.set, xscrollcommand=xscroll.set, **kwargs )
        xscroll.config( command=text.xview )
        yscroll.config( command=text.yview )
        #text.grid( column=0, row=0, sticky='NESW' )
        #yscroll.grid( column=1, row=0, sticky='NS' )
        #xscroll.grid( column=0, row=1, sticky='WE' )
        text.pack( side=LEFT, expand=True, fill=BOTH )
        yscroll.pack( side=LEFT, fill=Y )
        xscroll.pack( side=LEFT, expand=True, fill=X )
        grip = tkinter.ttk.Sizegrip(btm)
        grip.pack(side=LEFT)