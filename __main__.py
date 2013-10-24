import tkinter
import tkinter.ttk
from tkinter.constants import *
import tkinter.font
import tkinter.filedialog
import tkinter.messagebox

from threading import Thread
from subprocess import Popen
import subprocess
import webbrowser
import mimetypes
import traceback
import datetime
import platform
import logging
import json
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
import tooltip
import tkform

import num2engl
import persist
import walkdir

import bottle
#from bottle_renderer import RendererPlugin
from bottle_sqlalchemy import SQLAlchemyPlugin

import media_db
from media_db import Base, Series, Episode, Movie
import sqlalchemy

_path = os.path.dirname(__file__) or os.getcwd()

class Menu(tkinter.Tk):
    
    def __init__(self, mainloop=True):
        super().__init__()        
        self._setup()
        self.bottle_init()
        if mainloop:
            self.mainloop()

    def destroy(self):
        try:
            self.lastp.close()
            self.props.close()
            self.db.commit()
        except: pass
        super().destroy()
    
    def _setup(self):
        self.title('Media')
        
        self.pool = pool = ppk.Pool()
        pool.include(os.path.join(_path, 'ppk'))

        self.iconphoto(True, pool['i:media/play_alt_2.png'])
        #self.tk.call('wm', 'iconphoto', self._w, pool['i:/media/play_alt_2.png'], default=True)

        base = os.path.expanduser('~/.media')
        if not os.path.isdir(base):
            os.mkdir(base)
            
        self.propsFile = os.path.join(base, 'props')
        self.lastpFile = os.path.join(base, 'lastp')
        
        #self.db = self.db_Session()
        self.db_path = path = os.path.expanduser('~/.media/db')
        base = os.path.dirname(path)
        if not os.path.isdir(base):
            os.makedirs(base)
        self.db_engine = sqlalchemy.create_engine('sqlite:///' + path)

        media_db.Base.metadata.create_all(self.db_engine)

        self.db_Session = sqlalchemy.orm.sessionmaker(bind=self.db_engine)
        
        #self.props = tkprops.Reader(self.propsFile, yaml.load(pool['media/props.yaml']))
        #self.props = tkprops.Reader(self.propsFile, yaml.load(open('./media~/props.yaml', 'r').read()))
        #self.props = tkprops.Reader(self.propsFile, yaml.load(open(os.path.join(_path, 'media~', 'props.yaml'), 'r').read()))
        self.props = tkprops.Reader(self.propsFile, self.pool['y:media/props.yaml'])

        #self.props.bind('update-manager', self.updater)
        
        self.lastp = persist.PersistentDict(self.lastpFile)
        self.leaves = dict()
        self.movieentry = None
        
        self.treefrm = tkscroll.ScrolledTree(self, columns=[0], height=20)
        self.treefrm.pack(side=LEFT, expand=True, fill=BOTH)
        self.tree = tree = self.treefrm.tree
        
        tree.column('#0', width=250)
        tree.column(0, width=100)
        tree.heading('#0', text='Title / Season')
        tree.heading(0, text='Tag')
        
        #tree.tag_configure('file', image=self.pool['i:media/movie_16x16.png'])
        tree.tag_configure('stripe', background='#f2f5f9') #f4f4f4
        tree.tag_configure('last', foreground='#eb6901')

        tree.bind('<<TreeviewSelect>>', self.imdb_check)
        tree.bind('<<TreeviewOpen>>', self.tree_open)
        
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
        
        rebuildbutton = button(image=self.pool['i:media/spin.png'], image2=self.pool['i:media/spin_2.png'], command=self.rebuild, text='Rebuild cache and reload list')
        rebuildbutton.rmenu = tkinter.Menu(self, tearoff=False)
        rebuildbutton.rmenu.add_command(label='Auto-Finder', command=self.rebuild_autofind)
        rebuildbutton.bind('<Button-3>', lambda e: rebuildbutton.rmenu.post(e.x_root, e.y_root))

        button(image=self.pool['i:media/cog.png'], image2=self.pool['i:media/cog_2.png'], command=lambda: tkprops.ManagerWindow(self, self.props), text='Application properties')

        self.play_button = button(image=self.pool['i:media/play_alt_2.png'], command=self.play, text='Play selected file(s)')
        
        listbut = button(image=self.pool['i:media/list.png'], image2=self.pool['i:media/list_2.png'], text='Manage indices', command=lambda: IndexManager(self))
        '''rmenu = tkinter.Menu(self, tearoff=False)
        rmenu.add_command(label='Edit')
        rmenu.add_command(label='New')
        listbut.bind('<Button-3>', lambda e: rmenu.post(e.x_root, e.y_root))'''
                
        button(image=self.pool['i:media/document_alt_stroke.png'], image2=self.pool['i:media/document_alt_stroke_2.png'], command=self.copy, text='Copy selected file(s)')

        #button(image=self.pool['i:media/folder_fill.png'], image2=self.pool['i:media/folder_fill_2.png'], command=self.show, text='Show in file manager')

        self.imdb_button = button(image=self.pool['i:media/imdb.png'], image2=self.pool['i:media/imdb_2.png'], command=self.imdb, text='Open IMDb page', state=DISABLED)
        
        import tkform
        button(text='Form Test', command=lambda: tkform.formtest(self))

        self.update_idletasks()
        self.minsize(self.winfo_width(), self.winfo_height())
        
        vlcformresult = tkform.form(self, self.pool['y:forms/vlc.yaml'])
        
        if self.props.get('first'):
            self.after(200, self.rebuild)
            self.props.set('first', False)
            
            tries = [
                os.path.join(os.environ['PROGRAMFILES'], 'VideoLAN', 'VLC', 'vlc.exe') #Default install location for Windows
           ]
            
            for path in tries:
                if os.path.isfile(path):
                    self.props.set('vlc-path', path)
            
        else:
            self.after(100, self.refresh)

    def bottle_init(self):
        app = bottle.Bottle()
        #app.install(RendererPlugin())
        app.install(SQLAlchemyPlugin(
            self.db_engine,
            media_db.Base.metadata,
            create=True,
            keyword='db'
       ))

        self.session = uuid.uuid4().hex
        self.streams = {}

        def locked():
            cookie = bottle.request.get_cookie('HT-MEDIA-SESSION', default='')
            if cookie != self.session:
                bottle.redirect('/media/unlock')

        @app.get('/favicon.ico')
        def favicon():
            #return bottle.static_file('film.png', '')
            #bottle.response.content_type = 'image/png'
            #return self.pool['r:/media/play_alt_2.png']
            bottle.redirect('/media/ppk/media/play_alt_2.png')

        import bottle_handlers

        #@app.get('/media/static/<path:path>')
        #def static(path):
        #    print('STATICHANDLER', path)
        #    return bottle.static_file(filename=os.path.basename(path), root=os.path.join(_path, 'static', os.path.dirname(path)))

        #app.mount('/media/static', bottle_handlers.static(root=os.path.join(_path, 'static')))

        #@app.get('/media/secret/<path:path>')
        #def static(path):
        #    return bottle.static_file(path, '.')

        #@app.get('/media/ppk/<path:path>')
        #def static(path):
        #    data = self.pool['r:' + path]
        #    if not data: return bottle.HTTPError(404)
        #    bottle.response.content_type = mimetypes.guess_type(path)[0]
        #    return data

        #app.mount('/media/ppk', bottle_handlers.ppk())
        app.mount('/media/ppk', bottle_handlers.ppk())#(self.pool))

        @app.get('/media')
        def index(db):
            locked()
            tag = bottle.request.query.tag
            settings = bottle.request.get_cookie('HT-SETTINGS')
            if settings:
                settings = json.loads(settings)
            else:
                settings = [1, 0]

            return bottle.template(
                self.pool['views/index.stpl'].decode(),
                {
                'download': bottle.request.query.download,
                'max': sqlalchemy.func.max,
                'db': db,
                'Series': Series,
                'Episode': Episode,
                'Movie': Movie,
                'tag': tag,
                'bottle': bottle,
                'settings': settings
                }
            )

        @app.post('/media')
        def index_settings():
            locked()
            settings = [
                int(bottle.request.params.playtype),
                int(bottle.request.params.errorson)
            ]
            bottle.response.set_cookie('HT-SETTINGS', json.dumps(settings))
            return '<script>window.location="{0}"</script>'.format('/media')

        #@app.get('/media/unlock', renderer=os.path.join(_path, 'unlock.stpl'))
        @app.get('/media/unlock')
        def unlock_GET():
            return bottle.template(
                self.pool['views/unlock.stpl'].decode()
            )

        @app.post('/media/unlock')
        def unlock_POST():
            code = bottle.request.forms.code
            if code.encode() == self.props['server-unlock'].encode():
                bottle.response.set_cookie('HT-MEDIA-SESSION', self.session, path='/')
                return [None,]
            else:
                return bottle.HTTPError(403)
        
        @app.route('/media/lock')
        def lock():
            bottle.response.delete_cookie('HT-MEDIA-SESSION')
            return [None,]

        @app.get('/media/<action>')
        def stream(action):
            locked()
            query = bottle.request.query
            db = self.db_Session()
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

            if action == 'play':
                self.play(files=[path,], web=True)
            elif action == 'stream':
                urlid = uuid.uuid4().hex
                self.streams[urlid] = path
                url = '/media/link/' + urlid
                return bottle.template(
                    self.pool['views/stream.stpl'].decode(),
                    **{'url': url}
                )

            return ''

        @app.get('/media/link/<id>')
        def streamlink(id):
            print('LINK', id, bottle.request.remote_addr)
            stream = self.streams.get(id, None)
            if not stream: return bottle.HTTPError(404)
            #return bottle.static_file(os.path.basename(stream), root=os.path.dirname(stream), mimetype='application/x-vlc-plugin')
            bottle.response.content_type = 'application/x-vlc-plugin'
            return open(stream, 'rb')

        thread = Thread(
            target = lambda: app.run(host='0.0.0.0', port=self.props['server-port'], server='tornado', debug=True)
       )
        thread.daemon = True
        if self.props['server-enabled']:
            thread.start()
    
    def checkProps(self):
        if not self.props.changed('vlc-path'):
            cont = tkinter.messagebox.askyesno(
                'Missing path',
                'The property "vlc-path" is not currently defined; it is required to play media files. Define it now?'
           )
            if cont:
                tkprops.Modify(self, self.props, 'vlc-path')
    
    def rebuild(self, refresh=True):
        try:
            db = self.db_Session()
            self.leaves = {}
            root = tkinter.Toplevel(self)
            root.title('Rebuilding...')
            #root.resizable(0, 0)
            root.transient(self)
            root.grab_set()
            
            root.geometry('+{0}+{1}'.format(self.winfo_rootx(), self.winfo_rooty()))
            
            treefrm = tkscroll.ScrolledTree(root, height=15)
            treefrm.pack(expand=True, fill=BOTH)
            tree = treefrm.tree
            tree.column('#0', width=400)
            tree.tag_configure('error', image=self.pool['i:iconic/red/x_14x14.png']) #foreground='#C40233'
            tree.tag_configure('warning', image=self.pool['i:iconic/orange/info_8x16.png']) #foreground='#FFD300'
            tree.focus_set()
            
            tree.tag_configure('file', foreground='#333355')
            
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            #db.commit()
            
            pattern = re.compile(self.props.get('pattern-episodic'))
            pattern2 = re.compile(self.props.get('pattern-loose'))
            entryid = 0
            
            for basedir in self.props.get('directories'):
                
                basedir = os.path.abspath(basedir)
                
                if not os.path.isdir(basedir):
                    tree.insert('', 0, text='Directory "{0}" does not exist or is inaccessible.'.format(basedir), tags=['error',])
                    continue
                for subdir in os.listdir(basedir):
                    
                    subdir = os.fsdecode(os.path.join(basedir, subdir))
                    datafile = os.path.join(subdir, 'media.yaml')
                    
                    if os.path.isfile(datafile):
                        
                        dataentry = tree.insert('', 0, text=datafile)
                        root.update_idletasks()
                        
                        #data = yaml.load(open(datafile, 'rb').read())
                        with open(datafile, 'rb') as datafileobj:
                            data = yaml.load(datafileobj)
                        extensions = tuple(self.props.get('extensions'))
                        
                        
                        #Parsing tv series';
                        if 'series' in data and self.props.get('collect-series'):
                            for series in data['series']:
                                if 'dir' in series:
                                    serdir = os.path.join(subdir, series['dir'])
                                else:
                                    serdir = subdir
                                title = series['title']
                                tag = series['tag']
                                epientry = tree.insert(dataentry, END, text=tag + ' ' + title)
                                #db.execute('INSERT INTO series VALUES(?, ?, ?, ?)', (entryid, title, tag, yaml.dump(series)))
                                srecord = Series(item='', tag=tag, title=title, imdb=series.get('imdb', None))
                                srecord.episodes = []
                                loosei = 0
                                
                                for (dpath, dnames, fnames) in os.walk(str(serdir)):
                                    for fname in fnames:
                                        if fname.endswith(extensions):
                                            fpath = os.path.join(dpath, fname)
                                            match = pattern.match(fname)
                                            if match is not None:
                                                #epititle = match.group(5) or 'Episode {0}'.format(match.group(4))
                                                epititle = match.group(5) or 'Episode {0}'.format(' '.join(num2engl.num2words(int(match.group(4)))).capitalize())
                                                #db.execute('INSERT INTO episode VALUES(?, ?, ?, ?)', (entryid, epititle, match.group(1), fpath))
                                                erecord = Episode(tag=match.group(1), title=epititle, path=fpath, season=int(match.group(3)))
                                                srecord.episodes.append(erecord)
                                                db.add(erecord)
                                            elif self.props.get('collect-loose'):
                                                match = pattern2.match(fname)
                                                if match and match.group(1) == tag:
                                                    fname = pattern2.sub('', fname)
                                                    tree.insert(epientry, END, text=fname, tags=['file'])
                                                    #db.execute('INSERT INTO episode VALUES(?, ?, ?, ?)', (entryid, fname, tag, fpath))
                                                    loosetag = '{0}..{1:0>2} {2}'.format(tag, loosei, fname)
                                                    erecord = Episode(tag=loosetag, title=fname, path=fpath, season=-1)
                                                    srecord.episodes.append(erecord)
                                                    db.add(erecord)
                                                    print(fname)
                                                    loosei += 1
                                            root.update_idletasks()
                                
                                db.add(srecord)
                                root.update()
                        
                        #Parsing secondary files;
                        if 'file' in data and self.props.get('collect-files'):
                            for f in data['file']:
                                title = f['title']
                                tree.insert(dataentry, END, text=title, tags=['file'])
                                fpath = os.path.abspath(os.path.join(subdir, f['file']))
                                db.add(Movie(title=title, path=fpath, imdb=f.get('imdb', None)))
                                root.update_idletasks()
                            root.update()
                        
                        self.update()
            
            db.commit()
            tree.insert('', 0, text='Done!')
            self.after(100, self.refresh)
        except tkinter.TclError:
            pass

    def rebuild_autofind(self):
        topl = tkinter.Toplevel(self)
        topl.title('Directory Auto-Finder')
        topl.transient(self)
        topl.grab_set()
        topl.focus_set()


        tkinter.ttk.Label(topl, text='Directory Recursion Depth').grid(column=0, row=0, columnspan=2)

        tkinter.ttk.Separator(topl, orient=HORIZONTAL).grid(column=0, row=1, columnspan=2, sticky='WE')

        topl.scaleint = tkinter.IntVar(topl, value=2)
        topl.scale = tkinter.Scale(topl, from_=1, to=10, variable=topl.scaleint, orient=HORIZONTAL, showvalue=1, length=250)
        topl.scale.grid(column=0, row=2, columnspan=2, sticky='WE', ipadx=10)

        topl.status = tkinter.StringVar(topl)
        tkinter.ttk.Label(topl, textvariable=topl.status, wraplength=240).grid(column=0, row=4, columnspan=2)

        topl.running = False
        topl.halt = False

        def start():
            if topl.halt:
                topl.destroy()
                return

            topl.scale['state'] = DISABLED
            topl.startbutton['state'] = DISABLED

            system = platform.system()
            drives = []
            if system is 'Windows':
                import win32api
                drives = win32api.GetLogicalDriveStrings()
                drives = drives.split('\000')[:-1]
                try:
                    drives.remove('C:\\')
                    drives.remove('A:\\')
                except: pass
            elif system is 'Linux':
                try:
                    drives = os.listdir('/mount')
                    for drive in drives:
                        drive = os.path.join('/mount', drive)
                except FileNotFoundError:
                    tkinter.messagebox.showerror('Not Implemented!', 'The functionality is not implemented on your platform!')
                    topl.destroy()
                    return
            elif system is 'Mac':
                drives = os.listdir('/Volumes')
                for drive in drives:
                    drive = os.path.join('/Volumes', drive)
            else:
                tkinter.messagebox.showerror('Not Implemented!', 'The functionality is not implemented on your platform!')
                topl.destroy()
                return

            depth = topl.scaleint.get()
            
            for drive in drives:

                found = set()
                for root, dirs, files in walkdir.filtered_walk(drive, depth=depth):
                    topl.status.set(root)
                    topl.update()
                    if topl.halt:
                        topl.destroy()
                        return
                    if 'media.yaml' in files:
                        found.add(os.path.split(root)[0])

            topl.status.set('Directories found:')
            topl.cancelbutton['state'] = DISABLED
            tkinter.ttk.Label(topl, text='\n'.join(list(found))).grid(column=0, row=5, columnspan=2)

            directories = self.props.get('directories')
            for entry in directories:
                if entry in found:
                    found.remove(entry)
            directories += list(found)
            self.props.set('directories', directories)

        def cancel():
            topl.halt = True
            if not topl.running:
                start()

        topl.startbutton = tkinter.ttk.Button(topl, text='\nStart\n', command=start)
        topl.startbutton.grid(column=0, row=3, sticky='WESN')
        topl.cancelbutton = tkinter.ttk.Button(topl, text='\nCancel\n', command=cancel)
        topl.cancelbutton.grid(column=1, row=3, sticky='WESN')

        for i in range(2):
            topl.columnconfigure(i, weight=1)

        topl.rowconfigure(3, weight=1)

        tkmisc.center(topl, self)
        tkinter.messagebox.showinfo(
            'Info',
            'This will automatically detect mounted drives (excluding C:\\ and A:\\ on Windows), will search them for directories containing indexed movies/series, and will add them to the scan list if not already present.',
            parent=topl,
            icon=tkinter.messagebox.INFO
        )
    
    def refresh(self):
        db = self.db_Session()
        for child in self.tree.get_children():
            self.tree.delete(child)
        
        pattern = re.compile(self.props.get('pattern-episodic'))
        
        for series in db.query(Series).order_by(Series.title):
            if not series.tag in self.lastp:
                self.lastp[series.tag] = []
            lastp = self.lastp[series.tag]

            serentry = self.tree.insert('', END, text=series.title, values=[series.tag,])
            self.tree.insert(serentry, END, text='NULL')
            self.leaves[serentry] = series.tag
            self.update()

        self.movieentry = self.tree.insert('', END, text='Movies', image=self.pool['i:media/movie_16x16.png'])#, tags=['file',])
        self.tree.insert(self.movieentry, END, text='NULL')

    def tree_open(self, event):
        db = self.db_Session()
        item = self.tree.focus()
        children = self.tree.get_children(item)
        if children and self.tree.item(children[0])['text'] == 'NULL':
            [self.tree.delete(child) for child in children]
            if item == self.movieentry:
                for movie in db.query(Movie).order_by(Movie.title):
                    entry = self.tree.insert(self.movieentry, END, text=movie.title, tags=['file',])
                    self.leaves[entry] = movie.id
            else:
                parent = self.tree.parent(item)
                if parent == '':
                    tag = self.tree.item(item)['values'][0]
                    series = db.query(Series).filter_by(tag=tag).first()

                    '''for episode in self.db.query(Episode).filter(Episode.series == series.tag).filter(Episode.season == 0):
                        epientry = self.tree.insert(item, END, text=episode.title, values=[episode.tag,], tags=['file',])
                        self.leaves[epientry] = episode.tag'''

                    lastp = self.lastp[series.tag]
                    seasons = set()
                    marked = set()
                    for episode in db.query(Episode).filter(Episode.series == series.tag):
                        if episode.season > 0:
                            seasons.add(episode.season)
                        if episode.tag in lastp:
                            marked.add(episode.season)
                    for season in sorted(seasons):
                        seatag = '{0}{1:0>2}'.format(series.tag, season)
                        tags = []
                        if season in marked:
                            tags.append('last')
                        seaentry = self.tree.insert(item, END, text='Season {0}'.format(season), values=[seatag,], tags=tags)
                        self.tree.insert(seaentry, END, text='NULL')
                else:
                    tag = self.tree.item(parent)['values'][0]
                    series = db.query(Series).filter_by(tag=tag).first()
                    lastp = self.lastp[series.tag]
                    season = int(self.tree.item(item)['values'][0][-2:])
                    for episode in db.query(Episode).filter(Episode.series == series.tag).filter(Episode.season == season):
                        tags = []
                        if episode.tag in lastp:
                            tags.append('last')
                        epientry = self.tree.insert(item, END, text=episode.title, values=[episode.tag,], tags=tags)
                        self.leaves[epientry] = episode.tag
        else:
            self.play()
            #Handle file playing
    
    def stripeChildren(self, master, odd=True):
        #return
        for item in self.tree.get_children(master):
            tags = self.tree.item(item)['tags']
            if odd:
                if not tags: tags = []
                tags.append('stripe')
                self.tree.item(item, tags=tags)
            odd = not odd
            self.stripeChildren(item, odd)
    
    '''def setLastp(self, tags):
        db = self.db_Session()
        ileaves = {v:k for k, v in self.leaves.items()}
        series = {}
        for tag in tags:
            #tag = self.leaves.get(item, None)
            if not tag in tags: continue
            item = ileaves[tag]
            record = db.query(Episode).filter_by(tag = tag).first()
            if record is None:
                continue
            base = record.series
            if not base in series:
                series[base] = []
            series[base].append((record, item))
        
        for (sertag, records) in series.items():
            
            lastp = self.lastp[sertag]
            
            for tag in lastp:
                if tag in ileaves:
                    item = ileaves[tag]
                    tags = set(self.tree.item(item)['tags'] or [])
                    if 'last' in tags:
                        tags.remove('last')
                        self.tree.item(item, tags=list(tags))
                    
                    pitem = self.tree.parent(item)
                    tags = set(self.tree.item(pitem)['tags'] or [])
                    if 'last' in tags:
                        tags.remove('last')
                        self.tree.item(pitem, tags=list(tags))
                else:
                    pass
            
            lastp = []
            
            for (record, item) in records:
                tags = self.tree.item(item)['tags'] or []
                if not 'last' in tags:
                    tags.append('last')
                    self.tree.item(item, tags=tags)
                
                pitem = self.tree.parent(item)
                tags = self.tree.item(pitem)['tags'] or []
                if not 'last' in tags:
                    tags.append('last')
                    self.tree.item(pitem, tags=tags)
                
                lastp.append(record.tag)
            
            self.lastp[sertag] = lastp
        self.lastp.sync()'''
    
    def tagRem(self, tag, item):
        tags = set(self.tree.item(item)['tags'])
        tags.remove(tag)
        self.tree.item(item, tags=list(tags))
    
    def tagAdd(self, tag, item):
        tags = set(self.tree.item(item)['tags'])
        tags.add(tag)
        self.tree.item(item, tags=list(tags))

    def setLastp(self):
        db = self.db_Session()
        selec = self.tree.selection()
        ileaves = {v:k for k, v in self.leaves.items()}
        leaves = []
        lastp = {}
        for item in selec:
            values = self.tree.item(item)['values']
            if len(values) == 0: continue
            tag = values[0]
            episode = db.query(Episode).filter_by(tag=tag).first()
            if episode:
                leaves.append(item)
                
                if not episode.series in lastp:
                    lastp[episode.series] = []
                
                lastp[episode.series].append(episode.tag)
        
        self.lastp.update(lastp)
        
        for leaf in leaves:
            parent = self.tree.parent(self.tree.parent(leaf))
            for i in self.tree.get_children(parent):
                for j in self.tree.get_children(i):
                    if self.tree.tag_has('last', j):
                        self.tagRem('last', j)
                if self.tree.tag_has('last', i):
                    self.tagRem('last', i)
        
        for leaf in leaves:
            self.tagAdd('last', leaf)
            parent = self.tree.parent(leaf)
            self.tagAdd('last', parent)
    
    def getFiles(self, files=False, tags=False, items=False):
        retfiles = []
        rettags = []
        retitems = []
        db = self.db_Session()
        
        for item in self.tree.selection():
            tag = self.leaves.get(item, None)
            record = None
            if isinstance(tag, str):
                record = db.query(Episode).filter(Episode.tag == tag).first()
            elif isinstance(tag, int):
                record = db.query(Movie).filter(Movie.id == tag).first()
            if not record: continue
            retfiles.append(record.path)
            rettags.append(tag)
            retitems.append(item)
            
        if files:
            return retfiles
        if tags:
            return rettags
        if items:
            return retitems
    
    def play(self, files=None, web=False):
        #print('REQUEST?', bool(bottle.request))
        if not self.props.changed('vlc-path'):
            tkinter.messagebox.showerror('Missing property!', 'There is no defined path to VLC in the properties manager.')
            return
        
        db = self.db_Session()
        files = files or self.getFiles(files=True)
        if not files:
            return
        
        for file in files:
            if not os.path.isfile(file) and not web:
                tkinter.messagebox.showerror('Missing file!', 'File "{0}" does not exist or is inaccessible.'.format(file))
                return
        
        if not web:
            #tags = [obj[0] for obj in db.query(Episode.tag).filter(Episode.path.in_(files)).all()]
            self.setLastp()#tags)
           
        method = self.props.get('vlc-method')
        if method == 0:
            args = [self.props.get('vlc-path'),] + self.props.get('vlc-args') + files
            #self.play_button.config(state=DISABLED)
            Popen(args)
            #self.play_button.config(state=NORMAL)
    
    def _copyBlind(self, files):
        
        prog = tkmisc.ProgressDialog(self)
        
        for i, (src, dest) in enumerate(files):
            
            if prog.cancelled:
                break
            
            prog.set(0)
            prog.set('File {0} of {1}'.format(i + 1, len(files)))
            
            fsrc = None
            fdst = None
            keepGoing = False
            max = os.stat(src).st_size
            
            try:
                fsrc = open(src, 'rb')
                fdst = open(dest, 'wb')
                keepGoing = True
                count = 0
                
                while keepGoing:
                    buf = fsrc.read(2**20)
                    if not buf:
                        break
                    fdst.write(buf)
                    count += len(buf)
                    p = float(count) / float(max)
                    #prog.set(p * 100.0)
                    prog.set(p * 100)
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
            prog.set('Operation cancelled')
            for src, dest in files:
                if os.path.isfile(dest):
                    os.remove(dest)
        else:
            prog.set('Done!')
            prog.button.config(state=DISABLED)
    
    def copy(self):
        method = self.props.get('copy-method')
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
                    name = os.path.basename(srcfile)
                    src = os.path.normpath(srcfile)
                    dest = os.path.normpath(os.path.join(outdir, name))
                    files.append((src, dest))
                
                if method is 0:
                    system = platform.system()
                    if system is 'Windows':
                        try:
                            from win32com.shell import shell, shellcon
                        except ImportError:
                            tkinter.messagebox.showerror('Missing Module!', 'In order to make use of this feature, you must have the "pywin32" package installed. It can be obtained via the project\'s Sourceforge page.')
                            return
                        
                        srcstr = chr(0).join([file[0] for file in files])
                        deststr = chr(0).join([file[1] for file in files])
                        Thread(
                            target=lambda: shell.SHFileOperation(
                                (0, shellcon.FO_COPY, srcstr, deststr, shellcon.FOF_MULTIDESTFILES, None, None)
                           )
                       ).start()
                    else:
                        tkinter.messagebox.showerror('Not Implemented!', 'The shell copy method is not implemented on your platform!')
                
                elif method is 1:
                    
                    if platform.system() is not 'Windows':
                        tkinter.messagebox.showerror(
                            'Not Implemented!',
                            'The TeraCopy method is only implemented on Windows! (Which is not your current platform)'
                       )
                        return
                    
                    if not os.path.isfile('TeraCopy.exe'):
                        tkinter.messagebox.showerror(
                            'Missing Executable!',
                            'In order to use TeraCopy for copying files, the TeraCopy executable must be present in the current working directory. ("TeraCopy.exe")',
                       )
                        return
                    
                    listpath = os.path.join(os.getcwd(), 'media--teracopylist.txt')
                    listout = '\n'.join([file[0] for file in files])
                    with open(listpath, 'w') as listfile:
                        listfile.write(listout)
                    
                    args = [
                        'TeraCopy.exe',
                        'Copy',
                        '*"{0}"'.format(listpath),
                        outdir,
                   ]
                    
                    Popen(args)
                
                elif method is 2:
                    self._copyBlind(files)
    
    def show(self):
        files = self.getFiles(True)
        if files:
            system = platform.system()
            if system is 'Windows':
                os.system('explorer.exe /select,{0}'.format(files[0]))
            elif system is 'Mac':
                os.system('open -R "{0}"'.format(files[0]))
            elif system is 'Linux':
                os.system('xdg-open "{0}"'.format(os.path.dirname(files[0])))
                #In order to be cross-platform and all that jazz, I'm using xdg-open.
                #This command can't actually highlight the file like Mac and Windows can,
                #but it can open the directory where the file resides (theoretically)
            else:
                tkinter.messagebox.showerror('Not Implemented!', 'The functionality is not implemented on your platform!')

    def imdb_check(self, event=None):
        db = self.db_Session()
        item = self.tree.focus()
        if item == self.movieentry:
            self.imdb_button.config(state=DISABLED)
            return
        tag = self.leaves.get(item, None)
        if isinstance(tag, int):
            movie = db.query(Movie).filter(Movie.id == tag).first()
            if movie:
                if movie.imdb:
                    self.imdb_button.config(state=NORMAL)
                    return
        else:
            while True:
                if item == '': break
                parent = self.tree.parent(item)
                if parent == '':
                    break
                item = parent
            tag = self.tree.item(item)['values'][0]
            series = db.query(Series).filter(Series.tag == tag).first()
            if series and series.imdb:
                self.imdb_button.config(state=NORMAL)
                return
        self.imdb_button.config(state=DISABLED)

    def imdb(self):
        db = self.db_Session()
        item = self.tree.focus()
        tag = self.leaves.get(item, None)
        if isinstance(tag, int):
            movie = db.query(Movie).filter(Movie.id == tag).first()
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
        series = db.query(Series).filter(Series.tag == tag).first()
        if series and series.imdb:
            webbrowser.open_new_tab('http://www.imdb.com/title/' + series.imdb)

    def updater(self):
        self.destroy()























