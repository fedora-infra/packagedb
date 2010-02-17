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
Controller for displaying Applications related information
'''
#
#pylint Explanations
#

# :E1101: SQLAlchemy monkey patches database fields into the mapper classes so
#   we have to disable this when accessing an attribute of a mapped class.

from sqlalchemy.exceptions import InvalidRequestError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import and_, literal_column, union
from sqlalchemy import Text, Integer, func, desc

from turbogears import controllers, expose, identity, redirect, flash
from turbogears import paginate
from turbogears.database import session

from pkgdb.model import Comment, Application, Icon, IconName, PackageBuild
from pkgdb.model import Tag, Usage, ApplicationUsage, ApplicationTag
from pkgdb.model import MimeType
from pkgdb.utils import mod_grp
from pkgdb import release, _
from pkgdb.lib.text_utils import excerpt

from fedora.tg.util import request_format

from operator import itemgetter
import re


import logging
log = logging.getLogger('pkgdb.applications')

class ApplicationsController(controllers.Controller):
    
    def __init__(self, app_title=None):
        '''Create an Applications Controller

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title


    @expose(template='pkgdb.templates.apps')
    def index(self):
        '''Applications Home Page

        This page serves shop-window of fedora applications.
        Here you can see what's new and can search for applications
        '''

        redirect('/apps/name/list/a*')

    @expose(template='pkgdb.templates.apps_search')
    def search(self, pattern=''):
        '''Applications search result

        :arg pattern: pattern to be looked for in apps

        Search is performed on name, summary, description,
        tags, usages and comments. Results are sorted according 
        to relevancy. Parts where pattern was recognized are shown
        in listing.
        '''

        app_list = []
        pkg_list = []

        if pattern == '':
            flash('Insert search pattern...')

        apps = self._applications_search_query(pattern).execute()

        # merge all hits 
        merged_results = {}
        for app in apps:
            result = merged_results.get((app['name'], app['apptype']), None)
            if result is None:
                result = {
                    'name': app['name'],
                    'apptype': app['apptype'],
                    'score': 0,
                    'summary': app['summary'] or '',
                    'descr': ''.join(excerpt(app['description'], pattern, max=120, all=True)),
                    'comments': [],
                    'tags': [],
                    'mimetypes': [],
                    'usage': []
                }
            result['score'] += app['score']
            if app['foundin'] == 'Tags':
                result['tags'].append(app['data'])
            elif app['foundin'] == 'MimeTypes':
                result['mimetypes'].append(app['data'])
            elif app['foundin'] == 'Usage':
                result['usage'].append(app['data'])
            elif app['foundin'] == 'Comments':
                result['comments'].append(''.join(excerpt(app['data'], pattern, all=True)))

            merged_results[(app['name'], app['apptype'])] = result

        app_list = sorted(merged_results.values(), key=itemgetter('score'), reverse=True)
                
        return dict(title=self.app_title, version=release.VERSION,
            pattern=pattern, app_list=app_list, pkg_list=pkg_list)


    def _applications_search_query(self, pattern):
        p = re.compile(r'\W+')
        s_pattern = p.sub(' ', pattern).split(' ')

        # name
        q_name = session.query(
                Application.name,
                Application.apptype,
                Application.summary,
                Application.description,
                literal_column("'Name'", Text).label('foundin'),
                literal_column('100', Integer).label('score'),
                Application.name.label('data'))\
            .filter(
                and_(
                    Application.desktoptype == 'Application',
                    Application.apptype == 'desktop', 
                    *(Application.name.ilike('%%%s%%' % p) for p in s_pattern)
                )
            )

        # summary
        q_summary = session.query(
                Application.name,
                Application.apptype,
                Application.summary,
                Application.description,
                literal_column("'Summary'", Text).label('foundin'),
                literal_column('90', Integer).label('score'),
                Application.summary.label('data'))\
            .filter(
                and_(
                    Application.apptype == 'desktop', 
                    Application.desktoptype == 'Application',
                    *(Application.summary.ilike('%%%s%%' % p) for p in s_pattern)
                )
            )

        # descr
        q_descr = session.query(
                Application.name,
                Application.apptype,
                Application.summary,
                Application.description,
                literal_column("'Description'", Text).label('foundin'),
                literal_column('70', Integer).label('score'),
                Application.description.label('data'))\
            .filter(
                and_(
                    Application.apptype == 'desktop', 
                    Application.desktoptype == 'Application',
                    *(Application.description.ilike('%%%s%%' % p) for p in s_pattern)
                )
            )

        # usage
        q_usage = session.query(
                Application.name,
                Application.apptype,
                Application.summary,
                Application.description,
                literal_column("'Usage'", Text).label('foundin'),
                literal_column('20', Integer).label('score'),
                Usage.name.label('data'))\
            .join(
                Application.usages, 
                ApplicationUsage.usage)\
            .filter(
                and_(
                    Application.apptype == 'desktop', 
                    Application.desktoptype == 'Application',
                    *(Usage.name.ilike('%%%s%%' % p) for p in s_pattern)
                )
            )

        # tags
        q_tags = session.query(
                Application.name,
                Application.apptype,
                Application.summary,
                Application.description,
                literal_column("'Tags'", Text).label('foundin'),
                literal_column('10', Integer).label('score'),
                Tag.name.label('data'))\
            .join(
                Application.tags, 
                ApplicationTag.tag)\
            .filter(
                and_(
                    Application.apptype == 'desktop', 
                    Application.desktoptype == 'Application',
                    *(Tag.name.ilike('%%%s%%' % p) for p in s_pattern)
                )
            )


        # comments
        q_comments = session.query(
                Application.name,
                Application.apptype,
                Application.summary,
                Application.description,
                literal_column("'Comments'", Text).label('foundin'),
                literal_column('1', Integer).label('score'),
                Comment.body.label('data'))\
            .join(
                Application.comments)\
            .filter(
                and_(
                    Application.apptype == 'desktop', 
                    Application.desktoptype == 'Application',
                    Comment.published == True,
                    *(Comment.body.ilike('%%%s%%' % p) for p in s_pattern)
                )
            )

        # mimetypes
        q_mimetypes = session.query(
                Application.name,
                Application.apptype,
                Application.summary,
                Application.description,
                literal_column("'MimeTypes'", Text).label('foundin'),
                literal_column('10', Integer).label('score'),
                MimeType.name.label('data'))\
            .join(
                Application.mimetypes)\
            .filter(
                and_(
                    Application.apptype == 'desktop', 
                    Application.desktoptype == 'Application',
                    *(MimeType.name.ilike('%%%s%%' % p) for p in s_pattern)
                )
            )


        # union that
        apps_query = union(
                    q_name,
                    q_summary,
                    q_descr,
                    q_usage,
                    q_tags,
                    q_comments,
                    q_mimetypes)

        return apps_query


    @expose(template='pkgdb.templates.apps')
    def name(self, action='list', searchwords='a*' ):
        '''Applications view by name

        :arg action: type of listing
        :arg searchwords: filter used letter_paginator
        '''
        
        fresh = Application.fresh_apps(5)

        comments = Application.last_commented(5)
        
        pattern = searchwords.replace('*','%')
        #pylint:disable-msg=E1101
        app_list = session.query(
                    Application.name, 
                    Application.summary, 
                    Application.description)\
                .filter(and_(
                    Application.apptype == 'desktop',
                    Application.desktoptype == 'Application',
                    Application.name.ilike(pattern)))\
                .order_by(Application.name.asc())\
                .all()
        #pylint:enable-msg=E1101

        return dict(fresh=fresh, comments=comments,
            title=self.app_title, version=release.VERSION,
            searchwords=searchwords, list_type='name',
            app_list=app_list, pattern='')


    @expose(template='pkgdb.templates.apps')
    @paginate('app_list', limit=20, max_pages=13)
    def popular(self, action='list'):
        '''Applications view by popularity 
        '''
        
        fresh = Application.fresh_apps(5)

        comments = Application.last_commented(5)
        
        app_list = Application.most_popular(limit=0)
        

        return dict(fresh=fresh, comments=comments,
            title=self.app_title, version=release.VERSION,
            list_type='popular',
            app_list=app_list, pattern='')


    @expose(template='pkgdb.templates.apps')
    @paginate('app_list', limit=20, max_pages=13)
    def comments(self, action='list'):
        '''Applications view by comments (chronologicaly)
        '''
        
        fresh = Application.fresh_apps(5)

        comments = None
        
        app_list = Application.last_commented(limit=0)
        

        return dict(fresh=fresh, comments=comments,
            title=self.app_title, version=release.VERSION,
            list_type='comments',
            app_list=app_list, pattern='')


    @expose(template='pkgdb.templates.apps')
    @paginate('app_list', limit=20, max_pages=13)
    def latest(self, action='list'):
        '''Applications view by packagebuild import time
        '''
        
        fresh = None

        comments = Application.last_commented(5)
        
        app_list = Application.fresh_apps(limit=0)
        

        return dict(fresh=fresh, comments=comments,
            title=self.app_title, version=release.VERSION,
            list_type='latest',
            app_list=app_list, pattern='')


    @expose(template='pkgdb.templates.apps')
    def tag(self, action='list', tag=None):
        '''Applications view by tag
        '''
        
        fresh = None

        comments = Application.last_commented(5)
       
        tags = session.query(Tag).order_by(Tag.name.asc()).all()

        app_list = ()
        

        return dict(fresh=fresh, comments=comments,
            title=self.app_title, version=release.VERSION,
            list_type='tag', markers=tags, tag=tag,
            app_list=app_list, pattern='')


    @expose(template='pkgdb.templates._apps_ajax_result')
    def _by_tag(self, tag):

        #pylint:disable-msg=E1101
        app_list = session.query(
                    Application.name, 
                    Application.summary, 
                    Application.description)\
                .join(ApplicationTag, Tag)\
                .filter(and_(
                    Application.apptype == 'desktop', 
                    Application.desktoptype == 'Application',
                    Tag.name == tag))\
                .order_by(Application.name.asc())\
                .all()
        
        return dict(app_list=app_list, list_type='tag')


    @expose(template='pkgdb.templates.apps')
    def usage(self, action='list', usage=None):
        '''Applications view by usage
        '''
        
        fresh = None

        comments = Application.last_commented(5)
       
        usages = session.query(Usage).order_by(Usage.name.asc()).all()

        app_list = ()
        

        return dict(fresh=fresh, comments=comments,
            title=self.app_title, version=release.VERSION,
            list_type='usage', markers=usages, usage=usage,
            app_list=app_list, pattern='')


    @expose(template='pkgdb.templates._apps_ajax_result')
    def _by_usage(self, usage):

        #pylint:disable-msg=E1101
        app_list = session.query(
                    Application.name, 
                    Application.summary, 
                    Application.description,
                    func.avg(ApplicationUsage.rating).label('avg'),
                    func.count().label('count'))\
                .join(ApplicationUsage, Usage)\
                .filter(and_(
                    Application.apptype == 'desktop', 
                    Application.desktoptype == 'Application',
                    Usage.name == usage))\
                .group_by(
                    Application.name, 
                    Application.summary, 
                    Application.description)\
                .order_by(Application.name.asc())\
                .all()
        
        return dict(app_list=app_list, list_type='usage')


