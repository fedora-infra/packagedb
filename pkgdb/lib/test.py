# -*- coding: utf-8 -*-
#
# Copyright © 2007-2010  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2, or (at your option) any later version.  This
# program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the GNU
# General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA. Any Red Hat trademarks that are incorporated in the source
# code or documentation are not subject to the GNU General Public License and
# may only be used or replicated with the express permission of Red Hat, Inc.
#
# Red Hat Author(s): Martin Bacovsky <mbacovsk@redhat.com>
#
"""
Library with helpers making tests more readable
"""

from sqlalchemy import Table, Column, Integer, String
from sqlalchemy import ForeignKey, MetaData, create_engine

from turbogears import config, update_config, startup, database
import turbogears
from turbogears.util import get_model
import os
from unittest import TestCase
import atexit
import cherrypy
import cherrypy._cpwsgi
import fedora.tg.utils
from webtest import TestApp

cherrypy_major_ver = int(cherrypy.__version__.split('.')[0])
#if cherrypy_major_ver < 3:
#    from cherrypy._cphttptools import Request, Response
#else:
#    from cherrypy import Request, Response

# try to load test.cfg to setup testing database
# in memory sqlite is set by default
if os.path.exists('test.cfg'):
    for w in os.walk('.'):
        if w[0].endswith(os.sep + 'config') and not os.sep + '.' in w[0]:
            modulename = "%s.app" % w[0][2:].replace(os.sep, ".")
            break
    else:
        modulename = None
    update_config(configfile="test.cfg", modulename=modulename)
    # use database.admin_dburi as primary dburi during tests
    if config.get('database.admin_dburi', False):
        database.set_db_uri(config.get('database.admin_dburi'), 'sqlalchemy')
else:
    database.set_db_uri("sqlite:///:memory:")

config.update({'global':
        {'autoreload.on': False, 'tg.new_style_logging': True}})

# a few methods borrowed from testutils of TG1.1

def make_wsgiapp():
    """Return a WSGI application from cherrypy's root object."""
    if cherrypy_major_ver < 3:
        wsgiapp = cherrypy._cpwsgi.wsgiApp
    else:
        #This is untested but should work.. if not, one of the others will
        wsgiapp = cherrpy.root
        #wsgiapp = cherrypy.tree.mount(cherrypy.root, '/')
        #wsgiapp = cherrypy.wsgi.CPWSGIServer
    return wsgiapp


def make_app(controller=None):
    """Return a WebTest.TestApp instance from Cherrypy.
    If a Controller object is provided, it will be mounted at the root level.
    If not, it'll look for an already mounted root.
    """
    if controller:
        wsgiapp = mount(controller(), '/')
    else:
        wsgiapp = make_wsgiapp()
    testapp = TestApp(wsgiapp)

    return testapp


def unmount():
    """Remove an application from the object traversal tree."""
    # There's no clean way to remove a subtree under CP2, so the only use case
    #  handled here is to remove the entire application.
    # Supposedly, you can do a partial unmount with CP3 using:
    #  del cherrypy.tree.apps[path]
    cherrypy.root = None
    cherrypy.tree.mount_points = {}


def start_server():
    """Start the server if it's not already."""
    if not config.get("cp_started"):
        if cherrypy_major_ver < 3:
            cherrypy.server.start(serverClass=None, initOnly=True)
        else:
            cherrypy.server.quickstart()
            cherrypy.engine.start()
        config.update({"cp_started" : True})

    if not config.get("server_started"):
        startup.startTurboGears()
        config.update({"server_started" : True})


def stop_server(tg_only = False):
    """Stop the server and unmount the application.  \
    Use tg_only = True to leave CherryPy running (for faster tests).
    """
    unmount()
    if config.get("cp_started") and not tg_only:
       cherrypy.server.stop()
       config.update({"cp_started" : False})
   
    if config.get("server_started"):
        startup.stopTurboGears()
        config.update({"server_started" : False})


def mount(controller, path="/"):
    """Mount a controller at a path.  Returns a wsgi application."""
    if path == '/':
        cherrypy.root = controller
    else:
        cherrypy.tree.mount(controller, path)
    return make_wsgiapp()



