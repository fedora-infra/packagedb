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

'''
Feed Controller.

All feeds are provided in all the default TurboGears FeedController formats:
atom1.0, atom0.3, rss2.0.
'''
#
#pylint Explanations
#

# :E1101: SQLAlchemy monkey patches database fields into the mapper classes so
#   we have to disable this when accessing an attribute of a mapped class.


from turbogears import config
from sqlalchemy import Text
from sqlalchemy.orm import eagerload
from sqlalchemy.sql.expression import and_, literal_column
from operator import attrgetter

from turbogears.feed import FeedController
from turbogears.database import session

from fedora.tg.util import tg_url

try:
    from fedora.tg.util import tg_absolute_url
except:
    from pkgdb.lib.url import tg_absolute_url

from pkgdb.model import Comment, PackageBuildTable, PackageBuildReposTable
from pkgdb.model import Application, ApplicationUsage, Usage, ApplicationTag
from pkgdb.model import Tag, PackageBuild, Repo

import logging
log = logging.getLogger(__name__)


class ApplicationFeed(FeedController):
    '''Application feed factory.
    '''
    def __init__(self):
        baseurl = config.get('base_url_filter.base_url')
        while baseurl.endswith('/'):
            baseurl = baseurl[:-1]
        baseurl = '%s%s' % (baseurl, tg_url('/'))
        if baseurl.endswith('/'):
            baseurl = baseurl[:-1]
        self.baseurl = baseurl

    def get_feed_data(self, content, apps, **kwargs):

        content = content.split(' ')
        apps = apps.split(',')

        entries = []
        
        # how many items to output
        try:
            items = int(kwargs.get('items', 20))
        except:
            items = 20
       
        data = []

        # comments
        if u'comments' in content or u'all' in content:
            comments = session.query(
                    Comment.id,
                    Comment.time,
                    literal_column("'comment'", Text).label('type'),
                    Application.name.label('app'),
                    Comment.author,
                    Comment.body)\
                .join(Comment.application)\
                .filter(and_(
                    Comment.published==True,
                    Application.name.in_(apps)))\
                .order_by(Comment.time.desc())\
                .limit(items)
            data.extend(comments)

        # usages
        if u'usages' in content or u'all' in content:
            usages = session.query(
                    ApplicationUsage.rating,
                    ApplicationUsage.time,
                    ApplicationUsage.author,
                    literal_column("'usage'", Text).label('type'),
                    Application.name.label('app'),
                    Usage.name.label('usage'))\
                .join(
                    ApplicationUsage.application,
                    ApplicationUsage.usage)\
                .filter(Application.name.in_(apps))\
                .order_by(ApplicationUsage.time.desc())\
                .limit(items)
            data.extend(usages)

        # tags
        if u'tags' in content or u'all' in content:
            tags = session.query(
                    ApplicationTag.time,
                    literal_column("'tag'", Text).label('type'),
                    Application.name.label('app'),
                    Tag.name.label('tag'))\
                .join(
                    ApplicationTag.application,
                    ApplicationTag.tag)\
                .filter(Application.name.in_(apps))\
                .order_by(ApplicationTag.time.desc())\
                .limit(items)
            data.extend(tags)

        # builds
        if u'builds' in content or u'all' in content:
            builds = session.query(
                    PackageBuild.imported.label('time'),
                    PackageBuild.name,
                    PackageBuild.version,
                    PackageBuild.release,
                    PackageBuild.architecture,
                    PackageBuild.epoch,
                    Repo.shortname,
                    Application.name.label('app'),
                    literal_column("'build'", Text).label('type'))\
                .join(
                    PackageBuild.applications,
                    PackageBuild.repos)\
                .filter(Application.name.in_(apps))\
                .order_by(PackageBuild.imported.desc())\
                .limit(items)
            data.extend(builds)
                    

        # sort entries
        data.sort(key=attrgetter('time'), reverse=True) 

        # format entries
        for item in data[:items]:
            entry = {}
            title = u'N/A'
            author = {'name': '', 'email': ''}
            summary = u'N/A'
            link = '/'

            if item.type == u'comment':
                title = u'%s: commented by %s' % (item.app, item.author)
                author['name'] = item.author
                summary = item.body
                link = u'/applications/%s/#Comment%i' % (item.app, item.id)
            elif item.type == u'usage':
                title = u'%s: usage \'%s\' rated %i by %s' % (item.app, item.usage, 
                    item.rating, item.author)
                author['name'] = item.author
                summary = title
                link = '/applications/%s/#user_ratings' % item.app
            elif item.type == u'tag':
                title = u'%s: tagged \'%s\'' % (item.app, item.tag) 
                summary = title
                link = '/applications/%s/' % item.app
            elif item.type == u'build':
                title = u'%s: %s-%s-%s.%s imported in Fedora PkgDB' % (item.app, item.name,
                    item.version, item.release, item.architecture) 
                summary = title
                link = '/builds/show/%s/%s/%s/%s/%s/%s' % (item.shortname, item.name, item.epoch,
                    item.version, item.release, item.architecture)

            entry['published'] = item.time
            entry['title'] = title
            entry['author'] = author
            entry['summary'] = summary
            entry['link'] = tg_absolute_url(link)

            entries.append(entry)

        
        return dict(
            title = "Fedora Package Database",
            link = self.baseurl,
            author = {"name":"Fedora Websites",
                      "email":"webmaster@fedoraproject.org"},
            id = self.baseurl,
            entries = entries)


class CommentsFeed(FeedController):
    '''Provides a feed of the latest comments.

    These are the ones that have not been `unpublished` by a moderator.

    '''
    def __init__(self):
        baseurl = config.get('base_url_filter.base_url')
        while baseurl.endswith('/'):
            baseurl = baseurl[:-1]
        baseurl = '%s%s' % (baseurl, tg_url('/'))
        if baseurl.endswith('/'):
            baseurl = baseurl[:-1]
        self.baseurl = baseurl


    def get_feed_data(self, **kwargs):
        entries = []

        # how many items to output
        try:
            items = int(kwargs.get('items', 20))
        except:
            items = 20

        # build specific
        try:
            app_name = kwargs.get('app', None)
        except:
            app_name = None

        #pylint:disable-msg=E1101
        comment_query = session.query(Comment) \
                    .join('application') \
                    .options(eagerload('application')) \
                    .filter(Comment.published==True) \
                    .order_by(Comment.time)
        #pylint:enable-msg=E1101

        if app_name:
            #pylint:disable-msg=E1101
            comment_query = comment_query.filter(Application.name==app_name)

        for comment in comment_query:
            entry = {}

            entry["title"] = 'On %s by %s at %s' % (
                comment.application.name,
                comment.author,
                comment.time.strftime('%H:%M - %h %d'))
            
            entry["author"] = {}
            entry["author"]["name"] = comment.author
            
            entry["summary"] = comment.body
            
            entry["link"] = '%s/applications/%s/#Comment%i' % (self.baseurl,
                comment.application.name, comment.id)
            entries.append(entry)
            
        return dict(
            title = "Fedora Package Database - latest comments",
            link = self.baseurl,
            author = {"name":"Fedora Websites",
                      "email":"webmaster@fedoraproject.org"},
            id = self.baseurl,
            entries = entries)
