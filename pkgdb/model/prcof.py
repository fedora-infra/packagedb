'''
Mapping of PRCO (provides, requires, conflicts, obsoletes) and files
'''

from sqlalchemy import Table

from turbogears.database import metadata, mapper, get_engine

from fedora.tg.json import SABase

#
# Mapped Tables
#

RpmProvidesTable = Table('rpmprovides', metadata, autoload=True)
RpmRequiresTable = Table('rpmrequires', metadata, autoload=True)
RpmConflictsTable = Table('rpmconflicts', metadata, autoload=True)
RpmObsoletesTable = Table('rpmobsoletes', metadata, autoload=True)
RpmFilesTable = Table('rpmfiles', metadata, autoload=True)

#
# Mapped Classes
#

class RpmProvides(SABase):
    '''Packages and files that are provided by a specific PackageBuild.

    Table -- RpmProvides
    '''
    def __init__(self, name, packagebuildid, flags=None, epoch=None,
                 version=None, release=None):
        super(RpmProvides, self).__init__()
        self.name = name
        self.packagebuildid = packagebuildid
        self.flags = flags
        self.epoch = epoch
        self.version = version
        self.release = release

    def __repr__(self):
        return 'RpmProvides(%r, %r, flags=%r, epoch=%r, version=%r,' \
               'release=%r)' % (self.name, self.flags, self.packagebuildid,
                                self.epoch, self.version, self.release)

class RpmRequires(SABase):
    '''Packages and files that are required by a specific PackageBuild.

    Table -- RpmRequires
    '''
    def __init__(self, name, packagebuildid, flags=None, epoch=None,
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

class RpmObsoletes(SABase):
    '''Packages that are obsoleted by a specific PackageBuild.

    Table -- RpmObsoletes
    '''
    def __init__(self, name, packagebuildid, flags=None, epoch=None,
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

class RpmConflicts(SABase):
    '''Packages that are in conflict with a specific PackageBuild.

    Table -- RpmConflicts
    '''
    def __init__(self, name, packagebuildid, flags=None, epoch=None,
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

class RpmFiles(SABase):
    '''Files belonging to a specific PackageBuild.

    Table -- RpmFiles
    '''
    def __init__(self, name, packagebuildid):
        super(RpmFiles, self).__init__()
        self.name = name
        self.packagebuildid

    def __repr__(self):
        return 'RpmFiles(%r, %r)' % (self.name, self.packagebuildid)
    
#
# Mappers
#

mapper(RpmObsoletes, RpmObsoletesTable)
mapper(RpmConflicts, RpmConflictsTable)
mapper(RpmRequires, RpmRequiresTable)
mapper(RpmProvides, RpmProvidesTable)
mapper(RpmFiles, RpmFilesTable)