class ApplicationController(controllers.Controller):
    '''Display general information related to Applicaiton.
    '''

    def __init__(self, app_title=None):
        '''Create a Applications Controller

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title

    @expose(template='pkgdb.templates.application', allow_json=True)
    def default(self, app_name=None, repo='F-11-i386'):
        '''Retrieve application by its name.

        :arg app_name: Name of the packagebuild/rpm to lookup
        :arg repo: shortname of the repository to look in
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
        
        tagscore = application.scores

        #pylint:disable-msg=E1101
        comment_query = session.query(Comment).filter(
            Comment.application==application).order_by(Comment.time)
        #pylint:enable-msg=E1101
        # hide the mean comments from ordinary users
        if identity.in_group(mod_grp):
            comments = comment_query.all()
        else:
            comments = comment_query.filter_by(published=True).all()

        return dict(title=_('%(title)s -- %(app)s') % {
            'title': self.app_title, 'app': application.name},
                    tagscore=tagscore,
                    app=application,
                    comments=comments)


class AppIconController(controllers.Controller):
    '''Application icon API.
    '''

    def __init__(self, app_title=None):
        '''Create a App icon Controller

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title

    @expose(content_type='image/png')
    def show(self, app_name):
        # TODO: themes 
        icon_data = session.query(Icon.icon)\
                .join(Icon.name, IconName.applications)\
                .filter(Application.name==app_name)\
                .first()
        if not icon_data:
            redirect('/static/images/noicon.png')

        return str(icon_data[0])

                    



