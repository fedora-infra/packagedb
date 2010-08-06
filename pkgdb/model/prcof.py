'''
Mapping of PRCO (provides, requires, conflicts, obsoletes) and files
'''

from sqlalchemy import Table, Column, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy import Integer, Boolean, Text, ForeignKey, text

from turbogears.database import metadata, mapper

from fedora.tg.json import SABase
from pkgdb.lib.db import Grant_RW

FLAGS = {
    'EQ': '=',
    'GT': '>',
    'LT': '<',
    'GE': '>=',
    'LE': '<='}

#
# Mapped Tables
#

RpmProvidesTable = Table('rpmprovides', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
    Column('name', Text(),  nullable=False),
    Column('flags', Text()),
    Column('epoch', Text()),
    Column('version', Text()),
    Column('release', Text()),
    Column('packagebuildid', ForeignKey('packagebuild.id', ondelete='CASCADE'),
        nullable=False),
)
Grant_RW(RpmProvidesTable)


RpmRequiresTable = Table('rpmrequires', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
    Column('name', Text(),  nullable=False),
    Column('flags', Text()),
    Column('epoch', Text()),
    Column('version', Text()),
    Column('release', Text()),
    Column('packagebuildid', ForeignKey('packagebuild.id', ondelete='CASCADE'),
        nullable=False),
    Column('prereq', Boolean(), server_default=text('false'), nullable=False),
)
Grant_RW(RpmRequiresTable)


RpmConflictsTable = Table('rpmconflicts', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
    Column('name', Text(),  nullable=False),
    Column('flags', Text()),
    Column('epoch', Text()),
    Column('version', Text()),
    Column('release', Text()),
    Column('packagebuildid', ForeignKey('packagebuild.id', ondelete='CASCADE'),
        nullable=False),
)
Grant_RW(RpmConflictsTable)


RpmObsoletesTable = Table('rpmobsoletes', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
    Column('name', Text(),  nullable=False),
    Column('flags', Text()),
    Column('epoch', Text()),
    Column('version', Text()),
    Column('release', Text()),
    Column('packagebuildid', ForeignKey('packagebuild.id', ondelete='CASCADE'), 
        nullable=False),
)
Grant_RW(RpmObsoletesTable)


RpmFilesTable = Table('rpmfiles', metadata,
    Column('name', Text(),  primary_key=True, nullable=False),
    Column('packagebuildid', ForeignKey('packagebuild.id', ondelete='CASCADE'),
        primary_key=True, nullable=False),
)
Grant_RW(RpmFilesTable)

#
# Mapped Classes
#

class RpmProvides(SABase):
    '''Packages and files that are provided by a specific PackageBuild.

    Table -- RpmProvides
    '''
    def __init__(self, name, packagebuildid = None, flags=None, epoch=None,
                 version=None, release=None):
        super(RpmProvides, self).__init__()
        self.name = name
        self.packagebuildid = packagebuildid
        self.flags = flags
        self.epoch = epoch
        self.version = version
        self.release = release

    def __repr__(self):
        return 'RpmProvides(%r, packagebuildid=%r, flags=%r, epoch=%r, version=%r,' \
               'release=%r)' % (self.name, self.packagebuildid, self.flags,
                                self.epoch, self.version, self.release)

    def __str__(self):
        return "%s %s %s%s%s" % (self.name, FLAGS[self.flags],
                ('', self.epoch+':')[bool(self.epoch)], self.version,
                ('', '.'+self.release)[bool(self.release)])

class RpmRequires(SABase):
    '''Packages and files that are required by a specific PackageBuild.

    Table -- RpmRequires
    '''
    def __init__(self, name, packagebuildid=None, flags=None, epoch=None,
                 version=None, release=None, prereq=None):
        super(RpmRequires, self).__init__()
        self.name = name
        self.packagebuildid = packagebuildid
        self.flags = flags
        self.epoch = epoch
        self.version = version
        self.release = release
        self.prereq = prereq

    def __repr__(self):
        return 'RpmRequires(%r, %r, flags=%r, epoch=%r, version=%r,' \
               'release=%r, prereq=%r)' % (self.name, self.flags,
                        self.packagebuildid, self.epoch, self.version,
                        self.release, self.prereq)

    def __str__(self):
        return "%s %s %s%s%s" % (self.name, FLAGS[self.flags],
                ('', self.epoch+':')[bool(self.epoch)], self.version,
                ('', '.'+self.release)[bool(self.release)])


class RpmObsoletes(SABase):
    '''Packages that are obsoleted by a specific PackageBuild.

    Table -- RpmObsoletes
    '''
    def __init__(self, name, packagebuildid=None, flags=None, epoch=None,
                 version=None, release=None):
        super(RpmObsoletes, self).__init__()
        self.name = name
        self.packagebuildid = packagebuildid
        self.flags = flags
        self.epoch = epoch
        self.version = version
        self.release = release

    def __repr__(self):
        return 'RpmObsoletes(%r, %r, flags=%r, epoch=%r, version=%r,' \
                'release=%r)' % (self.name, self.packagebuildid, self.flags,
                                 self.epoch, self.version, self.release)

    def __str__(self):
        return "%s %s %s%s%s" % (self.name, FLAGS[self.flags],
                ('', self.epoch+':')[bool(self.epoch)], self.version,
                ('', '.'+self.release)[bool(self.release)])


class RpmConflicts(SABase):
    '''Packages that are in conflict with a specific PackageBuild.

    Table -- RpmConflicts
    '''
    def __init__(self, name, packagebuildid=None, flags=None, epoch=None,
                 version=None, release=None):
        super(RpmConflicts, self).__init__()
        self.name = name
        self.packagebuildid = packagebuildid
        self.flags = flags
        self.epoch = epoch
        self.version = version
        self.release = release

    def __repr__(self):
        return 'RpmConflicts(%r, %r, flags=%r, epoch=%r, version=%r,' \
               'release=%r)' % (self.name, self.packagebuildid, self.flags,
                                self.epoch, self.version, self.release)

    def __str__(self):
        return "%s %s %s%s%s" % (self.name, FLAGS[self.flags],
                ('', self.epoch+':')[bool(self.epoch)], self.version,
                ('', '.'+self.release)[bool(self.release)])



class RpmFiles(SABase):
    '''Files belonging to a specific PackageBuild.

    Table -- RpmFiles
    '''
    def __init__(self, name, packagebuildid=None):
        super(RpmFiles, self).__init__()
        self.name = name
        self.packagebuildid = packagebuildid

    def __repr__(self):
        return 'RpmFiles(%r, %r)' % (self.name, self.packagebuildid)
    
#
# Mappers
#

mapper(RpmProvides, RpmProvidesTable)
mapper(RpmObsoletes, RpmObsoletesTable)
mapper(RpmConflicts, RpmConflictsTable)
mapper(RpmRequires, RpmRequiresTable)
mapper(RpmFiles, RpmFilesTable)
