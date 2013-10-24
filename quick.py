import bottle

@bottle.route('/')
def index():
	return 'Hello, World!'

bottle.run(host='0.0.0.0', port=80, server='rocket')