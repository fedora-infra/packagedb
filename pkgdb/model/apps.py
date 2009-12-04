# -*- coding: utf-8 -*-
#
# Copyright © 2007-2009  Red Hat, Inc.
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
# Red Hat Author(s): Toshio Kuratomi <tkuratom@redhat.com>
#                    Martin Bacovsky <mbacovsk@redhat.com>    
# Fedora Project Author(s): Ionuț Arțăriși <mapleoin@fedoraproject.org>
#
'''
Application related part of the model.

'''
#
# PyLint Explanation
#

# :E1101: SQLAlchemy monkey patches the db fields into the class mappers so we
#   have to disable this check wherever we use the mapper classes.
# :R0913: The __init__ methods of the mapped classes may need many arguments
#   to fill the database tables.

from sqlalchemy import Table, Column, ForeignKeyConstraint
from sqlalchemy import Integer, String, Text, Boolean, DateTime, Binary
from sqlalchemy.orm import relation, backref
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.associationproxy import association_proxy
from turbogears.database import metadata, mapper, session

from fedora.tg.json import SABase

from pkgdb.model import PackageBuild, BinaryPackage, Collection
from pkgdb.lib.dt_utils import FancyDateTimeDelta

from datetime import datetime

import logging
log = logging.getLogger('pkgdb.model.apps')
#
# Tables
#