class IndexManager(tkinter.Toplevel):
    def __init__(self, root):
        self.root = root
        super().__init__(root)
        self.title('Index Manager')
        self.transient(root)
        self.grab_set()
        self.setup()
        tkmisc.center(self, root)
        self.update()
        self.after(100, self.scan)

    def setup(self):
        self.treefrm = treefrm = tkscroll.ScrolledTree(self, height=15)
        treefrm.pack(side=LEFT, expand=True, fill=BOTH)
        self.tree = tree = treefrm.tree
        tree.column('#0', width=400)
        tree.focus_set()

        self.side = side = tkinter.ttk.Frame(self)
        side.pack(side=LEFT, fill=Y)

        style = tkinter.ttk.Style()
        style.configure('center.Toolbutton', anchor=CENTER)
        def button(**kwargs):
            
            kwargs['style'] = 'center.Toolbutton'
            but = tkinter.ttk.Button(side, **kwargs)
            but.pack(expand=True, fill=BOTH, ipadx=10)
            
            if 'text' in kwargs:
                tip = tooltip.ToolTip(but, text=kwargs['text'], delay=500)

            return but

        self.addbutton = button(image=self.root.pool['i:iconic/green/plus_32x32.png'])
        dropmenu = tkinter.Menu(self, tearoff=False)
        dropmenu.add_command(label='Index File', command=self.add_index)
        dropmenu.add_command(label='Entry', command=self.add_entry)
        self.addbutton.bind('<ButtonRelease>', lambda e: dropmenu.post(e.x_root, e.y_root))

        button(image=self.root.pool['i:iconic/blue/pen_32x32.png'], command=self.edit_entry)
        button(image=self.root.pool['i:iconic/gray_dark/spin_alt_32x32.png'], command=self.scan)

        self.indices = {}
        self.entries = {}

    def scan(self, title=None):
        for child in self.tree.get_children():
            self.tree.delete(child)
        self.indices = {}
        self.entries = {}
        dirs = self.root.props['directories']
        for topdir in dirs:
            if not os.path.isdir(topdir): continue
            topentry = self.tree.insert('', END, text=topdir)

            for subdir in os.listdir(topdir):
                yamlpath = os.path.join(topdir, subdir, 'media.yaml')

                if os.path.isfile(yamlpath):
                    subentry = self.tree.insert(topentry, END, text=yamlpath)
                    self.indices[subentry] = yamlpath
                    data = yaml.load(open(yamlpath, 'rb').read())
                    if not data: continue

                    for section in data:
                        if not section in ('file', 'series'): continue
                        sectentry = self.tree.insert(subentry, END, text=section)
                        for (i, filedata) in enumerate(data[section]):
                            entry = self.tree.insert(sectentry, END, text='Entry {0:0>2}'.format(i), open=True)
                            self.entries[entry] = i
                            for key in filedata:
                                keyentry = self.tree.insert(entry, END, text='{0}: "{1}"'.format(key, filedata[key]))
                                if key == 'title' and filedata[key] == title:
                                    self.tree.see(keyentry)
                self.update_idletasks()

    def get_index(self, item):
        parent = item
        while parent != '':
            if parent in self.indices:
                break
            parent = self.tree.parent(parent)
        return self.indices.get(parent, None)

    def get_entry(self, item):
        parent = item
        while parent != '':
            if parent in self.entries: break
            parent = self.tree.parent(parent)
        entry = self.entries.get(parent, None)
        if not entry is None:
            etype = self.tree.item(self.tree.parent(parent))['text']
            return (etype, entry)
        else:
            return None

    def add_index(self):
        topl = tkinter.Toplevel(self)
        topl.title('New Index')
        topl.transient(self)
        topl.grab_set()
        topl.focus_set()

        topl.dirvar = tkinter.StringVar()
        tkinter.ttk.OptionMenu(topl, topl.dirvar, 'Choose parent directory', *self.root.props['directories']).pack(fill=X)

        topl.subentry = tkmisc.AdvEntry(topl, ghost='Enter name for subdirectory', width=40)
        topl.subentry.pack(fill=X)

        def choose_sub():
            topdir = topl.dirvar.get()
            if not topdir in self.root.props['directories']:
                tkinter.messagebox.showerror('Error', 'Please choose a parent directory first')
                return
            choice = tkinter.filedialog.askdirectory(initialdir=topdir)
            if choice == '': return
            rel = os.path.relpath(choice, topdir)
            if '..' in rel:
                tkinter.messagebox.showerror('Error', 'Please choose a directory lying one level within the parent directory')
                return
            topl.subentry.delete(0, END)
            topl.subentry.insert(0, rel)
        tkinter.ttk.Button(topl, text='Choose Directory', command=choose_sub).pack(fill=X)

        hull = tkinter.ttk.Frame(topl)
        hull.pack(expand=True, fill=BOTH, padx=5, pady=5)

        def check():
            topdir = topl.dirvar.get()
            if not topdir in self.root.props['directories']:
                tkinter.messagebox.showerror('Error', 'Please choose a parent directory')
                return
            subdir = topl.subentry.get()
            if not subdir:
                tkinter.messagebox.showerror('Error', 'Please supply a valid subdirectory')
                return
            fulldir = os.path.join(topdir, subdir)
            fullfile = os.path.join(fulldir, 'media.yaml')
            if os.path.isfile(fullfile):
                tkinter.messagebox.showerror('Error', 'Index already exists')
                return
            if not os.path.isdir(fulldir):
                os.makedirs(fulldir)
            open(fullfile, 'w').write(yaml.dump(dict()))
            topl.destroy()
            self.scan()
        tkinter.ttk.Button(hull, text='Create', command=check).pack(side=LEFT, expand=True, fill=BOTH)
        tkinter.ttk.Button(hull, image=self.root.pool['i:iconic/red/x_14x14.png'], command=topl.destroy).pack(side=LEFT, fill=Y)

        tkmisc.center(topl, self)

    def add_entry(self):
        item = self.tree.focus()
        if not item: return
        indexpath = self.get_index(item)
        if not indexpath: return
        indexdir = os.path.dirname(indexpath)

        topl = tkinter.Toplevel(self)
        topl.title('New Entry')
        topl.transient(self)
        topl.grab_set()
        topl.focus_set()

        topl.columnconfigure(0, weight=1)
        topl.rowconfigure(10, weight=1)

        tkinter.ttk.Label(topl, text='Choose an entry type:').grid(column=0, row=0, sticky='WE')
        choose = tkinter.IntVar()
        tkinter.ttk.Radiobutton(topl, text='Movie / File', variable=choose, value=1).grid(column=0, row=1, sticky='WE')
        tkinter.ttk.Radiobutton(topl, text='TV / Video Series', variable=choose, value=2).grid(column=0, row=2, sticky='WE')
        tkinter.ttk.Separator(topl, orient=HORIZONTAL).grid(column=0, row=3, sticky='WE')

        titleentry = tkmisc.AdvEntry(topl, ghost='Title', width=40)
        titleentry.grid(column=0, row=4, sticky='WE')

        #Begin file specific entries
        filevar = tkinter.StringVar()
        fileentry = tkmisc.AdvEntry(topl, ghost='File (relative to index)', textvariable=filevar)
        fileentry.grid(column=0, row=5, sticky='WE')
        def choosefile():
            filepath = tkinter.filedialog.askopenfilename(initialdir=indexdir)
            if not filepath: return
            filepath = os.path.normpath(filepath)
            try:
                rel = os.path.relpath(filepath, indexdir)
                filevar.set(rel)
            except ValueError:
                tkinter.messagebox.showerror('Error', 'This program\'s indexing system uses paths relative to the index files, and you provided a file mounted on a different drive. It\'s recommended you copy the file into the same directory as the index file.')
        filebutton = tkinter.ttk.Button(topl, text='Choose File', command=choosefile)
        filebutton.grid(column=0, row=6, sticky='WE')

        #Begin series specific entries
        tagentry = tkmisc.AdvEntry(topl, ghost='Series tag')
        tagentry.grid(column=0, row=7, sticky='WE')
        direntry = tkmisc.AdvEntry(topl, ghost='Subdirectory (optional)')
        direntry.grid(column=0, row=8, sticky='WE')

        imdbentry = tkmisc.AdvEntry(topl, ghost='IMDb id (ex. ttXXXXXX)')
        imdbentry.grid(column=0, row=9, sticky='WE')

        def typechange(*args):
            choice = choose.get()
            if choice == 1:
                tagentry.grid_remove()
                direntry.grid_remove()
                fileentry.grid()
                filebutton.grid()
            elif choice == 2:
                fileentry.grid_remove()
                filebutton.grid_remove()
                tagentry.grid()
                direntry.grid()
        choose.trace('w', typechange)
        choose.set(1)

        hull = tkinter.ttk.Frame(topl)
        hull.grid(column=0, row=10, sticky='WESN', padx=5, pady=5)

        def check():
            data = yaml.load(open(indexpath, 'rb').read()) or {}
            choice = choose.get()
            if not titleentry.get():
                tkinter.messagebox.showerror('Error', 'No title provided')
            if choice == 1:
                if not fileentry.get():
                    tkinter.messagebox.showerror('Error', 'No file provided')
                if not 'file' in data:
                    data['file'] = []
                data['file'].append({
                    'title': titleentry.get(),
                    'file': fileentry.get(),
                    'imdb': imdbentry.get() or None
                })
            elif choice == 2:
                if not tagentry.get():
                    tkinter.messagebox.showerror('Error', 'No series tag provided')
                if not 'series' in data:
                    data['series'] = []
                data['series'].append({
                    'title': titleentry.get(),
                    'tag': tagentry.get(),
                    'imdb': imdbentry.get() or None
                })
            else:
                return
            open(indexpath, 'wb').write(yaml.dump(data).encode())
            topl.destroy()
            self.scan()
        tkinter.ttk.Button(hull, text='Create', command=check).pack(side=LEFT, expand=True, fill=BOTH)
        tkinter.ttk.Button(hull, image=self.root.pool['i:iconic/red/x_14x14.png'], command=topl.destroy).pack(side=LEFT, fill=Y)

        tkmisc.center(topl, self)

    def edit_entry(self):
        item = self.tree.focus()
        if not item: return
        indexpath = self.get_index(item)
        if not indexpath: return
        indexdir = os.path.dirname(indexpath)

        entry = self.get_entry(item)

        topl = tkinter.Toplevel(self)
        topl.transient(self)
        topl.grab_set()
        topl.focus_set()

        if entry is None:
            topl.title('Edit Index')
            frm = tkinter.ttk.Frame(topl)
            frm.pack(expand=True, fill=BOTH, padx=5, pady=5)

            frm.rowconfigure(1, weight=1)
            frm.columnconfigure(0, weight=1)
            frm.columnconfigure(1, weight=1)

            def delete():
                if not tkinter.messagebox.askyesno('Confirm', 'Are you sure you wish to delete this index? No files inside the directory will be touched other than the index file.'):
                    return
                os.remove(indexpath)
                topl.destroy()
                self.scan()

            tkinter.ttk.Label(frm, text=indexpath, anchor=CENTER).grid(column=0, row=0, columnspan=2, sticky='WE')
            tkinter.ttk.Button(frm, image=self.root.pool['i:iconic/red/trash_stroke_32x32.png'], command=delete).grid(column=0, row=1, sticky='WESN')
            tkinter.ttk.Button(frm, image=self.root.pool['i:iconic/gray_dark/x_28x28.png'], command=topl.destroy).grid(column=1, row=1, sticky='WESN')
        else:
            topl.title('Edit Entry')
            (entrytype, entry) = entry
            data = yaml.load(open(indexpath, 'rb').read())
            entrydata = data[entrytype][entry]

            topl.columnconfigure(1, weight=1)

            i = 0
            entries = []
            for key in entrydata:
                tkinter.ttk.Label(topl, text=key).grid(column=0, row=i, sticky='E')
                ent = tkinter.ttk.Entry(topl, width=40)
                ent.grid(column=1, row=i, sticky='WE')
                if entrydata[key] is None:
                    ent.insert(0, '')
                else:
                    ent.insert(0, entrydata[key])
                entries.append((key, ent))
                i += 1

            topl.rowconfigure(i + 1, weight=1)
            hull = tkinter.ttk.Frame(topl)
            hull.grid(column=0, row=i + 1, columnspan=2, sticky='WESN', padx=5, pady=5)

            def save(delete=False):
                if delete:
                    del data[entrytype][entry]
                else:
                    for (key, obj) in entries:
                        entrydata[key] = obj.get()
                    data[entrytype][entry] = entrydata
                open(indexpath, 'wb').write(yaml.dump(data).encode())
                topl.destroy()
                self.scan(entrydata['title'])
            tkinter.ttk.Button(hull, text='Save', command=save).pack(side=LEFT, expand=True, fill=BOTH)
            tkinter.ttk.Button(hull, image=self.root.pool['i:iconic/red/trash_stroke_16x16.png'], command=lambda: save(True)).pack(side=LEFT, fill=Y)
            tkinter.ttk.Button(hull, image=self.root.pool['i:iconic/gray_dark/x_14x14.png'], command=topl.destroy).pack(side=LEFT, fill=Y)

        tkmisc.center(topl, self)

if __name__ == '__main__':
    #Menu()
    menu = Menu(mainloop=False)
    tkmisc.MainloopErrorMonitor(menu)