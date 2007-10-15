# -*- coding: utf-8 -*-
#
# Copyright © 2007  Red Hat, Inc. All rights reserved.
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
#
'''
Manipulate information from the download repositories.
'''
import os
import yum
import logging

from turbogears import config
from turbogears.database import session

import sqlalchemy
from sqlalchemy.exceptions import InvalidRequestError
from sqlalchemy import MetaData, create_engine
from sqlalchemy import Table, Column, Integer, String
from sqlalchemy.orm import Mapper
from sqlalchemy.ext.assignmapper import assign_mapper

from pkgdb.json import SABase
from pkgdb import model

log = logging.getLogger("pkgdb.controllers")

class UnknownRepoMDFormat(Exception):
    '''An unknown repository format was encountered.'''
    pass

class DB_Info (SABase):
    '''Metainformation about the yum cache.'''
    def __repr__(self):
        return 'DBInfo(%s, "%s")' % (self.dbversion, self.checksum)

class Packages(SABase):
    '''Package data in the yum repo.'''
    def __str__(self):
        return '%s-%s:%s-%s' % (self.name, self.epoch, self.version,
                self.release)

    def __repr__(self):
        return 'Packages(pkgKey=%s, pkgId="%s", name="%s", arch="%s",' \
                ' version="%s", epoch="%s", release="%s", summary="%s",' \
                ' description="%s", url="%s", time_file="%s",' \
                ' time_build="%s", rpm_license="%s", rpm_vendor="%s",' \
                ' rpm_group="%s", rpm_buildhost="%s", rpm_sourcerpm="%s",' \
                ' rpm_header_start=%s, rpm_header_end=%s, rpm_packager="%s",' \
                ' size_package=%s, size_installed=%s, size_archive=%s,' \
                ' location_href="%s", location_base="%s", checksum_type="%s")' \
                % (self.pkgKey, self.pkgId, self.name, self.arch, self.version,
                        self.epoch, self.release, self.summary,
                        self.description, self.url, self.time_file,
                        self.time_build, self.rpm_license, self.rpm_vendor,
                        self.rpm_group, self.rpm_buildhost, self.rpm_sourcerpm,
                        self.rpm_header_start, self.rpm_header_end,
                        self.rpm_packager, self.size_package,
                        self.size_installed, self.size_archive,
                        self.location_href, self.location_base,
                        self.checksum_type)

class RepoUpdater(yum.YumBase):
    '''Update yum repository information on the local system.
    
    This class allows one to update the yum metadata on the local system
    from a set of repo definitions. By splitting this into its own class we
    are able to run it from a separate application, useful because it can
    gradually acquire more memory over time which would lead a long-running
    server to have issues.
    '''

    def __init__(self):
        super(RepoUpdater, self).__init__()
        self.doConfigSetup()
        for repo in self.repos.findRepos('*'):
            self.repos.delete(repo.id)

        repodir = os.path.join(config.get('pkgdb.basedir',
                '/usr/local/fedora-packagedb'), 'yum.repos.d')
        if os.access(repodir, os.R_OK | os.X_OK):
            # Substitute for the system repo definitions because we can't
            # guarantee that the system repo's work (esp. for devel)
            self.conf.reposdir = [repodir]

        self.getReposFromConfig()
        self.repos.setCacheDir(yum.misc.getCacheDir())
        self.doRepoSetup()

        # Download repository information to use
        self._get_repodata()

    def _get_repodata(self):
        for repo in self.repos.findRepos('*'):
            repo.sack.populate(repo)
            # If we want more than just primary metadata, then pass:
            # repo.getPackageSack().populate(repo, mdtype='XXX')
            # where XXX == one of: 'filelists', 'otherdata', 'all'

