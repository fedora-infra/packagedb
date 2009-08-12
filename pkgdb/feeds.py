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

'''
Feed Controller.

All feeds are provided in all the default TurboGears FeedController formats:
atom1.0, atom0.3, rss2.0.
'''

from turbogears import config, expose

from turbogears.feed import FeedController

from pkgdb.model import PackageBuild, Comment

class DesktopFeed(FeedController):
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
            
        for build in PackageBuild.query.filter_by(
                                        repoid=repoid, desktop=True
                                        ).order_by(PackageBuild.id.desc()
                                                   )[:items]:
            entry = {}
            entry["title"] = '%s-%s-%s' % (
                build.name, build.version, build.release)

            # 'John Doe <john@doe.com>' is being split for the TG atom template
            entry["author"] = {}
            (entry["author"]["name"],
             nothing,
             entry["author"]["email"]) = build.committer.partition(' <')
            entry["author"]["email"] = "<%s" % entry["author"]["email"]

            entry["summary"] = build.changelog

            
            entry["link"] = self.baseurl + '/packages/%s/%s' % (
                                           build.name,
                                           build.repo.shortname
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
            buildName = kwargs.get('build', None)
        except:
            buildName = None

        comment_query = Comment.query.filter_by(published=True
                                               ).order_by(Comment.time)
        if buildName:
            comment_query = comment_query.filter_by(packagebuildname=buildName)
        for comment in comment_query:
            entry = {}
            build = PackageBuild.query.filter_by(name=comment.packagebuildname
                                                 ).first()
            # maybe it should also say what language it's in. Later.
            entry["title"] = 'On %s by %s at %s' % (
                build.name,
                comment.author,
                comment.time.strftime('%H:%M - %h %d'))
            
            entry["author"] = {}
            entry["author"]["name"] = comment.author
            
            entry["summary"] = comment.body
            
            entry["link"] = self.baseurl + '/packages/%s/%s/%s#Comment%i' % (
                build.name, build.repo.shortname, comment.language, comment.id)
            entries.append(entry)
            
        return dict(
            title = "Fedora Package Database - latest comments",
            link = self.baseurl,
            author = {"name":"Fedora Websites",
                      "email":"webmaster@fedoraproject.org"},
            id = self.baseurl,
            entries = entries)
