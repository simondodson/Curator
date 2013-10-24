import tkinter
import tkinter.ttk
from tkinter.constants import *
import tkinter.font
import tkinter.filedialog
import tkinter.messagebox

from threading import Thread
from subprocess import Popen
import webbrowser
import argparse
import datetime
import platform
import sqlite3
import atexit
import shelve
import time
import uuid
import yaml
import sys
import os
import re

import ppk
import tkprops
import tkscroll
import tkmisc
import media_tools
import tooltip

import num2engl
import persist

import bottle
from bottle_renderer import RendererPlugin
from bottle_sqlalchemy import SQLAlchemyPlugin

import media_db
from media_db import Base, Series, Episode, Movie
import sqlalchemy

class Menu( tkinter.Tk ):
    
    def __init__( self, enterloop=True ):
        super().__init__()
        
        #parser = argparse.ArgumentParser( add_help=False )
        #parser.add_argument( '--local', '-l', action='store_true', default=False )
        #args = parser.parse_args()
        #
        #self.dbLocal = args.local
        
        self._setup()
        self.bottle_init()
        if enterloop:
            self.mainloop()

    def destroy( self ):
        try:
            self.lastp.close()
            self.props.close()
            self.db.commit()
        except: pass
        super().destroy()
    
    def _setup( self ):
        self.title( 'Media' )
        
        self.pool = pool = ppk.Pool()
        pool.include()

        self.iconphoto(True, pool['i:/media/play_alt_2.png'])
        #self.tk.call('wm', 'iconphoto', self._w, pool[ 'i:/media/play_alt_2.png' ], default=True)

        base = os.path.expanduser( '~/.media' )
        if not os.path.isdir( base ):
            os.mkdir( base )
            
        self.propsFile = os.path.join( base, 'props' )
        self.lastpFile = os.path.join( base, 'lastp' )
        
        self.db = media_db.Session()
        
        self.props = tkprops.Reader( self.propsFile, yaml.load( pool[ 'media/props.yaml' ] ) )
        
        self.lastp = persist.PersistentDict( self.lastpFile )
        self.leaves = dict()
        
        self.treefrm = tkscroll.ScrolledTree( self, columns=[0], height=20 )
        self.treefrm.pack(side=LEFT, expand=True, fill=BOTH)
        self.tree = tree = self.treefrm.tree
        
        tree.column( '#0', width=250 )
        tree.column( 0, width=100 )
        tree.heading( '#0', text='Title / Season' )
        tree.heading( 0, text='Tag' )
        
        tree.tag_configure('file', image=self.pool['i:media/movie_16x16.png'])
        tree.tag_configure( 'stripe', background='#f2f5f9' ) #f4f4f4
        tree.tag_configure( 'last', foreground='#eb6901' )

        tree.bind('<<TreeviewSelect>>', self.imdb_check)
        
        panel = tkinter.ttk.Frame(self)
        panel.pack(side=LEFT, fill=Y, ipadx=16, ipady=32)
        
        style = tkinter.ttk.Style()
        style.configure('center.Toolbutton', anchor=CENTER)
        def button(**kwargs):
            
            kwargs['style'] = 'center.Toolbutton'
            but = tkmisc.ButtonDual(panel, **kwargs)
            but.pack(expand=True, fill=BOTH, ipady=8)
            
            if 'text' in kwargs:
                tip = tooltip.ToolTip(but, text=kwargs['text'], delay=500)

            return but
        
        button(image=self.pool['i:media/spin.png'], image2=self.pool['i:media/spin_2.png'], command=self.rebuild, text='Rebuild cache and reload list')

        button(image=self.pool['i:media/cog.png'], image2=self.pool['i:media/cog_2.png'], command=lambda: tkprops.ManagerWindow( self, self.props ), text='Application properties')
        
        listbut = button(image=self.pool['i:media/list.png'], image2=self.pool['i:media/list_2.png'], text='Manage indices')
        rmenu = tkinter.Menu(self, tearoff=False)
        rmenu.add_command(label='New')
        listbut.bind('<Button-3>', lambda e: rmenu.post(e.x_root, e.y_root))
        
        self.play_button = button(image=self.pool['i:media/play_alt_2.png'], command=self.play, text='Play selected file(s)')
        
        button(image=self.pool['i:media/document_alt_stroke.png'], image2=self.pool['i:media/document_alt_stroke_2.png'], command=self.copy, text='Copy selected file(s)')

        button(image=self.pool['i:media/folder_fill.png'], image2=self.pool['i:media/folder_fill_2.png'], command=self.show, text='Show in file manager')

        self.imdb_button = button(image=self.pool['i:media/imdb.png'], image2=self.pool['i:media/imdb_2.png'], command=self.imdb, text='Open IMDb page', state=DISABLED)
        
        self.update_idletasks()
        self.minsize(self.winfo_width(), self.winfo_height())
        
        
        if self.props.get( 'first' ):
            self.after( 200, self.rebuild )
            self.props.set( 'first', False )
            
            tries = [
                os.path.join(os.environ['PROGRAMFILES'], 'VideoLAN', 'VLC', 'vlc.exe') #Default install location for Windows
            ]
            
            for path in tries:
                if os.path.isfile(path):
                    self.props.set('vlc-path', path)
            
        else:
            self.after( 100, self.refresh, self.db )

    def bottle_init(self):
        app = bottle.Bottle()
        app.install(RendererPlugin())
        app.install(SQLAlchemyPlugin(
            media_db.engine,
            media_db.Base.metadata,
            create=True,
            keyword='db'
        ))

        self.session = uuid.uuid4().hex

        def locked():
            cookie = bottle.request.get_cookie('HT-MEDIA-SESSION', default='')
            if cookie != self.session:
                bottle.redirect('/media/unlock')

        @app.get('/favicon.ico')
        def favicon():
            #return bottle.static_file('film.png', '')
            bottle.response.content_type = 'image/png'
            return self.pool[ 'r:/media/play_alt_2.png' ]

        @app.get( '/media/static/<path:path>' )
        def static( path ):
            return bottle.static_file( path, 'static' )

        @app.get('/media', renderer='index.stpl')
        def index(db):
            locked()
            tag = bottle.request.query.tag
            return {
                'download': bottle.request.query.download,
                'max': sqlalchemy.func.max,
                'db': db,
                'Series': Series,
                'Episode': Episode,
                'Movie': Movie,
                'tag': tag,
                'bottle': bottle
            }

        @app.get('/media/unlock', renderer='unlock.stpl')
        def unlock_GET():
            pass

        @app.post('/media/unlock')
        def unlock_POST():
            code = bottle.request.forms.code
            print('CODE', code, 'CORRECT', self.props['server-unlock'], 'EQUAL?', code.encode() == self.props['server-unlock'].encode())
            if code.encode() == self.props['server-unlock'].encode():
                bottle.response.set_cookie('HT-MEDIA-SESSION', self.session, path='/')
                return [None,]
            else:
                return bottle.HTTPError(403)
        
        @app.route('/media/lock')
        def lock():
            bottle.response.delete_cookie('HT-MEDIA-SESSION')
            return [None,]

        @app.get('/media/stream')
        def stream():
            locked()
            query = bottle.request.query
            db = media_db.Session()
            if query.tag:
                episode = db.query(Episode).filter(Episode.tag == query.tag).first()
                title = episode.title
                path = episode.path
            elif query.id:
                movie = db.query(Movie).filter(Movie.id == query.id).first()
                title = movie.title
                path = movie.path
            else:
                return bottle.HTTPError(404, 'Invalid query')
            self.play(files=[path,])
            return ''

        thread = Thread(
            target = lambda: app.run(host='0.0.0.0', port=self.props['server-port'], server='rocket')
        )
        thread.daemon = True
        if self.props['server-enabled']:
            thread.start()
    
    def checkProps( self ):
        if not self.props.changed('vlc-path'):
            cont = tkinter.messagebox.askyesno(
                'Missing path',
                'The property "vlc-path" is not currently defined; it is required to play media files. Define it now?'
            )
            if cont:
                tkprops.Modify( self, self.props, 'vlc-path' )
    
    def rebuild( self, refresh=True ):
        root = tkinter.Toplevel( self )
        root.title( 'Rebuilding...' )
        root.resizable( 0, 0 )
        root.transient( self )
        root.grab_set()
        
        root.geometry( '+{0}+{1}'.format( self.winfo_rootx(), self.winfo_rooty() ) )
        
        treefrm = tkscroll.ScrolledTree( root, height=15 )
        treefrm.pack()
        tree = treefrm.tree
        tree.column( '#0', width=400 )
        tree.focus_set()
        
        tree.tag_configure( 'file', foreground='#333355' )
        
        for table in reversed( Base.metadata.sorted_tables ):
            self.db.execute( table.delete() )
        self.db.commit()
        
        pattern = re.compile( self.props.get( 'pattern-episodic' ) )
        pattern2 = re.compile( self.props.get( 'pattern-loose' ) )
        entryid = 0
        
        for basedir in self.props.get( 'directories' ):
            
            basedir = os.path.abspath( basedir )
            
            if not os.path.isdir( basedir ): continue
            for subdir in os.listdir( basedir ):
                
                subdir = os.fsdecode( os.path.join( basedir, subdir ) )
                datafile = os.path.join( subdir, 'media.yaml' )
                
                if os.path.isfile( datafile ):
                    
                    dataentry = tree.insert( '', 0, text=datafile )
                    root.update_idletasks()
                    
                    data = yaml.load( open( datafile, 'rb' ).read() )
                    extensions = tuple( self.props.get( 'extensions' ) )
                    
                    
                    #Parsing tv series';
                    if 'series' in data and self.props.get( 'collect-series' ):
                        for series in data[ 'series' ]:
                            if 'dir' in series:
                                serdir = os.path.join( subdir, series[ 'dir' ] )
                            else:
                                serdir = subdir
                            title = series[ 'title' ]
                            tag = series[ 'tag' ]
                            epientry = tree.insert( dataentry, END, text=tag + ' ' + title )
                            #self.db.execute( 'INSERT INTO series VALUES( ?, ?, ?, ? )', ( entryid, title, tag, yaml.dump( series ) ) )
                            srecord = Series( item='', tag=tag, title=title, imdb=series.get('imdb', '') )
                            srecord.episodes = []
                            loosei = 0
                            
                            for ( dpath, dnames, fnames ) in os.walk( str( serdir ) ):
                                for fname in fnames:
                                    if fname.endswith( extensions ):
                                        fpath = os.path.join( dpath, fname )
                                        match = pattern.match( fname )
                                        if match is not None:
                                            #epititle = match.group( 5 ) or 'Episode {0}'.format( match.group( 4 ) )
                                            epititle = match.group( 5 ) or 'Episode {0}'.format( ' '.join(num2engl.num2words(int(match.group(4)))).capitalize() )
                                            #self.db.execute( 'INSERT INTO episode VALUES( ?, ?, ?, ? )', ( entryid, epititle, match.group( 1 ), fpath ) )
                                            erecord = Episode( tag=match.group(1), title=epititle, path=fpath, season=int( match.group( 3 ) ) )
                                            srecord.episodes.append( erecord )
                                            self.db.add( erecord )
                                        elif self.props.get( 'collect-loose' ):
                                            match = pattern2.match( fname )
                                            if match and match.group( 1 ) == tag:
                                                fname = pattern2.sub( '', fname )
                                                tree.insert( epientry, END, text=fname, tags=[ 'file' ] )
                                                #self.db.execute( 'INSERT INTO episode VALUES( ?, ?, ?, ? )', ( entryid, fname, tag, fpath ) )
                                                loosetag = '{0}..{1:0>2} {2}'.format( tag, loosei, fname )
                                                erecord = Episode( tag=loosetag, title=fname, path=fpath, season=-1 )
                                                srecord.episodes.append( erecord )
                                                self.db.add( erecord )
                                                print( fname )
                                                loosei += 1
                                        root.update_idletasks()
                            
                            self.db.add( srecord )
                            root.update()
                    
                    #Parsing secondary files;
                    if 'file' in data and self.props.get( 'collect-files' ):
                        for f in data[ 'file' ]:
                            title = f[ 'title' ]
                            tree.insert( dataentry, END, text=title, tags=[ 'file' ] )
                            fpath = os.path.abspath( os.path.join( subdir, f[ 'file' ] ) )
                            #self.db.execute( 'INSERT INTO file VALUES( ?, ?, ?, ? )', ( entryid, title, fpath, yaml.dump( f ) ) )
                            self.db.add( Movie( title=title, path=fpath, imdb=f.get('imdb', '') ) )
                            root.update_idletasks()
                        root.update()
                    
                    self.update()
        
        self.db.commit()
        #print self.db.execute( r'SELECT title FROM episode WHERE tag LIKE ? AND NOT tag=? ORDER BY tag', ( 'TST%', 'TST' ) ).fetchall()
        tree.insert( '', 0, text='Done!' )
        #self.after( 1500, root.destroy )
        #root.wait_window()
        self.after( 100, self.refresh, self.db )
    
    def refresh( self, db=None ):
        for child in self.tree.get_children():
            self.tree.delete( child )
        
        pattern = re.compile( self.props.get( 'pattern-episodic' ) )
        #seriess =  db.execute( 'SELECT title, tag, data, id FROM series ORDER BY title ASC' ).fetchall()
        
        for series in self.db.query( Series ).order_by( Series.title ):
            if not series.tag in self.lastp:
                self.lastp[ series.tag ] = []
            lastp = self.lastp[ series.tag ]

            serentry = self.tree.insert( '', END, text=series.title, values=[ series.tag, ] )
            self.leaves[serentry] = series.tag
            #series.item = serentry
            seaentries = {}
            #episodes = db.execute( 'SELECT title, tag, id FROM episode WHERE tag LIKE ? AND NOT tag=? ORDER BY tag ASC', ( tag + '%', tag ) ).fetchall()
            for episode in self.db.query( Episode ).filter( Episode.series == series.tag ).order_by( Episode.tag ):
                tags = [ 'episode', ]
                
                if episode.season > 0:
                    #epimatch = pattern.match( episode.title )
                    #episea = epimatch.group( 3 )
                    episea = episode.season
                    if episea in seaentries:
                        seaentry = seaentries[ episea ]
                    else:
                        seatag = '{0}{1:0>2}'.format( episode.series, episea )
                        seaentry = self.tree.insert( serentry, END, text='Season {0}'.format( episea ), values=[ seatag, ] )
                        seaentries[ episea ] = seaentry
                        #self.update_idletasks()
    
                    #self.tree.insert( seaentry, END, text=str( episode[0] ), values=[ episode[1], episode[2] ], tags=tags )
                    if episode.tag in lastp:
                        self.tree.item( seaentry, tags=[ 'last', ] )
                        tags.append( 'last' )
                    
                    epientry = self.tree.insert( seaentry, END, text=episode.title, values=[ episode.tag ], tags=tags )
                    #episode.item = epientry
                    self.leaves[epientry] = episode.tag
                elif episode.season == 0:
                    tags.append('file')
                    entry = self.tree.insert( serentry, END, text=episode.title, values=[ episode.tag ], tags=tags )
                    #episode.item = entry
                    self.leaves[entry] = episode.tag
                    #entry = self.tree.insert( serentry, END, text=episode.title, values=[ episode.tag, ], tags=[ 'episode' ], image=self.pool[ 'i:fugue/film.png' ] )
            
            #files = db.execute( 'SELECT title, id FROM episode WHERE tag=? ORDER BY title DESC', ( tag, ) ).fetchall()
            #for f in files:
            self.update()
        
        #files = db.execute( 'SELECT title, id FROM file ORDER BY title ASC' ).fetchall()
        #for f in files:
        for movie in self.db.query( Movie ).order_by( Movie.title ):
            #self.tree.insert( '', END, text=f[0], values=[ '', f[1] ], tags=[ 'file', ], image=self.pool[ 'i:fugue/film.png' ] )
            entry = self.tree.insert( '', END, text=movie.title, tags=[ 'file', ] )
            #movie.item = entry
            self.leaves[entry] = movie.id
            #self.update()
        
        #self.db.commit()
        
        self.stripeChildren( '' )
    
    def stripeChildren( self, master, odd=True ):
        #return
        for item in self.tree.get_children( master ):
            tags = self.tree.item( item )[ 'tags' ]
            if odd:
                if not tags: tags = []
                tags.append( 'stripe' )
                self.tree.item( item, tags=tags )
            odd = not odd
            self.stripeChildren( item, odd )
    
    def setLastp( self, tags ):
        db = media_db.Session()
        ileaves = {v:k for k, v in self.leaves.items()}
        series = {}
        for tag in tags:
            #tag = self.leaves.get(item, None)
            if not tag in tags: continue
            item = ileaves[tag]
            record = db.query( Episode ).filter_by( tag = tag ).first()
            if record is None:
                continue
            base = record.series
            if not base in series:
                series[ base ] = []
            series[ base ].append( (record, item) )
        
        for ( sertag, records ) in series.items():
            
            lastp = self.lastp[ sertag ]
            
            for tag in lastp:
                item = ileaves[tag]
                tags = set( self.tree.item( item )[ 'tags' ] or [] )
                if 'last' in tags:
                    tags.remove( 'last' )
                    self.tree.item( item, tags=list( tags ) )
                
                pitem = self.tree.parent( item )
                tags = set( self.tree.item( pitem )[ 'tags' ] or [] )
                if 'last' in tags:
                    tags.remove( 'last' )
                    self.tree.item( pitem, tags=list( tags ) )
            
            lastp = []
            
            for (record, item) in records:
                tags = self.tree.item( item )[ 'tags' ] or []
                if not 'last' in tags:
                    tags.append( 'last' )
                    self.tree.item( item, tags=tags )
                
                pitem = self.tree.parent( item )
                tags = self.tree.item( pitem )[ 'tags' ] or []
                if not 'last' in tags:
                    tags.append( 'last' )
                    self.tree.item( pitem, tags=tags )
                
                lastp.append( record.tag )
            
            self.lastp[ sertag ] = lastp
        self.lastp.sync()
    
    def getFiles( self, files=False, tags=False, items=False ):
        retfiles = []
        rettags = []
        retitems = []
        db = media_db.Session()
        
        for item in self.tree.selection():
            tag = self.leaves.get(item, None)
            record = None
            if isinstance(tag, str):
                record = db.query( Episode ).filter( Episode.tag == tag ).first()
            elif isinstance(tag, int):
                record = db.query( Movie ).filter( Movie.id == tag ).first()
            if not record: continue
            retfiles.append( record.path )
            rettags.append( tag )
            retitems.append(item)
            
        if files:
            return retfiles
        if tags:
            return rettags
        if items:
            return retitems
    
    def play( self, files=None ):
        if not self.props.changed( 'vlc-path' ):
            tkinter.messagebox.showerror( 'Missing property!', 'There is no defined path to VLC in the properties manager.' )
            return
        
        #self.setLastp( self.getFiles(tags=True) )
        #return
        db = media_db.Session()
        #print('EXTERNAL_REQUEST?', bool(files))
        files = files or self.getFiles(files=True)
        if not files:
            #tkinter.messagebox.showerror('Selection Error!', 'You haven\'t an files selected to play')
            return
        #print('FILES', files)
        tags = [ obj[0] for obj in db.query(Episode.tag).filter(Episode.path.in_(files)).all() ]
        #print('TAGS', tags)
        self.setLastp(tags)

        if files:            
            method = self.props.get( 'vlc-method' )
            if method == 0:
                args = [ self.props.get( 'vlc-path' ), ] + self.props.get( 'vlc-args' ) + files
                self.play_button.config(state=DISABLED)
                Popen( args )
                self.play_button.config(state=NORMAL)
    
    def _copyBlind( self, files ):
        
        prog = tkmisc.ProgressDialog(self)
        
        for i, ( src, dest ) in enumerate( files ):
            
            if prog.cancelled:
                break
            
            prog.set( 0 )
            prog.set( 'File {0} of {1}'.format( i + 1, len( files ) ) )
            
            fsrc = None
            fdst = None
            keepGoing = False
            max = os.stat( src ).st_size
            
            try:
                fsrc = open( src, 'rb' )
                fdst = open( dest, 'wb' )
                keepGoing = True
                count = 0
                
                while keepGoing:
                    buf = fsrc.read( 2**20 )
                    if not buf:
                        break
                    fdst.write( buf )
                    count += len( buf )
                    p = float( count ) / float( max )
                    #prog.set( p * 100.0 )
                    prog.set( p * 100 )
                    self.update()
                    
                    if prog.cancelled:
                        break
                    #top.update()
                #top.destroy()
            finally:
                if fdst:
                    fdst.close()
                if fsrc:
                    fsrc.close()
        
        if prog.cancelled:
            prog.set( 'Operation cancelled' )
            for src, dest in files:
                if os.path.isfile( dest ):
                    os.remove( dest )
        else:
            prog.set( 'Done!' )
            prog.button.config( state=DISABLED )
    
    def copy( self ):
        method = self.props.get( 'copy-method' )
        srcfiles = self.getFiles(True)
        files = []
        if srcfiles:
            preserve = self.props['copy-preserve']
            if preserve == 0:
                preserve = tkinter.messagebox.askokcancel('Media', 'Would you like to preserve the directory structure of the files you are copying?\n(Useful for transferring files to another computer using this program)')
            elif preserve == 1:
                preserve = False
            elif preserve == 2:
                preserve = True
            outdir = tkinter.filedialog.askdirectory()
            if outdir:
                for srcfile in srcfiles:
                    name = os.path.basename( srcfile )
                    src = os.path.normpath( srcfile )
                    dest = os.path.normpath( os.path.join( outdir, name ) )
                    files.append( ( src, dest ) )
                
                if method is 0:
                    system = platform.system()
                    if system is 'Windows':
                        try:
                            from win32com.shell import shell, shellcon
                        except ImportError:
                            tkinter.messagebox.showerror( 'Missing Module!', 'In order to make use of this feature, you must have the "pywin32" package installed. It can be obtained via the project\'s Sourceforge page.' )
                            return
                        
                        srcstr = chr( 0 ).join( [ file[0] for file in files ] )
                        deststr = chr( 0 ).join( [ file[1] for file in files ] )
                        Thread(
                            target=lambda: shell.SHFileOperation(
                                ( 0, shellcon.FO_COPY, srcstr, deststr, shellcon.FOF_MULTIDESTFILES, None, None )
                            )
                        ).start()
                    else:
                        tkinter.messagebox.showerror( 'Not Implemented!', 'The shell copy method is not implemented on your platform!' )
                
                elif method is 1:
                    
                    if platform.system() is not 'Windows':
                        tkinter.messagebox.showerror(
                            'Not Implemented!',
                            'The TeraCopy method is only implemented on Windows! (Which is not your current platform)'
                        )
                        return
                    
                    if not os.path.isfile( 'TeraCopy.exe' ):
                        tkinter.messagebox.showerror(
                            'Missing Executable!',
                            'In order to use TeraCopy for copying files, the TeraCopy executable must be present in the current working directory. ("TeraCopy.exe")',
                        )
                        return
                    
                    listpath = os.path.join( os.getcwd(), 'media--teracopylist.txt' )
                    listout = '\n'.join( [ file[0] for file in files ] )
                    with open( listpath, 'w' ) as listfile:
                        listfile.write( listout )
                    
                    args = [
                        'TeraCopy.exe',
                        'Copy',
                        '*"{0}"'.format( listpath ),
                        outdir,
                    ]
                    
                    Popen( args )
                
                elif method is 2:
                    self._copyBlind( files )
    
    def show( self ):
        files = self.getFiles(True)
        if files:
            system = platform.system()
            if system is 'Windows':
                os.system( 'explorer.exe /select,{0}'.format( files[0] ) )
            elif system is 'Mac':
                os.system( 'open -R "{0}"'.format( files[0] ) )
            elif system is 'Linux':
                os.system( 'xdg-open "{0}"'.format( os.path.dirname( files[0] ) ) )
                #In order to be cross-platform and all that jazz, I'm using xdg-open.
                #This command can't actually highlight the file like Mac and Windows can,
                #but it can open the directory where the file resides (theoretically)
            else:
                tkinter.messagebox.showerror( 'Not Implemented!', 'The functionality is not implemented on your platform!' )

    def imdb_check(self, event=None):
        item = self.tree.focus()
        tag = self.leaves.get(item, None)
        if isinstance(tag, int):
            movie = self.db.query(Movie).filter(Movie.id == tag).first()
            if movie and movie.imdb:
                self.imdb_button.config(state=NORMAL)
                return
        while True:
            if item == '': break
            parent = self.tree.parent(item)
            if parent == '':
                break
            item = parent
        tag = self.tree.item(item)['values'][0]
        series = self.db.query(Series).filter(Series.tag == tag).first()
        if series and series.imdb:
            self.imdb_button.config(state=NORMAL)
            return
        self.imdb_button.config(state=DISABLED)

    def imdb(self):
        item = self.tree.focus()
        tag = self.leaves.get(item, None)
        if isinstance(tag, int):
            movie = self.db.query(Movie).filter(Movie.id == tag).first()
            if movie and movie.imdb:
                webbrowser.open_new_tab('http://www.imdb.com/title/' + movie.imdb)
                return
        while True:
            if item == '': break
            parent = self.tree.parent(item)
            if parent == '':
                break
            item = parent
        tag = self.tree.item(item)['values'][0]
        series = self.db.query(Series).filter(Series.tag == tag).first()
        if series and series.imdb:
            webbrowser.open_new_tab('http://www.imdb.com/title/' + series.imdb)

if __name__ == '__main__': Menu()