class DBTest(TestCase):
    """TestCase using db model of pkgdb

    During init the testcase make sure DB is created.
    For performance reasons the test DB is created only once 
    for whole test suite. Thus each test is responsible for
    cleaning after itself.
    """
    
    def __init__(self, methodName='runTest'):
        super(DBTest, self).__init__(methodName)
        from turbogears.database import session, metadata
        self.session = session
        self.metadata = metadata
        self.model = get_model()

    def setUp(self):
        self.metadata.create_all()


    def tearDown(self):
        # finish unfinished transaction to prevent locak during drop table
        try:
            self.session.rollback()
        except:
            pass
        self.metadata.drop_all()


class WebAppTest(DBTest):

    def __init__(self, methodName='runTest'):
        super(WebAppTest, self).__init__(methodName)

    def _init_env(self):
        import pkgdb.lib.utils
        pkgdb.lib.utils.init_globals()
        turbogears.startup.call_on_startup.append(fedora.tg.utils.enable_csrf)

    def _init_app(self, controller, path):
        mount(controller, path)
        self.app = make_app()
        start_server()


    def setUp(self):
        super(WebAppTest, self).setUp()
        self._init_env()
        from pkgdb.controllers import Root
        self._init_app(Root(), '/')


    def tearDown(self):
        stop_server(tg_only = True)
        del self.app
        super(WebAppTest, self).tearDown()


    def login_user(self, user):
        #TODO: test me!
        """ Log a specified user object into the system """
        self.app.post(config.get('identity.failure_url'), {
                'user_name' : user.user_name,
                'password'  : user.password,
                'login'     : 'Login',
        })


class BrowsingSession(object):
    #TODO: test me!

    def __init__(self):
        self.visit = None
        self.response, self.status = None, None
        self.cookie = Cookie.SimpleCookie()
        self.app = make_app()

    def goto(self, *args, **kwargs):
        if self.cookie:
            headers = kwargs.setdefault('headers', {})
            headers['Cookie'] = self.cookie_encoded
        response = self.app.get(*args, **kwargs)
        self.response = response.body
        self.status = response.status
        self.cookie = response.cookies_set
        self.cookie_encoded = response.headers.get('Set-Cookie', '')



def slow(func):
    """Decorator to mark long-running tests

    nose can filter marked tests 'nose -a \!slow'

    Usualy it is required for the unittests to finish quickly.
    Recommended time limit (in test-driven development approach)
    is one second for whole test suite. So if you write long-running test
    (e.g. cache expiration behaviour test, etc.) mark it with this decorator
    """

    func.slow = True
    return func


def create_stuff_table(metadata):
    """Dummy table 'stuff'
    :arg metadata: metadata
    :returns table: Table instance
    """
    return Table('stuff', metadata, 
        Column('id', Integer, autoincrement=True, primary_key=True),
        Column('data', String(50)),
    )


def create_more_stuff_table(metadata):
    """Dummy table 'more_stuff'
    :arg metadata: metadata
    :returns table: Table instance
    """
    
    return Table('more_stuff', metadata, 
        Column('id', Integer, primary_key=True),
        Column('stuff_id', Integer, ForeignKey('stuff.id')),
        Column('data', String(50)),
    )


def number_of_tables(metadata):
    """Count tables in metadata
    :arg metadata: metadata
    :return int: number of tables
    """
    return len(metadata.tables.keys())


def bound_metadata(echo=False):
    """Create metadata bound to sqlite engine
    :arg echo: set engine to spit out SQL commands
    :return metadata: metadata
    """
    engine = create_engine(config.get('sqlalchemy.dburi'), pool_size=1, echo=echo)
    conn = engine.connect()
    return MetaData(engine)


def unbound_metadata():
    """Create metadata
    :return metadata: metadata
    """
    return MetaData()


def table_names(metadata):
    """List of table names defined in metadata
    :arg metadata: metadata
    :return set: list of table names
    """
    names = [t.name for t in metadata.tables.values()]
    return set(names)


