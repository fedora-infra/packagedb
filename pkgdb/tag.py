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

import logging
from sqlalchemy.sql import and_, or_
from turbogears import controllers, expose, redirect, identity, flash, \
                       validate, validators
from turbogears.database import session
from cherrypy import request
from fedora.tg.util import request_format

from pkgdb.model import Tag, Language, PackageBuild, Application
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
        "builds": validators.Set()})
    def packages(self, builds):
        '''Retrieve all tags belonging to one or more PackageBuilds.

        :arg builds: The name (or list of names) of a generic PackageBuild
        to lookup
        '''

        if builds.__class__ != [].__class__:
            builds = [builds]
        tags = Tag.query.join(Tag.buildnames).filter(
            PackageBuildName.name.in_(builds)).all()
                
        return dict(title=self.app_title, tags=tags)

    @expose(allow_json=True)
    def scores(self, build, language='en_US'):
        '''Return a dictionary of tagname: score for a given package build.

        :arg build: The PackageBuild object to lookup.
        :kwarg language: A language, short ('en_US') or long ('American English')
        format. Look for them on https://translate.fedoraproject.org/languages/
        '''

        buildtags = PackageBuildName.query.filter_by(name=build).one().scores()
        return dict(title=self.app_title, buildtags=buildtags)


    @expose(allow_json=True)
    def search(self, tags, operator='OR', language='en_US'):
        '''Retrieve all the builds which have a specified set of tags.

        Can also be used with just one tag.

        :arg tags: One or more tag names to lookup
        :kwarg operator: Can be one of 'OR' and 'AND', case insensitive, decides
        how the search for tags is done.
        :kwarg language: A language, short ('en_US') or long ('American English')
        format. Look for them on https://translate.fedoraproject.org/languages/
        
        Returns:
        :tags: a list of Tag objects, filtered by :language:
        :builds: list of found PackageBuild objects
        '''

        builds = PackageBuild.search(tags, operator, language)
        return dict(title=self.app_title, tags=tags, builds=builds)

    @expose(template='pkgdb.templates._tags', allow_json=True)
    # FIXME: if auth expires let the user know
    @identity.require(identity.not_anonymous())
    def add(self, apps, tags, language='en_US'):
        '''Add a set of tags to a specific PackageBuild.

        This method will tag all packagebuilds in the given list. The tags are
        added to all the packagebuilds with the same name.
        
        :arg apps: one or more PackageBuild names to add the tags to.
        :kwarg tags: one or more tags to add to the packages.
        :kwarg language: name or shortname for the language of the tags.

        Returns a dictionary of tag: score if only one packagebuild is given.
        '''
        
        if tags == '' and request_format() != 'json':
            flash('Tag name can not be null.')
            raise redirect(request.headers.get("Referer", "/"))
       
        Application.tag(apps, tags, language)

        # we only get one build from the webUI
        if apps.__class__ != [].__class__:
            # get the scores dict with the new tags
            if is_xhr():
                app=session.query(Application).filter_by(name=apps).first()
                tagscore = app.scores_by_language(language)
                return dict(tagscore=tagscore)
            # return the user to the tagging page if all is well and no AJAX
            elif 'json' not in request_format():
                raise redirect(request.headers.get("Referer", "/"))

