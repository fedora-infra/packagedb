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
# Fedora Project Author(s): Ionuț Arțăriși <mapleoin@fedoraproject.org>
#
'''
Controller for Tag related retrieval and updating of information.
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

log = logging.getLogger('pkgdb.tags')

class Tags(controllers.Controller):
    '''Retrieve/search and enter tags

    '''

    def __init__(self, app_title=None):
        '''Create a Tags Controller.

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title
        self.list = Letters(app_title)

    @expose(allow_json=True)
    @validate(validators={
        # get a list even if only one string is provided
        "apps": validators.Set()})
    def packages(self, apps):
        '''Retrieve all tags belonging to one or more PackageBuilds.

        :arg apps: The name (or list of names) of a generic PackageBuild
        to lookup
        '''

        if apps.__class__ != [].__class__:
            apps = [apps]
        #pylint:disable-msg=E1101
        tags = session.query(Tag).join(Tag.applications).filter(
            Application.name.in_(apps)).all()
        #pylint:enable-msg=E1101
                
        return dict(title=self.app_title, tags=tags)

    @expose(allow_json=True)
    def scores(self, app):
        '''Return a dictionary of tagname: score for a given package build.

        :arg app: The application name to lookup.
        '''
        #pylint:disable-msg=E1101
        apptags = session.query(Application).filter_by(name=app).one().scores
        #pylint:enable-msg=E1101

        return dict(title=self.app_title, buildtags=apptags)


    @expose(allow_json=True)
    def search(self, tags, operator='OR'):
        '''Retrieve all the builds which have a specified set of tags.

        Can also be used with just one tag.

        :arg tags: One or more tag names to lookup
        :kwarg operator: Can be one of 'OR' and 'AND', case insensitive, decides
        how the search for tags is done.
        
        Returns:
        :tags: a list of Tag objects
        :builds: list of found PackageBuild objects
        '''
        #pylint:disable-msg=E1101
        apps = Application.search(tags, operator)
        #pylint:enable-msg=E1101
        return dict(title=self.app_title, tags=tags, apps=apps)

    @expose(template='pkgdb.templates._tags', allow_json=True)
    # FIXME: if auth expires let the user know
    @identity.require(identity.not_anonymous())
    def add(self, apps, tags):
        '''Add a set of tags to a specific PackageBuild.

        This method will tag all packagebuilds in the given list. The tags are
        added to all the packagebuilds with the same name.
        
        :arg apps: one or more PackageBuild names to add the tags to.
        :kwarg tags: one or more tags to add to the packages.

        Returns a dictionary of tag: score if only one packagebuild is given.
        '''
        
        if tags == '' and request_format() != 'json':
            flash('Tag name can not be null.')
            raise redirect(request.headers.get("Referer", "/"))
       
        Application.tag(apps, tags)

        # we only get one build from the webUI
        if apps.__class__ != [].__class__:
            # get the scores dict with the new tags
            if is_xhr():
                #pylint:disable-msg=E1101
                app = session.query(Application).filter_by(name=apps).first()
                #pylint:enable-msg=E1101
                return dict(tagscore=app.scores)
            # return the user to the tagging page if all is well and no AJAX
            elif 'json' not in request_format():
                raise redirect(request.headers.get("Referer", "/"))

