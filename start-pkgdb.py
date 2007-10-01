#!/usr/bin/python
__requires__ = 'TurboGears[future]'
import pkg_resources

from turbogears import config, update_config, start_server
import cherrypy
cherrypy.lowercase_api = True
import os.path
import sys

CONFDIR=@CONFDIR@
PKGDBDIR=os.path.join(@DATADIR@, 'packagedb')

# first look on the command line for a desired config file,
# if it's not on the command line, then
# look for setup.py in this directory. If it's not there, this script is
# probably installed
if len(sys.argv) > 1:
    update_config(configfile=sys.argv[1], 
        modulename="pkgdb.config")
elif exists(join(os.path.dirname(__file__), "setup.py")):
    update_config(configfile="dev.cfg",modulename="pkgdb.config")
else:
    update_config(configfile=os.path.join(CONFDIR,'pkgdb.cfg'),modulename="pkgdb.config")

sys.path.append(PKGDBDIR)

from pkgdb.controllers import Root

start_server(Root())
