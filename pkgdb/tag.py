# -*- coding: utf-8 -*-
#
# Copyright © 2009  Red Hat, Inc. All rights reserved.
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

from sqlalchemy.sql import and_, or_

from turbogears import controllers, expose, redirect, identity

from pkgdb.model import Tag, Language, PackageBuild, PackageBuildName
from pkgdb.letter_paginator import Letters

class Tag(controllers.Controller):
    '''Retrieve/search and enter tags

    '''

    def __init__(self, app_title=None):
        '''Create a Tags Controller.

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title
        self.list = Letters(app_title)

    @expose(allow_json=True)
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

        buildtags = PackageBuild.query.filter_by(name=build).one().scores()
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

    @expose(allow_json=True)
    @identity.require(identity.not_anonymous())
    def add(self, builds, tags, language='en_US'):
        '''Add a set of tags to a specific PackageBuild.

        This method will tag all packagebuilds in the given list.
        This is nice because it tags builds regardless of their architecture.
        
        :arg builds: one or more PackageBuild names to add the tags to.
        :kwarg tags: one or more tags to add to the packages.
        :kwarg language: name or shortname for the language of the tags.

        Returns two lists (unchanged): tags and builds.
        '''

        PackageBuild.tag(builds, tags, language)
