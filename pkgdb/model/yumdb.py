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
#
'''
Mapping of tables needed in the sqlite database that goes to yum
'''

from sqlalchemy import Table, Column, String, Integer, MetaData, ForeignKey

from pkgdb.model import TagsTable, LanguagesTable

yummeta = MetaData()

YumTagsTable = TagsTable.tometadata(yummeta)
YumPackageBuildNamesTable = Table('packagebuildnames', yummeta,
        Column('name', String(30), primary_key=True))
YumPackageBuildNamesTagsTable = Table('packagebuildnametags', yummeta,
        Column('packagebuildname', String,
            ForeignKey('packagebuildnames.name'), primary_key=True),
        Column('tagid', Integer, ForeignKey('tags.id'), primary_key=True),
        Column('score', Integer))
YumReposTable = Table('repos', yummeta,
                      Column('id', Integer, primary_key=True),
                      Column('name', String(50), nullable=False),
                      Column('shortname', String(20), nullable=False))

YumPackageBuildTable = Table('packagebuild', yummeta,
                              Column('id', Integer, primary_key=True),
                              Column('name', String(30), nullable=False),
                              Column('repoid', Integer, ForeignKey('repos.id'))
                              )
