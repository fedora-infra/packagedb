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


from turbogears import config, expose

from turbogears.feed import FeedController

from pkgdb.model import PackageBuild

class Feed(FeedController):
    def __init__(self):
         self.baseurl = config.get('base_url_filter.base_url')

    def get_feed_data(self):
        entries = []
        repoid = 1
        for build in PackageBuild.query.filter_by(
            repoid=repoid, desktop=True).order_by(PackageBuild.id.desc())[:10]:
            entry = {}
            entry["title"] = build.name
            entry["link"] = "/pkgdb/"
            entry["summary"] = build.changelog
            entries.append(entry)
        
        return dict(
            title = "Fedora Package Database - latest applications",
            link = self.baseurl,
            author = {"name":"Fedora Websites",
                      "email":"webmaster@fedoraproject.org"},
            id = self.baseurl,
            entries = entries)
