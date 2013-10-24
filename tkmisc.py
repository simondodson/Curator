import tkinter
import tkinter.ttk
ttk = tkinter.ttk
import tkinter.filedialog
from tkinter.constants import *

import tkscroll

import traceback
import logging
import math
import time

class ProgressRect( tkinter.Toplevel ):
    
    def __init__( self, master ):
        tkinter.Toplevel.__init__( self, master )
        self.transient( master )
        self.resizable( 0, 0 )
        self.fg = '#3399ff'
        self.fghalf = '#99ccff'
        
        self.can = can = tkinter.Canvas( self, width=256, height=256 )
        
        can.pack()
        can.focus_set()
        
        self.dots = dots = []
        circleRad = 110
        dotRad = 3
        dotNum = 40
        #dotRad = 4
        #dotNum = 128
        dotStep = ( 2 * math.pi ) / dotNum
        
        for i in range( dotNum ):
            radian = i * dotStep
            radian -= math.pi / 2.0
            x = math.cos( radian ) * circleRad + 128
            y = math.sin( radian ) * circleRad + 128
            
            x1 = x - dotRad
            y1 = y + dotRad
            x2 = x + dotRad
            y2 = y - dotRad
            dots.append( can.create_oval( x1, y1, x2, y2, outline='#e4e4e4' ) )

        self.dotsfull = 0
        
        #for dot in dots:
        #    can.itemconfig( dot, fill=fg )
        #    self.update()
        #    time.sleep( 0.05 )
        self.text = tkinter.StringVar()
        ent = tkinter.ttk.Entry( self, textvariable=self.text, justify=CENTER, state='readonly', width=30 )
        self.update_idletasks()
        entx = 128 - ent.winfo_reqwidth() / 2
        enty = 128 - ent.winfo_reqheight() / 2
        ent.place( x=entx, y=enty )
        
        self.button_pressed = False
        self.button = but = tkinter.ttk.Button( self, text='Cancel', command=self.button_press )
        butx = 128 - but.winfo_reqwidth() / 2
        buty = 128 + ent.winfo_reqheight() / 2
        but.place( x=butx, y=buty )
        #self.after( 500, self._test )
    
    def button_press( self ):
        self.button_pressed = True
        self.button.config( state=DISABLED )
        
        odd = True
        #for dot in self.dots:
        for i in range(self.dotsfull):
            dot = self.dots[i]
            self.can.itemconfig( dot, fill='#c40233' )        
    
    def set( self, prog ):
        if prog > 100:
            prog -= math.floor( prog / 100 )
        
        if prog is 0:
            self.dotsfull = 0
        else:
            prog /= 100
            self.dotsfull = math.floor( len( self.dots ) * prog ) + 1
        
        for dot in self.dots:
            self.can.itemconfig( dot, fill='' )
        
        for i in range( self.dotsfull ):
            if i is 0:
                self.can.itemconfig( self.dots[0], fill=self.fghalf )
            elif i is len( self.dots ):
                self.can.itemconfig( self.dots[0], fill=self.fg )
            else:
                self.can.itemconfig( self.dots[i], fill=self.fg )
    
    def set_text( self, text ):
        self.text.set( text )

