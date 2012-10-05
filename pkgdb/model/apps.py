# -*- coding: utf-8 -*-
#
# Copyright © 2007-2009  Red Hat, Inc.
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

MS_NEW = 0
MS_EXPORTED = 1
MS_SYNCED = 2

from sqlalchemy import Table, Column, ForeignKeyConstraint, func, desc
from sqlalchemy import Integer, String, Text, Boolean, DateTime, Binary
from sqlalchemy import PassiveDefault
from sqlalchemy.orm import relation, backref
from sqlalchemy.sql.expression import and_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.associationproxy import association_proxy
from turbogears.database import metadata, mapper, session

from fedora.tg.json import SABase
from turbogears import url, config
from fedora.tg.tg1utils import tg_url

from pkgdb.model import PackageBuild, BinaryPackage, Collection
from pkgdb.lib.dt_utils import fancy_delta

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
    Column('icon_status_id', nullable=False, default=MS_NEW),
    ForeignKeyConstraint(['apptype'],['apptypes.apptype'], onupdate="CASCADE",
        ondelete="CASCADE"),
    ForeignKeyConstraint(['iconid'],['icons.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
    ForeignKeyConstraint(['iconnameid'],['iconnames.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
    ForeignKeyConstraint(['icon_status_id'],['media_status.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
)

#BlacklistTable = Table('blacklist', metadata,
#    Column('id', Integer, primary_key=True, autoincrement=True,
#        nullable=False),    
#    Column('name', Text, nullable=False),
#    Column('bltype', String(32), nullable=False),
#    ForeignKeyConstraint(['bltype'],['blacklisttypes.name'], onupdate="CASCADE",
#        ondelete="CASCADE"),
#)
#
#BlacklistTypesTable = Table('blacklistttypes', metadata,
#    Column('nmae', String(32), primary_key=True, nullable=False),
#)

ApplicationsUsagesTable = Table('applicationsusages', metadata,
    Column('applicationid', Integer, primary_key=True, nullable=False),
    Column('usageid', Integer, primary_key=True, nullable=False),
    Column('rating', Integer, default=1, nullable=False),
    Column('author', Text, primary_key=True, nullable=False),
    Column('time', DateTime(timezone=True), PassiveDefault(func.now()),
        nullable=False),
    ForeignKeyConstraint(['applicationid'], ['applications.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['usageid'], ['usages.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
)

ApplicationsTagsTable = Table('applicationstags', metadata,
    Column('applicationid', Integer, primary_key=True, nullable=False),
    Column('tagid', Integer, primary_key=True, nullable=False),
    Column('score', Integer, default=1, nullable=False),
    Column('time', DateTime(timezone=True), PassiveDefault(func.now()),
        nullable=False),
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

UsagesTable = Table('usages', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True, nullable=False),
    Column('name', Text, nullable=False, unique=True),
)

MimeTypesTable = Table('mimetypes', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True, nullable=False),
    Column('name', Text, nullable=False, unique=True),
)

AppsMimeTypesTable = Table('appsmimetypes', metadata,
    Column('applicationid', Integer, primary_key=True, nullable=False),
    Column('mimetypeid', Integer, primary_key=True, nullable=False),
    ForeignKeyConstraint(['applicationid'], ['applications.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['mimetypeid'], ['mimetypes.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
)

TagsTable = Table('tags', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True, nullable=False),
    Column('name', Text, nullable=False, unique=True),
)

IconNamesTable = Table('iconnames', metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('name', Text, nullable=False, unique=True)
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
    Column('m_status_id', nullable=False, default=MS_NEW),
    Column('icon', Binary, nullable=False),
    Column('orig_size', Integer, nullable=False),
    ForeignKeyConstraint(['nameid'], ['iconnames.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
    ForeignKeyConstraint(['collectionid'], ['collection.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['themeid'], ['themes.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
    ForeignKeyConstraint(['m_status_id'], ['media_status.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
)


MediaStatusTable = Table('media_status', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', Text, nullable=False)
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
            desktoptype=None, iconname=None, icon=None, icon_status_id=None ):
        super(Application, self).__init__()
        self.name = name
        self.description = description
        self.url = url
        self.apptype = apptype
        self.desktoptype = desktoptype
        self.iconname = iconname
        self.summary = summary
        self.icon = icon
        self.icon_status_id = icon_status_id

    # scores is dict {<tag_object>:score}
    # scores[<tag-object>] = <score> create/update app2tag relation with given score
    scores = association_proxy('by_tag', 'score', 
            creator=_create_apptag)

    _rating = None

    def __repr__(self):
        return 'Application(%r, summary=%r, url=%r, apptype=%r )' % (
            self.name, self.summary, self.url, self.apptype)


    def rating(self):
        '''Get application usages rating


        Returns dict(usage_name: (rating, votes))
        '''

        if not self._rating:

            ratings = {}

            for a2u in self.usages:
               current = ratings.get(a2u.usage.name, (0, 0))
               votes = current[1] + 1
               rating = ((current[0] * current[1]) + a2u.rating)*1.0 / votes
               ratings[a2u.usage.name] = (rating, votes)

            self._rating = ratings

        return self._rating


    def user_rating(self, user):
        """Ratings set by given user

        :arg user: username

        Returns dict(usage: rating)
        """

        usages = {}
        for a2u in self.usages:
            if a2u.author == user:
                usages[a2u.usage.name] = a2u.rating

        return usages
    

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


    def assign_mimetype(self, mimetype_name):
        '''Assign mime-type to application.

        If mime-type with the given name does not exist in the DB,
        it will be created as well

        :arg mimetype_name: mime-type name.

        Returns MimeType object
        '''

        #pylint:disable-msg=E1101
        try:
            mimetype = session.query(MimeType).filter_by(name=mimetype_name).one()
        except NoResultFound:
            mimetype = MimeType(name=mimetype_name)
            session.add(mimetype)
        #pylint:enable-msg=E1101

        if mimetype not in self.mimetypes:
            self.mimetypes.append(mimetype)

        return mimetype


    def update_rating(self, usage_name, rating, author):

        #pylint:disable-msg=E1101
        try:
            usage = session.query(Usage).filter_by(name=usage_name).one()
        except:
            usage = Usage(name=usage_name)
            session.add(usage)
        #pylint:enable-msg=E1101

        found = False

        for app_usage in self.usages:
            if app_usage.usage == usage and app_usage.author == author:
                user_rating = app_usage
                found = True
                break
        
        if not found:
            user_rating = ApplicationUsage(author=author)
            user_rating.usage = usage
            self.usages.append(user_rating)
            session.add(user_rating)

        user_rating.rating = int(rating)


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


    def builds_by_collection(self):
        '''Get builds grouped by collection

        :returns: {<collection>: {<build>: [<repo>,]}}
        '''
        builds = {}

        for build in self.builds:
            for repo in build.repos:
                coll = builds.get(repo.collection, {})
                b = coll.get(build, [])
                b.append(repo)
                coll[build] = b
                builds[repo.collection] = coll

        return builds


    def build_names(self):
        '''Get names of all binary packages that include this application.
        
        Returns list of distinct names
        '''
        build_names = {}
        for build in self.builds:
            build_names[build.name] = 1

        return build_names.keys()


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


    @classmethod
    def most_popular(self, limit=5):
        """Query that returns most rated applications

        :arg limit: top <limit> apps

        Number of votes is relevant here not the rating value
        """
        #pylint:disable-msg=E1101
        popular = session.query(
                    Application.name, 
                    Application.summary, 
                    Application.description,
                    Application.icon_status_id.label('icon_status'),
                    func.sum(ApplicationUsage.rating).label('total'),
                    func.count(ApplicationUsage.rating).label('count'))\
                .join('usages')\
                .filter(and_(
                    Application.apptype == 'desktop',
                    Application.desktoptype == 'Application'))\
                .group_by(
                    Application.name, 
                    Application.summary, 
                    Application.description,
                    Application.icon_status_id)\
                .order_by(desc('count'))
        #pylint:enable-msg=E1101
        if limit > 0:
            popular = popular.limit(limit)
        return popular

    @classmethod
    def fresh_apps(self, limit=5):
        """Query that returns last pkgbuild imports

        :arg limit: top <limit> apps

        Excerpt from changelog is returned as well
        """
        #pylint:disable-msg=E1101
        fresh = session.query(
                    Application.name, 
                    Application.summary, 
                    Application.icon_status_id.label('icon_status'),
                    PackageBuild.changelog,
                    PackageBuild.committime,
                    PackageBuild.committer)\
                .distinct()\
                .join('builds')\
                .filter(and_(
                    Application.apptype == 'desktop', 
                    Application.desktoptype=='Application'))\
                .order_by(PackageBuild.committime.desc())
        #pylint:enable-msg=E1101
        if limit > 0:
            fresh = fresh.limit(limit)
        return fresh


    @classmethod
    def last_commented(self, limit=5):
        """Query that returns last commented apps

        :arg limit: top <limit> apps

        Last comment is returned as well
        """
        #pylint:disable-msg=E1101
        comments = session.query(
                    Application.name, 
                    Application.summary,
                    Application.icon_status_id.label('icon_status'),
                    Comment.body,
                    Comment.time,
                    Comment.author)\
                .join('comments')\
                .filter(and_(
                    Application.apptype == 'desktop',
                    Application.desktoptype == 'Application',
                    Comment.published == True))\
                .order_by(Comment.time.desc())
        #pylint:enable-msg=E1101
        if limit > 0:
            comments = comments.limit(limit)
        return comments
        

    @classmethod
    def most_discussed(self, limit=5):
        """Query that returns most commented apps

        :arg limit: top <limit> apps
        """
        #pylint:disable-msg=E1101
        comments = session.query(
                    Application.name, 
                    Application.summary, 
                    Application.icon_status_id.label('icon_status'),
                    func.count().label('count'))\
                .join(Comment)\
                .filter(and_(
                    Application.apptype == 'desktop', 
                    Application.desktoptype == 'Application'))\
                .group_by(
                    Application.name, 
                    Application.summary,
                    Application.icon_status_id)\
                .order_by(desc('count'))
        #pylint:enable-msg=E1101
        if limit > 0:
            comments = comments.limit(limit)
        return comments


    def icon_url(self):
        return icon_url(self.name, self.icon_status_id)
        

#class Blacklist(SABase):
#
#    def __init__(self, name, bltype=None, just_store=False):
#        super(Blacklist, self).__init__()
#        self.name = name
#        self.bltype = bltype
#    
#        if not just_store:
#            # clean such objects from db
#            pass
#
#
#    def __repr__(self):
#        return 'Blacklist(%r, bltype=%r)' % (
#            self.name, self.bltype)#pylint:disable-msg=E1101
    

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
        return 'ApplicationTag(applicationid=%r, tagid=%r, score=%r, time=%r)' % (
            self.applicationid, self.tagid, self.score, self.time)#pylint:disable-msg=E1101


class ApplicationUsage(SABase):
    '''Application usage association.

    The association holds rating (0-5) which indicates 
    how suitable the application is for the usage.

    '''

    def __init__(self, application=None, usage=None, rating=1, author=None):
        super(ApplicationUsage, self).__init__()
        self.application = application
        self.usage = usage
        self.rating = rating
        self.author = author

    def __repr__(self):
        return 'ApplicationUsage(applicationid=%r, usageid=%r, rating=%r, author=%r, time=%r)' % (
            self.applicationid, self.usageid, self.rating, self.author, self.time)#pylint:disable-msg=E1101


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

    def fancy_delta(self, precision=2, short=False):
        return fancy_delta(self.time, precision, short)


class Usage(SABase):
    '''Application usage tags.

    Table -- usages
    '''

    def __init__(self, name):
        super(Usage, self).__init__()
        self.name = name

    def __repr__(self):
        return 'Usage(%r)' % (self.name)
        

class Tag(SABase):
    '''Application and/or Binarypackage Tags.

    Table -- Tags
    '''

    def __init__(self, name):
        super(Tag, self).__init__()
        self.name = name

    def __repr__(self):
        return 'Tag(%r)' % (self.name)
        

class MimeType(SABase):
    '''Mimetype representation.

    Table -- MimeTypes
    '''

    def __init__(self, name):
        super(MimeType, self).__init__()
        self.name = name

    def __repr__(self):
        return 'MimeType(%r)' % (self.name)


class IconName(SABase):

    def __init__(self, name):
        super(IconName, self).__init__()
        self.name = name

    def __repr__(self):
        return 'IconName(%r)' % (self.name)
       

def icon_url(app_name, status=0):
    if app_name:
        if config.get('server.allow_static_icons', False) and status == MS_SYNCED:
            app_name = app_name.replace('/', '_')
            return tg_url('/static/appicon/%s/%s.png' % \
                (app_name, app_name))
        else:
            return url('/appicon/show/%s' % app_name)
    else:
        return tg_url('/static/appicon/noicon.png')
        

class Theme(SABase):

    def __init__(self, name):
        super(Theme, self).__init__()
        self.name = name

    def __repr__(self):
        return 'Theme(%r)' % (self.name)
        
class Icon(SABase):

    def __init__(self, icon=None, name=None, collection=None, 
            theme=None, orig_size=0, m_status_id=0):
        super(Icon, self).__init__()
        self.icon = icon
        self.name = name
        self.collection = collection
        self.theme = theme
        self.orig_size = orig_size
        self.m_status_id = m_status_id

    def __repr__(self):
        return 'Icon(%r, collection=%r, theme=%r, orig_size=%r)' % (
            self.name, self.collection.name, self.theme.name, self.orig_size)

#
# Mappers
#

mapper(Application, ApplicationsTable, properties={
    'builds': relation(PackageBuild, backref=backref('applications'),
        secondary=PackageBuildApplicationsTable, cascade='all'),
    'by_tag': relation(ApplicationTag,
        collection_class=attribute_mapped_collection('tag')),
    'tags': relation(ApplicationTag, cascade='all'),
    'mimetypes': relation(MimeType, backref=backref('applications'),
        secondary=AppsMimeTypesTable, cascade='all'),
    'comments': relation(Comment, backref=backref('application'),
        cascade='all, delete-orphan'),
    'iconname': relation(IconName, backref=backref('applications')),
    'icon': relation(Icon, backref=backref('applications')),
    'usages': relation(ApplicationUsage, cascade='all'),
    })

#mapper(Blacklist, BlacklistTable)

mapper(ApplicationUsage, ApplicationsUsagesTable, 
    properties={
        'usage': relation(Usage, cascade='all'),
        'application': relation(Application, cascade='all'),
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

mapper(MimeType, MimeTypesTable)

mapper(Tag, TagsTable)

mapper(Usage, UsagesTable)

mapper(IconName, IconNamesTable)

mapper(Theme, ThemesTable)

mapper(Icon, IconsTable, properties = {
    'name': relation(IconName, backref=backref('icons')),
    'collection': relation(Collection),
    'theme': relation(Theme),
    })
