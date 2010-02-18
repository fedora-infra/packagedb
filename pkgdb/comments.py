# -*- coding: utf-8 -*-
#
# Copyright © 2009  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2, or (at your option) any later version.  This
# program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the GNU
# General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA. Any Red Hat trademarks that are incorporated in the source
# code or documentation are not subject to the GNU General Public License and
# may only be used or replicated with the express permission of Red Hat, Inc.
#
# Fedora Project Author(s): Ionuț Arțăriși <mapleoin@fedoraproject.org>
#
'''
Controller for displaying Comments related information.
'''
#
#pylint Explanations
#

# :E1101: SQLAlchemy monkey patches database fields into the mapper classes so
#   we have to disable this when accessing an attribute of a mapped class.

from sqlalchemy.sql import and_

from turbogears import controllers, expose, identity, redirect
from turbogears.database import session

from cherrypy import request

from fedora.tg.util import request_format

from pkgdb.model import Comment, PackageBuild, Application
from pkgdb.lib.utils import mod_grp, is_xhr
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
    def add(self, author, body, app):
        '''Add a new comment to a packagebuild.

        :arg author: the FAS author of the comment
        :arg body: text body of the comment
        :arg app: the name of the application to search for
        '''
        #pylint:disable-msg=E1101
        application = session.query(Application).filter_by(name=app).first()
        application.comment(author, body)

        comment_query = session.query(Comment)\
                .filter(Comment.application==application)\
                .order_by(Comment.time)
        #pylint:enable-msg=E1101
        # hide the mean comments from ordinary users
        if identity.in_group(mod_grp):
            comments = comment_query.all()
        else:
            comments = comment_query.filter_by(published=True).all()

        if is_xhr():
            # give AJAX the new comments
            return dict(comments = comments, app=application)
        elif request_format() != 'json':
            # reload the page we came from
            raise redirect(request.headers.get("Referer", "/"))

    @expose(allow_json=True)
    def author(self, author):
        '''Retrieve all the comments of a specific author.

        :arg author: the FAS author of the comment
        '''

        #pylint:disable-msg=E1101
        comments = Comment.query.filter(Comment.author==author).all()
        #pylint:enable-msg=E1101

        return dict(title=self.app_title, comments=comments)

    @expose(allow_json=True)
    def build(self, build):
        '''Return all the comments on a given packagebuild.

        :arg build: the name of the packagebuild to search for
        '''
        
        #pylint:disable-msg=E1101
        packagebuild = PackageBuild.query.filter(PackageBuild.name==build
                                                 ).first()

        comments = Comment.query.filter(
            Comment.packagebuildname==packagebuild.name).all()
        #pylint:enable-msg=E1101

        return dict(title=self.app_title, comments=comments)

    @identity.require(identity.in_group(mod_grp))
    @expose(allow_json=True)
    def toggle_published(self, commentid):
        '''Publish or unpublish a given comment

        :arg commentid: the id of the Comment
        '''
        #pylint:disable-msg=E1101
        comment = Comment.query.filter_by(id=commentid).one()
        #pylint:enable-msg=E1101

        if comment.published:
            comment.published = False
        else:
            comment.published = True

        if request_format != 'json':
            # reload the page we came from
            raise redirect(request.headers.get("Referer", "/"))
