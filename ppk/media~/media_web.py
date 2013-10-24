import os
import re
import sys
import uuid
import time
import random
import wsgiref.handlers

from threading import Thread
from subprocess import Popen, PIPE

import sqlalchemy
import bottle
import yaml

import ppk
import tkprops
from media_db import Session, Series, Episode, Movie
import persist
import lru

import users

@bottle.get('/favicon.ico')
def favicon():
    return bottle.static_file('film.png', '')

@bottle.get( '/media/static/<path:path>' )
def static( path ):
    return bottle.static_file( path, 'static' )

@bottle.get('/media')
@bottle.view('index')
def index():
    return {
        'download': bottle.request.query.download,
        'max': sqlalchemy.func.max,
        'db': Session(),
        'Series': Series,
        'Episode': Episode,
        'Movie': Movie,
    }

@bottle.get('/media/stream')
@bottle.view('stream')
def stream():
    query = bottle.request.query
    db = Session()
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
    key = str(uuid.uuid4())
    filecache[key] = path
    #filecache.sync()
    return { 'title': title, 'file': '/media/file/' + key }
    #return bottle.HTTPError(410, "Feature temporarily removed" )

@bottle.get('/media/file/<key>')
def open_file(key):
    if not key in filecache:
        return bottle.HTTPError(404, 'Invalid key')
    path = filecache[key]
    
    return bottle.static_file(*os.path.split(path)[::-1], download=False, mimetype='video/x-msvideo')
    
    '''if os.path.isfile(path): 
        fp = open(path, 'rb') 
    else:
        return bottle.HTTPError(404)
    if 'wsgi.file_wrapper' in bottle.request.environ:
        print('lol!')
        return bottle.request.environ['wsgi.file_wrapper'](fp)
    else:
        print('lol2!')
        #import wsgiref.handlers
        #return wsgiref.handlers.FileHandler.wsgi_file_wrapper(fp)
        import wsgiref.util
        return wsgiref.util.FileWrapper(fp)'''
    
    #bottle.response.content_type = 'application/x-vlc-plugin'
    #print( path, bottle.request.environ['wsgi.file_wrapper'] )
    #
    #print( bottle.request.environ['wsgi.file_wrapper'] )
    #
    #return wsgiref.util.FileWrapper(fp)
    '''url = 'http://localhost:8080/' + key
    cmd = '"{0}" -vvv "{1}" --sout "#standard{{access=http,mux=ogg,dst={2}}}"'.format( props['vlc-path'], path, url )
    vlc = Popen( cmd )
    time.sleep(1)
    bottle.redirect( url )'''
    '''else: 
        f = fp.read() 
        fp.close() 
        return f'''
"""def open_file(key):
    if not key in cache:
        return bottle.HTTPError(404, 'Invalid key')
    path = cache[key]
    split = os.path.split(path)
    #return bottle.static_file(split[1], split[0], download=True)
    #return open( path, 'rb' )
    return bottle.HTTPError(410, "Feature temporarily removed" )"""

@bottle.get('/')
@bottle.view('root')
def root():
    return { 'bottle': bottle }

@bottle.get('/test')
def test():
    return 'Success!'

base = os.path.expanduser( '~/.media' )
if not os.path.isdir( base ):
    os.mkdir( base )
propsFile = os.path.join( base, 'props' )

pool = ppk.Pool()
pool.include()
props = tkprops.Reader( propsFile, yaml.load( pool[ 'media/props.yaml' ] ) )

#filecache = lru.LRU(3)
filecache = persist.PersistentDict( os.path.join( base, 'cache' ) )
#filecache['null'] = None
#filecache.sync()

pattern = re.compile( props.get( 'pattern-episodic' ) )


bottle.run( host="0.0.0.0", port=80, server='rocket')