ApplicationsTable = Table('applications', metadata, 
    Column('id', Integer, primary_key=True, autoincrement=True,
        nullable=False),    
    Column('name', Text, nullable=False),
    Column('description', Text, nullable=False),
    Column('summary', Text, nullable=False),
    Column('url', Text),
    Column('apptype', String(32), nullable=False),
    Column('desktoptype', Text),
    Column('iconid', nullable=True),
    Column('iconnameid', nullable=True),
    ForeignKeyConstraint(['apptype'],['apptypes.apptype'], onupdate="CASCADE",
        ondelete="CASCADE"),
    ForeignKeyConstraint(['iconid'],['icons.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
    ForeignKeyConstraint(['iconnameid'],['iconnames.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
)

ApplicationsTagsTable = Table('applicationstags', metadata,
    Column('applicationid', Integer, primary_key=True, nullable=False),
    Column('tagid', Integer, primary_key=True, nullable=False),
    Column('score', Integer, default=1, nullable=False),
    ForeignKeyConstraint(['applicationid'], ['applications.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['tagid'], ['tags.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
)

BinaryPackageTagsTable = Table('binarypackagetags', metadata,
    Column('binarypackagename', Text, primary_key=True, nullable=False),
    Column('tagid', Integer, primary_key=True, nullable=False),
    Column('score', Integer, default=1, nullable=False),
    ForeignKeyConstraint(['binarypackagename'],['binarypackages.name'], onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['tagid'],['tags.id'], onupdate="CASCADE", ondelete="CASCADE"),
)

PackageBuildApplicationsTable = Table('packagebuildapplications', metadata,
    Column('applicationid', Integer, primary_key=True, nullable=False),
    Column('packagebuildid', Integer, primary_key=True, nullable=False),
    ForeignKeyConstraint(['applicationid'], ['applications.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['packagebuildid'], ['packagebuild.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
)

AppTypesTable = Table('apptypes', metadata,
    Column('apptype', String(32), primary_key=True, nullable=False),
)

CommentsTable = Table('comments', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True, nullable=False),
    Column('author', Text, nullable=False),
    Column('body', Text, nullable=False),
    Column('published', Boolean, default=True, nullable=False),
    Column('time', DateTime(timezone=True), default=datetime.now,
        nullable=False),
    Column('applicationid', Integer, nullable=False),
    ForeignKeyConstraint(['applicationid'],['applications.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
)

TagsTable = Table('tags', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True, nullable=False),
    Column('name', Text, nullable=False, unique=True),
)

IconNamesTable = Table('iconnames', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('name', Text, nullable=False, unique=True),
)
                        
ThemesTable = Table('themes', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('name', Text, nullable=False, unique=True),
)
                        
IconsTable = Table('icons', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('nameid', nullable=False),
    Column('collectionid', nullable=False),                   
    Column('themeid', nullable=False),                   
    Column('icon', Binary, nullable=False),
    ForeignKeyConstraint(['nameid'], ['iconnames.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
    ForeignKeyConstraint(['collectionid'], ['collection.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['themeid'], ['themes.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
)


def _create_apptag(tag, score):
    """Creator function for apptags association proxy """
    apptag = ApplicationTag(tag=tag, score=score)
    session.add(apptag) #pylint:disable-msg=E1101
    return apptag


#
# Mapped Classes
# 

class Application(SABase):
    '''Application

    We take .desktop file as an application definition. Also packages without .desktop
    file will have application record (we will presume that the whole package is application)
    Apptype column indicates the type of the record.
    '''
    def __init__(self, name, description, url, apptype, summary,
            desktoptype=None, iconname=None, icon=None ):
        super(Application, self).__init__()
        self.name = name
        self.description = description
        self.url = url
        self.apptype = apptype
        self.desktoptype = desktoptype
        self.iconname = iconname
        self.summary = summary
        self.icon = icon

    # scores is dict {<tag_object>:score}
    # scores[<tag-object>] = <score> create/update app2tag relation with given score
    scores = association_proxy('by_tag', 'score', 
            creator=_create_apptag)

    def __repr__(self):
        return 'Application(%r, summary=%r, url=%r, apptype=%r )' % (
            self.name, self.summary, self.url, self.apptype)


    def tag(self, tag_name):
        '''Tag application.

        Add tag to application. If the tag already exists, 
        the score will be increased.

        :arg tag_name: tag name.

        Returns tag object
        '''

        #pylint:disable-msg=E1101
        try:
            tag = session.query(Tag).filter_by(name=tag_name).one()
        except:
            tag = Tag(name=tag_name)
            session.add(tag)
        #pylint:enable-msg=E1101

        score = self.scores.get(tag, 0)
       
        self.scores[tag] = score + 1
        return tag


    def comment(self, author, body):
        '''Add a new comment to a packagebuild.

        :arg author: the FAS author
        :arg body: text body of the comment
        '''

        comment = Comment(author, body, published=True, application=self)
        #pylint:disable-msg=E1101
        self.comments.append(comment)
        session.flush()
        #pylint:enable-msg=E1101


    @classmethod
    def search(cls, tags, operator):
        '''Retrieve all the apps which have a specified set of tags.

        Can also be used with just one tag.

        :arg tags: One or more tag names to lookup
        :arg operator: Can be one of 'OR' and 'AND', case insensitive, decides
        how the search for tags is done.

        Returns:
        :apps: list of found Application objects
        '''
        
        if isinstance(tags, (tuple, list)):
            tags = [tags]
        applications = set()

        # get the actual Tag objects
        object_tags = []
        for tag in tags:
            try:
                #pylint:disable-msg=E1101
                object_tags.append(Tag.query.\
                        filter_by(name=tag).one())
                #pylint:enable-msg=E1101
            except:
                raise Exception(tag)
        tags = object_tags

        if operator.lower() == 'or':
            for tag in tags:
                apps = tag.applications
                for app in apps:
                    applications.add(app)
        elif operator.lower() == 'and':
            applications = set(tags[0].applications)
            if len(tags) > 0:
                # do an intersection between all the taglists to get
                # the common ones
                for tag in tags[1:]:
                    applications = set(tags[0].applications)\
                            & set(tag.applications)

        return applications


class ApplicationTag(SABase):
    '''Application tag association.

    The association holds score which indicates how many users assigned 
    related tag to the application.

    '''

    def __init__(self, application=None, tag=None, score=1):
        super(ApplicationTag, self).__init__()
        self.application = application
        self.tag = tag
        self.score = score

    def __repr__(self):
        return 'ApplicationTag(applicationid=%r, tagid=%r, score=%r)' % (
            self.applicationid, self.tagid, self.score)#pylint:disable-msg=E1101


class BinaryPackageTag(SABase):
    '''BinaryPackage tag association.

    The association holds score which indicates how many users assigned 
    related tag to the BinaryPackage.

    '''

    def __init__(self, binarypackage=None, tag=None, score=1):
        super(BinaryPackageTag, self).__init__()
        self.binarypackage = binarypackage
        self.tag = tag
        self.score = score

    def __repr__(self):
        return 'BinaryPackageTag(binarypackage=%r, tagid=%r, score=%r)' % (
            self.binarypackagename, self.tagid, self.score) #pylint:disable-msg=E1101



class Comment(SABase):
    '''Comments associated to PackageBuilds.

    Users signed into FAS can comment on specific applications.
    '''
    def __init__(self, author, body, published, application):
        super(Comment, self).__init__()
        self.author = author
        self.body = body
        self.published = published
        self.application = application
    def __repr__(self):
        return 'Comment(author=%r, body=%r, published=%r, application=%r, '\
               'time=%r)' % (
                       self.author, self.body, self.published,
                       self.application.name,
                       self.time) #pylint:disable-msg=E1101

    def fancy_delta(self, precision=2):
        fancy_delta = FancyDateTimeDelta(self.time) #pylint:disable-msg=E1101
        return fancy_delta.format(precision)


class Tag(SABase):
    '''Application and/or Binarypackage Tags.

    Table -- Tags
    '''

    def __init__(self, name):
        super(Tag, self).__init__()
        self.name = name

    def __repr__(self):
        return 'Tag(%r)' % (self.name)
        
class IconName(SABase):

    def __init__(self, name):
        super(IconName, self).__init__()
        self.name = name

    def __repr__(self):
        return 'IconName(%r)' % (self.name)
        
class Theme(SABase):

    def __init__(self, name):
        super(Theme, self).__init__()
        self.name = name

    def __repr__(self):
        return 'Theme(%r)' % (self.name)
        
class Icon(SABase):

    def __init__(self, icon=None, name=None, collection=None, theme=None):
        super(Icon, self).__init__()
        self.icon = icon
        self.name = name
        self.collection = collection
        self.theme = theme

    def __repr__(self):
        return 'Icon(%r, collection=%r, theme=%r)' % (
            self.name, self.collection.name, self.theme.name)
        
#
# Mappers
#

mapper(Application, ApplicationsTable, properties={
    'builds': relation(PackageBuild, backref=backref('applications'),
        secondary=PackageBuildApplicationsTable, cascade='all'),
    'by_tag': relation(ApplicationTag,
        collection_class=attribute_mapped_collection('tag')),
    'comments': relation(Comment, backref=backref('application'),
        cascade='all, delete-orphan'),
    'iconname': relation(IconName, backref=backref('applications')),
    'icon': relation(Icon),
    })

mapper(ApplicationTag, ApplicationsTagsTable, 
    properties={
        'tag': relation(Tag, cascade='all'),
        'application': relation(Application, cascade='all'),
    })

mapper(BinaryPackageTag, BinaryPackageTagsTable, 
    properties={
        'tag': relation(Tag, cascade='all'),
        'binarypackage': relation(BinaryPackage, cascade='all'),
    })

mapper(Comment, CommentsTable)

mapper(Tag, TagsTable)

mapper(IconName, IconNamesTable)

mapper(Theme, ThemesTable)

mapper(Icon, IconsTable, properties = {
    'name': relation(IconName),
    'collection': relation(Collection),
    'theme': relation(Theme),
    })
