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

import media_db
from media_db import Base, Series, Episode, Movie

class Menu( tkinter.Tk ):
    
    def __init__( self, enterloop=True ):
        super().__init__()
        
        #parser = argparse.ArgumentParser( add_help=False )
        #parser.add_argument( '--local', '-l', action='store_true', default=False )
        #args = parser.parse_args()
        #
        #self.dbLocal = args.local
        
        self._setup()
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
        self.title( 'Media Menu' )
        
        self.resizable( 0, 0 )
        
        self.pool = pool = ppk.Pool()
        #pool.load( 'fugue.ppk' )
        #pool.load( 'media.ppk' )
        pool.include()
        
        self.tk.call('wm', 'iconphoto', self._w, pool[ 'i:/media/icon.png' ])
        
        #self.dbFile = os.path.expanduser( '~/media.db' )
        base = os.path.expanduser( '~/.media' )
        if not os.path.isdir( base ):
            os.mkdir( base )
            
        self.propsFile = os.path.join( base, 'props' )
        self.lastpFile = os.path.join( base, 'lastp' )
        
        self.db = media_db.Session()
        #self.db = sqlite3.connect( self.dbFile )
        #self.db.execute( 'CREATE TABLE IF NOT EXISTS series( id INTEGER, title TEXT, tag TEXT, data TEXT )' )
        #self.db.execute( 'CREATE TABLE IF NOT EXISTS episode( id INTEGER, title TEXT, tag TEXT, file TEXT )' )
        #self.db.execute( 'CREATE TABLE IF NOT EXISTS file( id INTEGER, title TEXT, file TEXT, data TEXT )' )
        
        #Loading the properties template, and then loading the template into the propertiy engine
        """try: self.propsTemplate = yaml.load( open( 'media.conf', 'r' ).read() )
        except IOError:
            self.withdraw()
            tkinter.messagebox.askokcancel( 'Error', 'Properties configuration file is missing; it is required to continue operation, so please find a replacement.' )
            sys.exit()
        self.props = tkprops.Reader( self.db, self.propsTemplate )"""
        #self.props = tkprops.Reader( self.db, yaml.load( pool[ 'media/props.yaml' ] ) )
        self.props = tkprops.Reader( self.propsFile, yaml.load( pool[ 'media/props.yaml' ] ) )
        self.after( 1000, self.checkProps )
        
        #self.lastp = shelve.open( self.shelfFile )
        self.lastp = persist.PersistentDict( self.lastpFile )
        
        #self.searchvar = tkinter.StringVar( self )
        #self.searchent = tkmisc.AdvEntry( self, ghost='Search' )
        #self.searchent.bind( '<Key>', lambda event: self.search(), '+' )
        #self.searchent.bind( '<Escape>', lambda event: event.widget.clear() )
        #def check( *args ):
        #    if self.searchent.get() == '':
        #        self.refresh()
        #    else:
        #        self.search()
        #self.searchent.var.trace( 'w', check )
        #self.searchent.grid( column=0, row=0, sticky='WE' )

        #tooltip.ToolTip( self.searchent, text='Search episodes, files, and their tags. Enter text then press return to search. Searches with regular expression patterns, so be wary of special characters.', delay=500 )

        self.treefrm = tkscroll.ScrolledTree( self, columns=[0], height=20 )
        self.treefrm.grid( column=0, row=0, rowspan=2, sticky='NWS' )
        self.tree = tree = self.treefrm.tree
        
        tree.column( '#0', width=250 )
        tree.column( 0, width=100 )
        tree.heading( '#0', text='Title / Season' )
        tree.heading( 0, text='Tag' )
        
        #tree.tag_configure( 'file', foreground='#3399ff' )
        tree.tag_configure( 'file', foreground='#333355' )
        tree.tag_configure( 'stripe', background='#f2f5f9' ) #f4f4f4
        #tree.tag_configure( 'last', foreground='#33aa33' )
        tree.tag_configure( 'last', foreground='#eb6901' )
        
        #Initializing notebook and notebook tabs
        self.noteb = noteb = tkinter.ttk.Notebook( self )
        noteb.grid( column=1, row=0, rowspan=2, padx=10, pady=5, sticky='WESN' )
        self.pages = pages = []
        for i in range( 2 ):
            outer = tkinter.ttk.Frame( self )
            self.pages.append( outer )

        noteb.add( pages[0], sticky='WESN', text='Controls' )
        noteb.add( pages[1], sticky='WESN', text='Misc' )

        #Configuring notebook tab content
        page = self.pages[0]

        logo = tkinter.ttk.Label( page, image=self.pool[ 'i:media/ht.png' ] )
        logo.pack( pady=20, anchor=CENTER )
        logo.bind( '<Button>', lambda e: webbrowser.open_new( 'http://halktek.appspot.com/' ) )

        inner = tkinter.ttk.Frame( page )
        inner.pack( padx=5, pady=10 )
        #tkinter.ttk.Label( inner, image=self.pool.open( 'media--ht.png' ) )

        tkinter.ttk.Separator( inner, orient=VERTICAL ).grid( column=1, row=0, rowspan=99, padx=10, sticky='NS' )
        
        self.i = 0
        def button( image, text, command, **kw ):
            tkinter.ttk.Label( inner, image=image, **kw ).grid( column=0, row=self.i )
            tkinter.ttk.Button( inner, text=text, command=command, **kw ).grid( column=2, row=self.i, ipady=4, sticky='WE' )
            self.i += 1
        
        def spacer():
            tkinter.ttk.Label( inner, image=self.pool[ 'i:media/spacer.png' ] ).grid( column=0, row=self.i )
            self.i += 1
        
        #Control button configuration
        button( self.pool[ 'i:fugue/arrow-circle-double.png' ], 'Rebuild', self.rebuild )

        button( self.pool[ 'i:fugue/gear.png' ], 'Properties', lambda: tkprops.Manager( self, self.props ).wait_window() )
        
        spacer()

        button( self.pool[ 'i:fugue/document-search-result.png' ], 'Copy Item(s)', self.copy )

        button( self.pool[ 'i:fugue/documents.png' ], 'Show in File Manager', self.show )

        spacer()

        button( self.pool[ 'i:fugue/edit-list.png' ], 'Index Manager', lambda: media_tools.IndexManager( self ), state=DISABLED )
        
        button( self.pool[ 'i:fugue/lightning.png' ], 'Execute test', self.test )#, state=DISABLED )
        #end

        tkinter.ttk.Separator( page, orient=HORIZONTAL ).pack( fill=BOTH )

        style = tkinter.ttk.Style()
        style.configure( 'play.TButton', font=( 'Arial', 24 ) )
        tkinter.ttk.Button( page, text='Open in VLC', image=self.pool[ 'i:media/vlc.png' ], compound=LEFT, style='play.TButton', command=self.play ).pack( expand=True, fill=BOTH, padx=5, pady=5)
        
        #end page 1
        #configuring page 2
        ##meh
        #end page 2        
        
        if self.props.get( 'first' ):
            self.after( 100, self.rebuild )
            self.props.set( 'first', False )
        else:
            self.after( 100, self.refresh, self.db )
    
    def test( self ):
        #p = tkmisc.ProgressRect( self )
        #movies = [ entry[0] for entry in self.db.execute( 'SELECT title FROM file' ).fetchall() ]
        #open( 'movies.txt', 'w' ).write( '\n'.join( movies ) )
        from asizeof import asizeof as aso
        print( 'Size:', aso( self.pool.cache ), sys.getsizeof( self.pool.cache ) )
    
    def checkProps( self ):
        if self.props.is_def( 'vlc-path' ):
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
                                            erecord = Episode( item='', tag=match.group(1), title=epititle, path=fpath, season=int( match.group( 3 ) ) )
                                            srecord.episodes.append( erecord )
                                            self.db.add( erecord )
                                        elif self.props.get( 'collect-loose' ):
                                            match = pattern2.match( fname )
                                            if match and match.group( 1 ) == tag:
                                                fname = pattern2.sub( '', fname )
                                                tree.insert( epientry, END, text=fname, tags=[ 'file' ] )
                                                #self.db.execute( 'INSERT INTO episode VALUES( ?, ?, ?, ? )', ( entryid, fname, tag, fpath ) )
                                                loosetag = '{0}..{1:0>2} {2}'.format( tag, loosei, fname )
                                                erecord = Episode( item='', tag=loosetag, title=fname, path=fpath, season=-1 )
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
                            self.db.add( Movie( item='', title=title, path=fpath, imdb=f.get('imdb', '') ) )
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
            series.item = serentry
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
                    episode.item = epientry
                elif episode.season == 0:
                    entry = self.tree.insert( serentry, END, text=episode.title, values=[ episode.tag ], tags=tags, image=self.pool[ 'i:fugue/film.png' ] )
                    episode.item = entry
                    #entry = self.tree.insert( serentry, END, text=episode.title, values=[ episode.tag, ], tags=[ 'episode' ], image=self.pool[ 'i:fugue/film.png' ] )
            
            #files = db.execute( 'SELECT title, id FROM episode WHERE tag=? ORDER BY title DESC', ( tag, ) ).fetchall()
            #for f in files:
            self.update()
        
        #files = db.execute( 'SELECT title, id FROM file ORDER BY title ASC' ).fetchall()
        #for f in files:
        for movie in self.db.query( Movie ).order_by( Movie.title ):
            #self.tree.insert( '', END, text=f[0], values=[ '', f[1] ], tags=[ 'file', ], image=self.pool[ 'i:fugue/film.png' ] )
            entry = self.tree.insert( '', END, text=movie.title, tags=[ 'file', ], image=self.pool[ 'i:fugue/film.png' ] )
            movie.item = entry
            self.update()
        
        self.db.commit()
        self.stripeChildren( '' )

    def search( self ):
        return
        db = self.db
        stext = self.searchent.get()

        if not self.searchent.ghosted and stext:
            for child in self.tree.get_children():
                self.tree.delete( child )
            
            pattern = re.compile( self.props.get( 'pattern-episodic' ) )
            seriess =  db.execute( 'SELECT title, tag, data, id FROM series WHERE title REGEXP ? ORDER BY title ASC', ( stext, ) ).fetchall()
            for series in seriess:
                title = series[0]
                tag = series[1]
                data = yaml.load( series[2] )

                serentry = self.tree.insert( '', END, text=title, values=[ tag, ] )
                seaentries = {}
                episodes = db.execute( 'SELECT title, tag, id FROM episode WHERE tag LIKE ? AND NOT tag=? ORDER BY tag ASC', ( tag + '%', tag ) ).fetchall()
                for episode in episodes:
                    epimatch = pattern.match( episode[1] )
                    episea = epimatch.group( 3 )
                    if episea in seaentries:
                        seaentry = seaentries[ episea ]
                    else:
                        seaentry = self.tree.insert( serentry, END, text='Season {0}'.format( int( episea ) ), values=[ tag + episea, ] )
                        seaentries[ episea ] = seaentry
                    
                    tags = [ 'episode', ]
                    self.tree.insert( seaentry, END, text=str( episode[0] ), values=[ episode[1], episode[2] ], tags=tags )
                
                files = db.execute( 'SELECT title, id FROM episode WHERE tag=? ORDER BY title DESC', ( tag, ) ).fetchall()
                for f in files:
                    self.tree.insert( serentry, 0, text=f[0], values=[ tag, f[1] ], tags=[ 'episode' ] )
            
            episodes = db.execute( 'SELECT title, tag, id FROM episode WHERE title REGEXP ? OR tag REGEXP ? ORDER BY tag ASC', ( stext, stext ) ).fetchall()
            for episode in episodes:
                tags = [ 'episode', ]
                self.tree.insert( '', END, text=str( episode[0] ), values=[ episode[1], episode[2] ], tags=tags )

            files = db.execute( 'SELECT title, id FROM file WHERE title REGEXP ? ORDER BY title ASC', ( stext, ) ).fetchall()
            for f in files:
                self.tree.insert( '', END, text=f[0], values=[ '', f[1] ], tags=[ 'file', ] )

            self.stripeChildren( '' )
    
    def stripeChildren( self, master, odd=True ):
        for item in self.tree.get_children( master ):
            tags = self.tree.item( item )[ 'tags' ]
            if odd:
                if not tags: tags = []
                tags.append( 'stripe' )
                self.tree.item( item, tags=tags )
            odd = not odd
            self.stripeChildren( item, odd )
    
    #def updateLastp( self, tags ):
    #    pattern = re.compile( self.props.get( 'pattern-episodic' ) )
    #    masters = {}
    #    for tag in tags:
    #        match = pattern.match( tag )
    #        base = match.group(2)
    #        if not base in masters:
    #            masters[ base ] = []
    #        masters[ base ].append( tag )
    #    
    #    for master in masters.keys():
    #        for item in self.tree.get_children( '' ):
    #            tag = self.tree.item( item )[ 'values' ][0]
    #            if tag == master:
    #                lastp = masters[ master ]
    #                for sea in self.tree.get_children( item ):
    #                    seamark = False
    #                    seatags = self.tree.item( sea )[ 'tags' ]
    #                    if 'last' in seatags:
    #                        self.tree.item( sea, tags=seatags[:-1] )
    #                    for epi in self.tree.get_children( sea ):
    #                        epitag = self.tree.item( epi )[ 'values' ][0]
    #                        epitags = self.tree.item( epi )[ 'tags' ]
    #                        if 'last' in epitags and not epitag in lastp:
    #                            self.tree.item( epi, tags=epitags[:-1] )
    #                        elif not 'last' in epitags and epitag in lastp:
    #                            self.tree.item( epi, tags=epitags + [ 'last', ] )
    #                            seamark = True
    #                        elif 'last' in epitags and epitag in lastp:
    #                            seamark = True
    #                    if seamark:
    #                        seatags = self.tree.item( sea )[ 'tags' ] or []
    #                        self.tree.item( sea, tags=seatags + [ 'last', ] )
    #    
    #    for ( tag, tags ) in masters.items():
    #        self.lastp[ tag ] = tags
    
    def setLastp( self, tags ):
        series = {}
        for tag in tags:
            record = self.db.query( Episode ).filter_by( tag = tag ).first()
            if record is None:
                continue
            base = record.series
            if not base in series:
                series[ base ] = []
            series[ base ].append( record )
        
        for ( sertag, records ) in series.items():
            
            lastp = self.lastp[ sertag ]
            
            for tag in lastp:
                item = self.db.query( Episode ).filter_by( tag = tag ).first().item
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
            
            for record in records:
                item = record.item
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
    
    def getFiles( self, getTags=False ):
        items = self.tree.selection()
        files = []
        tags = []
        
        for item in items:
            record = self.db.query( Episode ).filter( Episode.item == item ).first()
            if not record:
                record = self.db.query( Movie ).filter( Movie.item == item ).first()
                files.append(record.path)
                continue
            files.append( record.path )
            tags.append( record.tag )
            
        
        if getTags:
            return tags
        return files
    
    def play( self ):
        if self.props.is_def( 'vlc-path' ):
            tkinter.messagebox.showerror( 'Missing property!', 'There is no defined path to VLC in the properties manager.' )
            return
        
        self.setLastp( self.getFiles( True ) )
        #return
        files = self.getFiles()
        if files:            
            method = self.props.get( 'vlc-method' )
            if method == 0:
                args = [ self.props.get( 'vlc-path' ), ] + self.props.get( 'vlc-args' ) + files
                Popen( args )
    
    def _copyBlind( self, files ):
        
        prog = tkmisc.ProgressRect( self )
        
        for i, ( src, dest ) in enumerate( files ):
            
            if prog.button_pressed:
                break
            
            prog.set( 0 )
            prog.set_text( 'File {0} of {1}'.format( i + 1, len( files ) ) )
            
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
                    
                    if prog.button_pressed:
                        break
                    #top.update()
                #top.destroy()
            finally:
                if fdst:
                    fdst.close()
                if fsrc:
                    fsrc.close()
        
        if prog.button_pressed:
            prog.set_text( 'Operation cancelled' )
            for src, dest in files:
                if os.path.isfile( dest ):
                    os.remove( dest )
        else:
            prog.set_text( 'Done!' )
            prog.button.config( state=DISABLED )
    
    def copy( self ):
        method = self.props.get( 'copy-method' )
        srcfiles = self.getFiles()
        files = []
        if srcfiles:
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
                            tkinter.messagebox.showerror( 'Missing Module!', 'In order to make use of this feature on Windows, you must have the "pywin32" package installed.' )
                            return
                        
                        srcstr = chr( 0 ).join( [ file[0] for file in files ] )
                        deststr = chr( 0 ).join( [ file[1] for file in files ] )
                        shell.SHFileOperation(
                            ( 0, shellcon.FO_COPY, srcstr, deststr, shellcon.FOF_MULTIDESTFILES, None, None )
                        )
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
                
                elif method is 3:
                    cmds = self.props.get( 'copy-custom' ).split( '\n' )
                    for file in files:
                        for cmd in cmds:
                            os.system( cmd.format( *file ) )
    
    def show( self ):
        files = self.getFiles()
        if files:
            system = platform.system()
            if system is 'Windows':
                os.system( 'explorer.exe /select, "{0}"'.format( files[0] ) )
            elif system is 'Mac':
                os.system( 'open -R "{0}"'.format( files[0] ) )
            elif system is 'Linux':
                os.system( 'xdg-open "{0}"'.format( os.path.dirname( files[0] ) ) )
                #In order to be cross-platform and all that jazz, I'm using xdg-open.
                #This command can't actually highlight the file like Mac and Windows can,
                #but it can open the directory in the system's default file manager
            else:
                tkinter.messagebox.showerror( 'Not Implemented!', 'The functionality is not implemented on your platform!' )
    
    def serverCheck( self ):
        if self.props.get( 'server-enabled' ):
            from rpyc.utils.server import ThreadedServer
            if self.server:
                pass
            else:
                print('Starting servers...')
                self.server = server = ThreadedServer( MediaService )
    
    def connect( self ):
        self.connectBut.config( state=DISABLED )
        self.disconnectBut.config( state=NORMAL )
    
    def disconnect( self ):
        self.connectBut.config( state=NORMAL )
        self.disconnectBut.config( state=DISABLED )

if __name__ == '__main__': Menu()
