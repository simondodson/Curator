import os
from bottle import Bottle, static_file
import bottle

import mimetypes

import ppk as _ppk

# default configuration
_config = {
    'root': None,
}


class StaticFileRepository:
    """This repository is home to our core business logic"""
    def __init__(self, root):
        if not os.path.exists(root):
            raise FileNotFoundError(root)
        self.root = root
    
    def get(self, filename):
        download = bool(bottle.request.params.download)
        return static_file(filename, root=self.root, download=download)
        

def static(root=None):    
    app = Bottle()
    repo = StaticFileRepository(root)
    
    @app.get('/:filename#.+#')
    def get(filename):
        """Locally scoped proxy for the actual repo action we 
        wish to call. This evil hack is needed because of functools' 
        poor implementation of update_wrapper. 
        See: 
         - https://github.com/defnull/bottle/issues/223
         - http://bugs.python.org/issue3445"""
        return repo.get(filename)
        
    return app

def ppk(pool=None, include=None):
    app = Bottle()
    app.pool = pool or _ppk.Pool()

    if isinstance(include, str):
        app.pool.include(include)

    @app.get('/<path:path>')
    def get(path):
        data = app.pool['f:' + path]
        if not data: return bottle.HTTPError(404)
        bottle.response.content_type = mimetypes.guess_type(path)[0]
        return data

    return app