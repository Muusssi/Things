
import json
import os
import sys

import tornado.httpserver
import tornado.ioloop
import tornado.web

from tornado_swagger.setup import setup_swagger

import database as db
from view_handlers import URLS
from things_api import API_URLS

APP_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
STATIC_DIRECTORY = os.path.abspath(os.path.join(APP_DIRECTORY, 'static'))
TEMPLATES_DIRECTORY = os.path.abspath(os.path.join(APP_DIRECTORY, 'templates'))

def load_config_file(config_file):
    with open(config_file, 'r') as f:
        return json.load(f)

class Application(tornado.web.Application):
    def __init__(self, database):
        handlers = []
        handlers.extend(URLS)
        handlers.extend(API_URLS)

        settings = dict(
            cookie_secret='foobar',
            template_path=TEMPLATES_DIRECTORY,
            static_path=STATIC_DIRECTORY,
            debug=True,
        )

        self.database = database
        setup_swagger(handlers,
                      swagger_url="/data/doc",
                      description='System of Things',
                      api_version='0.1.0',
                      title='Things API')
        tornado.web.Application.__init__(self, handlers, **settings)


if __name__ == "__main__":
    config = load_config_file(sys.argv[1])
    httpserver = tornado.httpserver.HTTPServer(Application(db.Database(config)))
    httpserver.listen(int(config['port']))
    print('Running on port {}'.format(config['port']))
    tornado.ioloop.IOLoop.current().start()