class RepoInfo(object):
    '''Interact with a set of yum repositories.

    Why not use the yum API to do this?  There are some memory leaks
    (More technically, it might be memory fragmentation) that can push a long
    running server into eventual memory starvation.

    Using our own access routines curbs this memory usage.
    '''
    ### FIXME: Test what happens when we are accessing a repo.sqlite file that
    # is changed or replaced.
    # Test what happens if we have a repo.sqlite file open and use RepoUpdater
    # to change it.
    
    def __init__(self):
        '''Setup the links to repositories and the table mappings.
        '''
        # Find all the repos we know about
        self.repodir = yum.misc.getCacheDir()
        dbFiles = yum.misc.getFileList(self.repodir, '.sqlite', [])

        # Add paths to repoDB files
        self.repoFiles = {}
        for dbFile in dbFiles:
            repoDir, dbFileName = os.path.split(dbFile)
            repoName = os.path.basename(repoDir)
            mdtype = dbFileName[:dbFileName.index('.')]
            engine = create_engine('sqlite:///' + dbFile)
            try:
                self.repoFiles[repoName][mdtype] = engine
            except KeyError:
                self.repoFiles[repoName] = {mdtype: engine}

        # Set up sqlalchemy mappers for the packageDB tables
        self.metadata = MetaData()
        self.DB_InfoTable = Table('db_info', self.metadata,
                Column('dbversion', Integer, nullable=False),
                Column('checksum', String,  primary_key=True)
                )
        self.PackagesTable = Table('packages', self.metadata,
                Column('pkgKey', Integer, primary_key=True),
                Column('pkgId', String),
                Column('name', String),
                Column('arch', String),
                Column('version', String),
                Column('epoch', String),
                Column('release', String),
                Column('summary', String),
                Column('description', String),
                Column('url', String),
                Column('time_file', String),
                Column('time_build', String),
                Column('rpm_license', String),
                Column('rpm_vendor', String),
                Column('rpm_group', String),
                Column('rpm_buildhost', String),
                Column('rpm_sourcerpm', String),
                Column('rpm_header_start', Integer),
                Column('rpm_header_end', Integer),
                Column('rpm_packager', String),
                Column('size_package', Integer),
                Column('size_installed', Integer),
                Column('size_archive', Integer),
                Column('location_href', String),
                Column('location_base', String),
                Column('checksum_type', String)
                )
        Mapper(DB_Info, self.DB_InfoTable)
        Mapper(Packages, self.PackagesTable)
        self.session = sqlalchemy.create_session()

    def _bind_to_repo(self, repo, mdtype):
        '''Set our model to talk to the db in this particular repo.'''
        self.metadata.bind = self.repoFiles[repo][mdtype]
        info = self.session.query(DB_Info).one()
        if info.dbversion != 10:
            raise UnknownRepoMDFormat, 'Expected Repo format 10, got %s' % (
                    info.dbversion)

    def sync_package_descriptions(self):
        '''Add a new package to the database.
        '''
        noDesc = []

        # Retrieve all the packages without a description
        pkgs = model.Package.select_by(model.Package.c.description==None)

        # development-source has a very high chance of containing the package
        # so search it first
        repoList = self.repoFiles.keys()
        repoList.remove('development-source')
        repoList.insert(0, 'development-source')

        # For each package query the source repos for a package description
        for pkg in pkgs:
            desc = None
            for repoName in repoList:
                self._bind_to_repo(repoName, 'primary')
                try:
                    packages = self.session.query(Packages
                            ).filter_by(name=pkg.name).one()
                except InvalidRequestError:
                    # No information here, search another
                    pass
                else:
                    # Found!  We can stop searching now
                    desc = packages.description
                    break

            if desc:
                pkg.description = desc
            else:
                noDesc.append(pkg.name)

            # Close our local session
            self.session.close()

        # Flush the new descriptions to the TG context session
        session.flush()
        session.close()

        log.warning('\t'.join(noDesc))
        log.warning('Packages without descriptions: %s' % len(noDesc))

### FIXME: DB Tables not yet listed here:
# CREATE TABLE provides (  name TEXT,  flags TEXT,  epoch TEXT,  version TEXT,
# release TEXT,  pkgKey INTEGER );
# CREATE TABLE requires (  name TEXT,  flags TEXT,  epoch TEXT,  version TEXT,
# release TEXT,  pkgKey INTEGER , pre BOOLEAN DEFAULT FALSE);
# CREATE TABLE conflicts (  name TEXT,  flags TEXT,  epoch TEXT,  version
# TEXT,  release TEXT,  pkgKey INTEGER );
# CREATE TABLE files (  name TEXT,  type TEXT,  pkgKey INTEGER);
# CREATE TABLE obsoletes (  name TEXT,  flags TEXT,  epoch TEXT,  version
# TEXT,  release TEXT,  pkgKey INTEGER );
#
