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

Be able to: add tags, retrieve tags on a package, all the package which have
a set of tags, all packages that have any one of a set of tags, The method to
add a tag should probably operate on a list of packages as well.
'''
from sqlalchemy.sql import and_, or_

from turbogears import controllers, expose, redirect

from pkgdb.model import Package, Tag, TagsTable, Language, PackageTagTable

class Tag(controllers.Controller):
    '''Retrieve and enter tags

    '''

    def __init__(self, app_title=None):
        '''Create a Tags Controller.

        :warg app_title: Title of the web app.
        '''
        self.app_title = app_title

    @expose(allow_json=True)
    def packages(self, pkgs):
        '''Retrieve all tags belonging to one or more Packages.

        :arg pkgs: The name (or list of names) of a generic Package
        to lookup

        Returns:
        :tags: A set of Tag objects

        '''
        if pkgs.__class__ != [].__class__:
            pkgs = [pkgs]

        tags = set()
        for pkg in pkgs:
            for tag in Package.query.filter_by(name=pkg).one().tags:
                tags.add(tag)

        return dict(title=self.app_title, tags=tags)

    @expose(allow_json=True)
    def scores(self, packageName, language='en_US'):
        '''Return a dictionary of tagname: score for a given package.

        :arg packageName: The Package object to lookup.
        :arg language (optional): If given, restrict the search to just one
        language.
        '''
        package = Package.query.filter_by(name=packageName).one()
        tags = package.tags

        lang = self.language(language)
        # filter on language
        for tag in tags:
            if tag.language != lang:
                tags.remove(tag)
        # build the dictionary
        packagetags = {}
        for tag in tags:
            packagetags[tag.name] = package.score(tag)

        return dict(title=self.app_title, packagetags=packagetags)


    @expose(allow_json=True)
    def search(self, tags, operator='OR', language='en_US'):
        '''Retrieve all the packages which have a specified set of tags.

        Can also be used with just one tag.

        :arg tags: One or more tag names to lookup
        :arg operator: Can be one of 'OR' and 'AND', case insensitive, decides
        how the search for tags is done.
        :arg language: A language in short ('en_US') or long ('American English')
        format. Look for them on https://translate.fedoraproject.org/languages/

        Returns:
        :tags: a list of Tag objects, filtered by :language:
        :pkgs: list of found Package objects
        '''

        lang = self.language(language)
        
        if tags.__class__ != [].__class__:
            tags = [tags]
        packages = set()

        # get the actual Tag objects
        object_tags = []
        for tag in tags:
            try:
                object_tags.append(
                    Tag.query.filter_by(name=tag, language=lang).one())
            except:
                raise Exception(tag, lang)
        tags = object_tags
                        
        if operator == 'OR':
            for tag in tags:
                pkgs = tag.packages
                for pkg in pkgs:
                    packages.add(pkg)
        elif operator == 'AND':
            packages = set(tags[0].packages)
            if len(tags) > 0:
                for tag in tags[1:]:
                    packages = set(tags[0].packages) & tag.packages
        
        return dict(title=self.app_title, tags=tags, packages=packages)

    @expose(allow_json=True)
    def add(self, pkgs, tags, language='en_US'):
        '''Add a set of tags to a specific Package.

        :arg pkgs: one or more Package names to add the tags to.
        :arg tags: one or more tags to add to the packages.
        :arg language: name or shortname for the language of the tags.

        Returns two lists: tags and pkgs.
        '''
        lang = self.language(language)
        # if we got just one argument, make it a list
        if tags.__class__ != [].__class__:
            tags = [tags]
        if pkgs.__class__ != [].__class__:
            pkgs = [pkgs]
            
        for tag in tags:
            try:
                conn = TagsTable.select(and_(
                    TagsTable.c.name==tag, TagsTable.c.language==lang
                    )).execute()
                tagid = conn.fetchone()[0]
                conn.close()
                #tagid = Tag.query.filter(and_(Tag.name==tag, Tag.language==lang)
                #                         ).one().id
            except:
                tagid = TagsTable.insert().values(name=tag, language=lang
                    ).execute().last_inserted_ids()[-1]

            for pkg in pkgs:
                try:
                    package = Package.query.filter_by(name=pkg).one()
                except:
                    # FIXME: Fail silently if none of the packages are found?
                    pass
                else:
                    # the db knows to increment the score if the packageid,
                    # tagid pair is already there.
                    PackageTagTable.insert().values(packageid=package.id,
                                                    tagid=tagid).execute()

        return dict(title=self.app_title, tags=tags, pkgs=pkgs)
    
    def language(self, language):
        '''Helper method to get a language from the db

        :arg language: string name or shortname for a language

        Returns the shortname if found, raises error otherwise.
        '''
        try:
            lang = Language.query.filter(or_(Language.name==language,
                       Language.shortname==language)).one().shortname
            return lang
        except:
            error = dict(status=False,
                         title=_('%(app)s -- Invalid Language Name') % {
                             'app': self.app_title},
                             message=_('The language you tried to use '
                             ' (%(language)s) does not appear in the Package '
                             ' Database. If you received this error from a link'
                             ' on the fedoraproject.org website, please report'
                             ' it.') % {'language': language})
            if self.request_format() != 'json':
                error['tg_template'] = 'pkgdb.templates.errors'
                return error
