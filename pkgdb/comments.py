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
Controller for displaying Comments related information.
'''

from sqlalchemy.sql import and_, or_

from turbogears import controllers, expose, identity

from pkgdb.model import Branch, Comment, Language, PackageBuild, Repo
from pkgdb.utils import mod_grp

REPO = 'F-11-i386'
class Comments(controllers.Controller):
    '''Retrieve, enter and moderate comments.

    '''

    def __init__(self, app_title=None):
        '''Create a Comment Controller.

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title

    @identity.require(identity.not_anonymous())
    @expose(allow_json=True)
    def add(self, author, body, build, language='en_US'):
        '''Add a new comment to a packagebuild.

        :arg author: the FAS author of the comment
        :arg body: text body of the comment
        :arg build: the name of the packagebuild to search for
        :kwarg language: the language that the comment was written in
        '''
        packagebuild = PackageBuild.query.filter(PackageBuild.name==build).one()

        packagebuild.comment(author, body, language)

    @expose(allow_json=True)
    def author(self, author, language='en_US'):
        '''Retrieve all the comments of a specific author.

        :arg author: the FAS author of the comment
        :kwarg language: the language that the comments were written in
        '''
        lang = Language.find(language)

        comments = Comment.query.filter(and_(Comment.language==lang,
                                             Comment.author==author)).all()

        return dict(title=self.app_title, comments=comments)

    @expose(allow_json=True)
    def build(self, build, language='en_US'):
        '''Return all the comments on a given packagebuild.

        :arg build: the name of the packagebuild to search for
        :kwarg language: the language that the comments were written in
        '''
        lang = Language.find(language)
        
        packagebuild = PackageBuild.query.filter(PackageBuild.name==build).one()

        comments = Comment.query.filter(and_(
            Comment.packagebuildname==packagebuild.name,
            Comment.language==lang)).all()

        return dict(title=self.app_title, comments=comments)

    @identity.require(identity.in_group(mod_grp))
    @expose(allow_json=True)
    def toggle_published(self, commentid):
        '''Publish or unpublish a given comment

        :arg commentid: the id of the Comment
        '''
        comment = Comment.query.filter_by(id=commentid).one()

        if comment.published:
            comment.published=False
        else:
            comment.published=True
