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
#                           Martin Bacovsky <mbacovsk@redhat.com>
#
'''
Controller for displaying PackageBuild(Rpm) related information
'''
#
#pylint Explanations
#

# :E1101: SQLAlchemy monkey patches database fields into the mapper classes so
#   we have to disable this when accessing an attribute of a mapped class.

from sqlalchemy.sql import and_
from sqlalchemy.exceptions import InvalidRequestError

from turbogears import controllers, expose, identity, redirect
from turbogears.database import session

from pkgdb.model import Comment, Application
from pkgdb.utils import mod_grp
from pkgdb import _

from fedora.tg.util import request_format

import logging
log = logging.getLogger('pkgdb.applications')

class ApplicationController(controllers.Controller):
    '''Display general information related to Applicaiton.
    '''

    def __init__(self, app_title=None):
        '''Create a Applications Controller

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title

    @expose(template='pkgdb.templates.application', allow_json=True)
    def default(self, app_name=None, repo='F-11-i386', language='en_US'):
        '''Retrieve application by its name.

        :arg app_name: Name of the packagebuild/rpm to lookup
        :arg repo: shortname of the repository to look in
        :arg language: A language string, (e.g. 'American English' or 'en_US')
        '''
        if app_name == None:
            raise redirect('/')

        # look for The One application
        try:
            #pylint:disable-msg=E1101
            application = session.query(Application).filter_by(name=app_name).\
                    one()
            #pylint:enable-msg=E1101
        except InvalidRequestError, e:
            error = dict(status=False,
                         title=_('%(app)s -- Invalid Application Name') % {
                             'app': self.app_title},
                             message=_('The application you were linked to'
                             ' (%(app)s) does not exist in the Package '
                             ' Database. If you received this error from a link'
                             ' on the fedoraproject.org website, please report'
                             ' it.') % {'app': app_name})
            if request_format() != 'json':
                error['tg_template'] = 'pkgdb.templates.errors'
                return error
        
        tagscore = application.scores_by_language(language)

        #pylint:disable-msg=E1101
        comment_query = session.query(Comment).filter(and_(
            Comment.application==application,
            Comment.language==language)).order_by(Comment.time)
        #pylint:enable-msg=E1101
        # hide the mean comments from ordinary users
        if identity.in_group(mod_grp):
            comments = comment_query.all()
        else:
            comments = comment_query.filter_by(published=True).all()

        return dict(title=_('%(title)s -- %(app)s') % {
            'title': self.app_title, 'app': application.name},
                    tagscore=tagscore, language=language,
                    app=application,
                    comments=comments)
