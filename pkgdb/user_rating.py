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
# Red Hat Author(s): Martin Bacovsky <mbacovsk@redhat.com>
#
'''
Controller for Usage related retrieval and updating of information.
'''
#
#pylint Explanations
#

# :E1101: SQLAlchemy monkey patches database fields into the mapper classes so
#   we have to disable this when accessing an attribute of a mapped class.

import logging
from turbogears import controllers, expose, redirect, identity, flash, \
                       validate, validators
from turbogears.database import session
from cherrypy import request
from fedora.tg.util import request_format

from pkgdb.model import Tag, PackageBuild, Application
from pkgdb.letter_paginator import Letters
from pkgdb.utils import is_xhr

log = logging.getLogger('pkgdb.user_rating')

class UserRatings(controllers.Controller):
    '''Retrieve/search and enter ratings

    '''

    def __init__(self, app_title=None):
        '''Create a UserRatings Controller.

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title
        self.list = Letters(app_title)


    @expose(template='pkgdb.templates._user_ratings', allow_json=True)
    # FIXME: if auth expires let the user know
    @identity.require(identity.not_anonymous())
    def add(self, app, usage, rating, author):
        '''Add a usage and rating to a specific Application

        :arg app: application name to add the tags to.
        :arg usage: usage name.
        :arg rating: rating associated with the usage
        :arg author: author of this usage and/or rating

        Returns updated application object.
        '''
        
        if (usage == '' or rating == '' or author == '') \
                and request_format() != 'json':
            flash('Usage name, rating and author has to be filled.')
            raise redirect(request.headers.get("Referer", "/applications/%s" % app))

        #FIXME: handle if app does not exist
        #pylint:disable-msg=E1101
        app_obj = session.query(Application).filter_by(name=app).one()
        #pylint:enable-msg=E1101

        app_obj.update_rating(usage, rating, author)

        if is_xhr():
            return dict(app=app_obj)
        # return the user to the tagging page if all is well and no AJAX
        elif 'json' not in request_format():
            raise redirect(request.headers.get("Referer", "/"))

