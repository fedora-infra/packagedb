# -*- coding: utf-8 -*-
#
# Copyright © 2009  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.  You should have
# received a copy of the GNU General Public License along with this program;
# if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
# Fifth Floor, Boston, MA 02110-1301, USA. Any Red Hat trademarks that are
# incorporated in the source code or documentation are not subject to the GNU
# General Public License and may only be used or replicated with the express
# permission of Red Hat, Inc.
#
# Red Hat Project Author(s): Martin Bacovsky <mbacovsk@redhat.com>
#
'''
Controller for displaying PackageBuild related information
'''
#
#pylint Explanations
#

# :E1101: SQLAlchemy monkey patches database fields into the mapper classes so
#   we have to disable this when accessing an attribute of a mapped class.

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import and_, literal_column, union

from turbogears import controllers, expose, identity, redirect, flash
from turbogears import paginate
from turbogears.database import session

from pkgdb.model import Repo, PackageBuild
from pkgdb import release, _

from fedora.tg.util import request_format

from operator import itemgetter
import re


import logging
log = logging.getLogger('pkgdb.builds')

class BuildsController(controllers.Controller):
    
    def __init__(self, app_title=None):
        '''Create an Builds Controller

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title


    @expose(template='pkgdb.templates.builds')
    def default(self):
        '''Applications Home Page

        This page serves shop-window of fedora applications.
        Here you can see what's new and can search for applications
        '''

        redirect('/apps/name/list/a*')


    @expose(template='pkgdb.templates.build')
    def show(self, shortname, buildname, epoch, version, rel, arch):
        
        try:
            repo = session.query(Repo).filter_by(shortname=shortname).one()
        except NoResultFound:
            flash('Repo "%s" was not found' % shortname)
            redirect('/builds')

        try:
            build = session.query(PackageBuild).filter_by(
                name=buildname,
                epoch=epoch,
                version=version,
                release=rel,
                architecture=arch,
                repo=repo).one()
        except NoResultFound:
            flash('Build (%s-%s:%s-%s.%s) was not found' % (buildname, epoch, version, rel, arch))
            redirect('/builds')

        return dict(title=self.app_title, version=release.VERSION,
            build=build)
            

                
        