class FreeformDialog( tkinter.Toplevel ):

    def __init__( self, master, config, **kwargs ):
        tkinter.Toplevel.__init__( self, master, **kwargs )
        self.master = master
        self.config = config
        self.transient( master )
        self.resizable( 0, 0 )
        self.grab_set()
        self._setup()
        self.wait_window()

    def _setup( self ):
        self.cancel = True
        self.frame = frame = tkinter.ttk.Frame( self )
        frame.pack( padx=24, pady=24 )
        tkinter.ttk.Separator( frame, orient=VERTICAL ).grid( column=1, row=0, rowspan=len( self.config ), padx=2, sticky='NS' )
        tkinter.ttk.Separator( self, orient=HORIZONTAL ).pack( fill=X, pady=2 )
        tkinter.ttk.Button( self, text='Okay', command=self.submit ).pack( fill=X )
        self.keyvars = keyvars = {}

        for i, data in enumerate( self.config ):
            tkinter.Label( frame, text=data[ 'key' ] + ':' ).grid( column=0, row=i, padx=10, sticky='E' )

            key = data[ 'key' ]
            vtype = data[ 'type' ]
            vdef = data[ 'default' ]

            if vtype is 'option':
                var = tkinter.StringVar()
                tkinter.ttk.OptionMenu( frame, var, vdef, *data[ 'options' ] ).grid( column=2, row=i, sticky='WE' )
                keyvars[ key ] = var

            elif vtype is 'string':
                var = tkinter.StringVar( value=vdef )
                tkinter.ttk.Entry( frame, textvariable=var ).grid( column=2, row=i, sticky='WE' )
                keyvars[ key ] = var

            elif vtype is 'int':
                var = tkinter.IntVar( value=vdef )
                tkinter.ttk.Entry( frame, textvariable=var ).grid( column=2, row=i, sticky='WE' )
                keyvars[ key ] = var

            elif vtype is 'fileopen':
                var = tkinter.StringVar( value=vdef )
                tkinter.ttk.Entry( frame, textvariable=var ).grid( column=2, row=i, sticky='WE' )
                but = tkinter.ttk.Button( frame, text='...' )
                but.grid( column=3, row=i, sticky='WE' )
                but.bind( '<Button>', lambda e: e.widget.var.set( tkinter.filedialog.askopenfilename() ) )
                but.var = var
                keyvars[ key ] = var

            elif vtype is 'filesave':
                var = tkinter.StringVar( value=vdef )
                tkinter.ttk.Entry( frame, textvariable=var ).grid( column=2, row=i, sticky='WE' )
                but = tkinter.ttk.Button( frame, text='...' )
                but.grid( column=3, row=i, sticky='WE' )
                but.bind( '<Button>', lambda e: e.widget.var.set( tkinter.filedialog.asksaveasfilename() ) )
                but.var = var
                keyvars[ key ] = var

            elif vtype is 'directory':
                var = tkinter.StringVar( value=vdef )
                tkinter.ttk.Entry( frame, textvariable=var ).grid( column=2, row=i, sticky='WE' )
                but = tkinter.ttk.Button( frame, text='...' )
                but.grid( column=3, row=i, sticky='WE' )
                but.bind( '<Button>', lambda e: e.widget.var.set( tkinter.filedialog.askdirectory() ) )
                but.var = var
                keyvars[ key ] = var

    def submit( self ):
        self.cancel = False
        self.destroy()

    def get( self ):
        if self.cancel:
            return False

        return { key: self.keyvars[ key ].get() for key in self.keyvars.keys() }

class AdvEntry( tkinter.ttk.Entry ):
    
    def __init__( self, master, ghost='', clearonclick=True, **kwargs ):
        self.ghost = ghost
        self.ghosted = True
        self.coc = clearonclick

        if not 'textvariable' in kwargs:
            self.var = tkinter.StringVar( master )
            kwargs[ 'textvariable' ] = self.var
        kwargs[ 'textvariable' ].set( ghost )
        kwargs[ 'foreground' ] = '#bbbbbb'

        super().__init__( master, **kwargs )
        #self.event_add( '<<Cleared>>', None )
        
        self.var = kwargs[ 'textvariable' ]

        self.bind( '<FocusIn>', self.focusin )
        self.bind( '<FocusOut>', self.focusout )
        self.bind( '<Key>', self.key )
        if self.coc:
            self.bind( '<Double-Button-1>', lambda event: self.var.set( '' ) )
    
    def get( self ):
        if self.var.get() == self.ghost:
            return ''
        else:
            return super().get()

    def focusin( self, event ):
        if self.ghosted:
            self.icursor( 0 )

    def focusout( self, event ):
        if not self.ghosted and self.var.get() == '':
            self.clear()

    def key( self, event ):
        if self.ghosted:
            self.var.set( '' )
            self.config( foreground='#000000' )
            self.ghosted = False

    def clear( self, event=None ):
        self.ghosted = True
        self.var.set( self.ghost )
        self.config( foreground='#bbbbbb' )
        self.icursor( 0 )

