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

from turbogears import controllers, expose, identity, redirect
from turbogears.database import session

from cherrypy import request

from fedora.tg.util import request_format

from pkgdb.model import Branch, Comment, Language, PackageBuild, Repo, Application
from pkgdb.utils import mod_grp, is_xhr
import logging
log = logging.getLogger('pkgdb.comments')

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
    @expose(template='pkgdb.templates._comments', allow_json=True)
    def add(self, author, body, app, language='en_US'):
        '''Add a new comment to a packagebuild.

        :arg author: the FAS author of the comment
        :arg body: text body of the comment
        :arg app: the name of the application to search for
        :kwarg language: the language that the comment was written in
        '''
        application = session.query(Application).filter_by(name=app).first()
        application.comment(author, body, language)
        #session.flush()

        if is_xhr():
            # give AJAX the new comments
            # FIXME: though it is just once in the db, the last inserted comment is in application.comments twice
            return dict(comments = application.comments, app=application)
        elif request_format() != 'json':
            # reload the page we came from
            raise redirect(request.headers.get("Referer", "/"))

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
        
        packagebuild = PackageBuild.query.filter(PackageBuild.name==build
                                                 ).first()

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

        if request_format != 'json':
            # reload the page we came from
            raise redirect(request.headers.get("Referer", "/"))
