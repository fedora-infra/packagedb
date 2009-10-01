# -*- coding: utf-8 -*-
#
# Copyright © 2009 Red Hat, Inc. All rights reserved.
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
Mapping of comments related database tables to python classes.
'''

from sqlalchemy import Table
from sqlalchemy.orm import relation, backref
from sqlalchemy.orm.collections import attribute_mapped_collection

from fedora.tg.json import SABase

from turbogears.database import mapper, metadata

#
# Tables
#

CommentsTable = Table('comments', metadata, autoload=True)

#
# Mapped Classes
# 

class Comment(SABase):
    '''Comments associated to PackageBuilds.

    Users signed into FAS can comment on specific packagebuilds, each comment
    belongs to a specific language.
    '''
    def __init__(self, author, body, language, published, application):
        super(Comment, self).__init__()
        self.author = author
        self.body = body
        self.language = language
        self.published = published
        self.application = application
    def __repr__(self):
        return 'Comment(author=%r, body=%r, published=%r, application=%r, '\
               'language=%r, time=%r)' % (
            self.author, self.body, self.published, self.application.name,
            self.language, self.time)

#
# Mappers
#

mapper(Comment, CommentsTable)
