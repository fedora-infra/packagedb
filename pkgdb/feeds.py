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
from sqlalchemy.orm import eagerload

from turbogears.feed import FeedController
from turbogears.database import session

from pkgdb.model import Comment, PackageBuildTable, Application

class ApplicationFeed(FeedController):
    '''A feed of all the latest PackageBuilds.

    These PackageBuilds are considered applications of general interest
    because they have a .desktop file
    '''
    def __init__(self):
         self.baseurl = config.get('base_url_filter.base_url')

    def get_feed_data(self, **kwargs):
        entries = []
        
        # look for repoid
        try:
            repoid = int(kwargs.get('repoid', 1))
        except:
            repoid = 1
            
        # how many items to output
        try:
            items = int(kwargs.get('items', 20))
        except:
            items = 20
        
        # TODO apps

        #pylint:disable-msg=E1101
        apps = Application.query.options(eagerload('builds')).join('builds')\
                .filter(PackageBuildTable.c.repoid==repoid)\
                .order_by(Application.id.desc())[:items]
        #pylint:enable-msg=E1101
        for app in apps:
            entry = {}
            entry["title"] = '%s-%s-%s' % (
                app.name, app.builds[0].version, apps.builds[0].release)

            # 'John Doe <john@doe.com>' is being split for the TG atom template
            entry["author"] = {}
            entry["author"]["name"], discard, entry["author"]["email"] =\
                    app.builds[0].committer.partition(' <')
            entry["author"]["email"] = "<%s" % entry["author"]["email"]

            entry["summary"] = app.builds[0].changelog

            
            entry["link"] = self.baseurl + '/packages/%s/%s' % (
                                           apps.build.name,
                                           apps.build.repo.shortname
                                           )
            entries.append(entry)
        
        return dict(
            title = "Fedora Package Database - latest applications",
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
        self.baseurl = config.get('base_url_filter.base_url')


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

            # maybe it should also say what language it's in. Later.
            entry["title"] = 'On %s by %s at %s' % (
                comment.application.name,
                comment.author,
                comment.time.strftime('%H:%M - %h %d'))
            
            entry["author"] = {}
            entry["author"]["name"] = comment.author
            
            entry["summary"] = comment.body
            
            entry["link"] = self.baseurl + '/applications/%s/%s/#Comment%i' % (
                comment.application.name, comment.language, comment.id)
            entries.append(entry)
            
        return dict(
            title = "Fedora Package Database - latest comments",
            link = self.baseurl,
            author = {"name":"Fedora Websites",
                      "email":"webmaster@fedoraproject.org"},
            id = self.baseurl,
            entries = entries)
