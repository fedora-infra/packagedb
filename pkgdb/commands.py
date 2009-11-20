# -*- coding: utf-8 -*-
"""This module contains functions called from console script entry points."""

import sys
import pkgdata
sys.path.append(pkgdata.get_location('public_code'))

from pkgdb.utils import init_globals
init_globals()

from os import getcwd
from os.path import dirname

import pkg_resources
pkg_resources.require("TurboGears>=1.0.4.4")
pkg_resources.require("SQLAlchemy>=0.3.10")

import cherrypy
import turbogears

cherrypy.lowercase_api = True


class ConfigurationError(Exception):
    pass


def start():
    """Start the CherryPy application server."""

    setupdir = dirname(dirname(__file__))
    curdir = getcwd()

    # First look on the command line for a desired config file,
    # if it's not on the command line then load pkgdb.cfg from the sysconfdir
    if len(sys.argv) > 1:
        configfile = sys.argv[1]
    else:
        configfile = pkgdata.get_filename('pkgdb.cfg', 'config')

    turbogears.update_config(configfile=configfile,
        modulename="pkgdb.config")

    from pkgdb.controllers import Root

    turbogears.start_server(Root())