class ProgressDialog(tkinter.Toplevel):
    def __init__(self, root, grab=True):
        super().__init__(root)
        self.intvar = tkinter.IntVar()
        self.progressbar = pbar = ttk.Progressbar(self, length=300, variable=self.intvar)
        pbar.pack(expand=True, fill=BOTH)
        self.strvar = tkinter.StringVar()
        self.entry = entry = ttk.Entry(self, textvariable=self.strvar, state=DISABLED, justify=CENTER)
        entry.pack(fill=X)
        self.cancelled = False
        self.button = but = ttk.Button(self, text='Cancel', command=lambda: setattr(self, 'cancelled', True))
        but.pack(fill=X)
        self.bind = but.bind

    def set(self, var):
        if isinstance(var, (int, float)):
            self.intvar.set(int(var))
        elif isinstance(var, str):
            self.strvar.set(var)
        else:
            self.strvar.set(repr(var))

class ButtonDual(ttk.Button):
    def __init__(self, *args, **kwargs):
        self.image = None
        if 'image' in kwargs:
            self.image = kwargs['image']
        if 'image2' in kwargs and self.image:
            self.image2 = kwargs.pop('image2')
        else:
            self.image2 = self.image
        super().__init__(*args, **kwargs)

        if self.image:
            self.bind('<Button>', self.butdown)
            self.bind('<ButtonRelease>', self.butup)

    def butdown(self, event):
        if not self.config('state'):
            self.config(image=self.image2)

    def butup(self, event):
        self.config(image=self.image)

def center(widget, within):
    widget.update_idletasks()
    x = within.winfo_rootx() + (within.winfo_width() - widget.winfo_width()) / 2
    y = within.winfo_rooty() + (within.winfo_height() - widget.winfo_height()) / 2
    widget.geometry('+{0}+{1}'.format(int(x), int(y)))

class MainloopErrorMonitor:
    def __init__(self, master, logfile='./media.log'):
        self.master = master
        logging.basicConfig(filename=logfile)
        master.report_callback_exception = self.error
        master.mainloop()
        #try:
        #    master.mainloop()
        #except:
        #    self.error()

    def error(self, *args):
        errortext = ''.join(traceback.format_exception(*args)) + '\nPlease report repetitive and/or anomalous errors to spgill@vt.edu'
        errortextlines = errortext.split('\n')
        lengths = []
        for line in errortextlines:
            lengths.append(len(line))
        width = max(lengths)
        height = len(errortextlines)
        logging.error(errortext)

        root = tkinter.Toplevel(self.master)
        root.title('Error Encountered')
        root.transient(self.master)
        root.grab_set()
        root.focus_set()

        textbox = tkscroll.ScrolledText(root, width=width, height=height, wrap=None)
        textbox.grid(column=0, columnspan=2, row=0, sticky='WESN')
        textbox.text.insert(0.0, errortext)
        textbox.text.config(state=DISABLED)

        tkinter.ttk.Button(root, text='Close Application', command=self.master.destroy).grid(column=0, row=1, sticky='WE')
        tkinter.ttk.Button(root, text='Continue', command=root.destroy).grid(column=1, row=1, sticky='WE')

        for i in range(2):
            root.columnconfigure(i, weight=1)

        root.rowconfigure(0, weight=1)

        center(root, self.master)
        root.wait_window()

class EntryWithPlaceholder(tkinter.ttk.Entry):
    def __init__(self, *args, **kwargs):
        self.kwargs = {'placeholder': ''}
        self.kwargs.update(kwargs)
        self.phtext = self.kwargs.pop('placeholder')
        self.show = self.kwargs.get('show', '')
        super().__init__(*args, **self.kwargs)
        self.setup()

    def setup(self):
        self.realvar = self.kwargs.get('textvariable', None) or tkinter.StringVar()
        self.hiddenvar = tkinter.StringVar(value=self.phtext)

        if self.realvar.get():
            self.config(show=self.show)
            self.config(textvariable=self.realvar)
            self.config(foreground='#000000')
        else:
            self.config(show='')
            self.config(textvariable=self.hiddenvar)
            self.config(foreground='#AAAAAA')

        self.bind('<FocusIn>', self.focusin)
        self.bind('<FocusOut>', self.focusout)

    def focusin(self, event):
        self.config(show=self.show)
        self.config(textvariable=self.realvar)
        self.config(foreground='#000000')

    def focusout(self, event):
        if not self.realvar.get():
            self.config(show='')
            self.config(textvariable=self.hiddenvar)
            self.config(foreground='#AAAAAA')