# -*- coding: utf-8 -*-
#
# Copyright © 2007-2010  Red Hat, Inc.
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
# Red Hat Author(s):        Toshio Kuratomi <tkuratom@redhat.com>
# Fedora Project Author(s): Ionuț Arțăriși <mapleoin@fedoraproject.org>
#
'''
Controller for handling Package ownership information.
'''

#
# Pylint Explanations
#

# :E1101: SQLAlchemy monkey patches the database fields into the mapper
#   classes so we have to disable these checks.
# :C0322: Disable space around operator checking in multiline decorators

from sqlalchemy.orm import eagerload
from sqlalchemy import case, cast
from sqlalchemy.types import Integer 

from turbogears import controllers, error_handler, expose, paginate, validate
from turbogears import validators

from pkgdb.model import Package, Collection, PackageAclStatus, PackageListing, \
        PackageListingTable
from pkgdb.dispatcher import PackageDispatcher
from pkgdb.bugs import Bugs
from pkgdb.letter_paginator import Letters
from pkgdb.lib.utils import STATUS
from pkgdb import _

from fedora.tg.util import request_format

COLLECTION = 21

#
# Validators
#

class AclName(validators.Schema):
    '''Validator for the acls.name method'''
    # validator schemas don't have methods (R0903, W0232)
    #pylint:disable-msg=R0903,W0232
    packageName = validators.UnicodeString(not_empty=True, strip=True)
    collectionName = validators.UnicodeString(not_empty=False, strip=True)
    collectionVersion = validators.UnicodeString(not_empty=False, strip=True)
    eol = validators.StringBool()

class Acls(controllers.Controller):
    '''Display ownership information related to individual packages.
    '''

    def __init__(self, app_title=None):
        '''Create an Aclsn Controller.

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title
        self.bugs = Bugs(app_title)
        self.list = Letters(app_title)
        self.dispatcher = PackageDispatcher()

    @validate(validators=AclName())
    @error_handler()
    @expose(template='pkgdb.templates.pkgpage', allow_json=True)
    def name(self, packageName, collectionName=None, collectionVersion=None, eol=False):
        '''Retrieve Packages by their name.

        This method returns ownership and acl information about a package.
        When given optional arguments the information can be limited by what
        collections they are present in.

        :arg packageName: Name of the package to lookup
        :kwarg collectionName: If given, limit information to branches for
            this distribution.
        :kwarg collectionVersion: If given, limit information to this
            particular version of a distribution.  Has no effect if
            collectionName is not also specified.
        :kwarg eol: end-of-life flag.  If True, do not limit information.
            If False, limit information to non-eol collections.
        '''
        
        #pylint:disable-msg=E1101
        # Return the information about a package.
        package = Package.query.filter(
                Package.statuscode!=STATUS['Removed']
                ).filter_by(name=packageName).first()
        #pylint:enable-msg=E1101
        if not package:
            error = dict(status=False,
                    title=_('%(app)s -- Invalid Package Name') % {
                        'app': self.app_title},
                        message=_('The packagename you were linked to'
                        ' (%(pkg)s) does not appear in the Package Database.'
                        ' If you received this error from a link on the'
                        ' fedoraproject.org website, please report it.') % {
                            'pkg': packageName})
            if request_format() != 'json':
                error['tg_template'] = 'pkgdb.templates.errors'
            return error

        collection = None
        if collectionName:
            #pylint:disable-msg=E1101
            collection = Collection.query.filter_by(name=collectionName)
            #pylint:enable-msg=E1101
            if collectionVersion:
                collection = collection.filter_by(version=collectionVersion)
            if (not eol):
                collection = collection.filter(statuscode!=STATUS['EOL'])
            if not collection.count():
                error = dict(status=False,
                        title=_('%(app)s -- Not a Collection') % {
                            'app': self.app_title},
                        message=_('%(name)s %(ver)s is not a Collection.') % {
                            'name': collectionName,
                            'ver': collectionVersion or ''})
                if request_format() != 'json':
                    error['tg_template'] = 'pkgdb.templates.errors'
                return error

        # Possible ACLs
        acl_names = ('watchbugzilla', 'watchcommits', 'commit', 'approveacls')
        # Possible statuses for acls:
        acl_status = PackageAclStatus.query.options( #pylint:disable-msg=E1101
                eagerload('locale')).all()
        acl_status_translations = ['']
        for status in acl_status:
            ### FIXME: At some point, we have to pull other translations out,
            # not just C
            if acl_status_translations != 'Obsolete':
                acl_status_translations.append(
                        status.locale['C'].statusname)

        #pylint:disable-msg=E1101
        # Fetch information about all the packageListings for this package
        # The order is a bit complex.  We want:
        # 1) EOL collections last
        # 2) Within those groups, same named collections together
        # 3) Within collections, version devel first,
        # 4) All other collections sorted as numbers in descending order
        pkg_listings = PackageListing.query.options(
                eagerload('people2.acls2.status.locale'),
                eagerload('groups2.acls2.status.locale'),
                eagerload('status.locale'),
                eagerload('collection.status.locale'),)\
                        .filter(PackageListingTable.c.packageid==package.id)\
                        .join(Collection)\
                        .order_by(case(value=Collection.statuscode,
                                whens={STATUS['EOL']: 999999},
                                else_=0),
                            Collection.name,
                            case(value=Collection.version,
                                whens={'devel':999999},
                                else_=cast(Collection.version, Integer))\
                            .desc()
                        )
        #pylint:enable-msg=E1101
        if collection:
            # User asked to limit it to specific collections
            pkg_listings = pkg_listings.filter(
                    PackageListingTable.c.collectionid.in_(
                    [c.id for c in collection]))
            if not pkg_listings.count():
                error = dict(status=False,
                        title=_('%(app)s -- Not in Collection') % {
                            'app': self.app_title},
                        message=_('The package %(pkg)s is not in Collection'
                            ' %(collctn_name)s %(collctn_ver)s.') % {
                                'pkg': packageName,
                                'collctn_name': collectionName,
                                'collctn_ver': collectionVersion or ''})
                if request_format() != 'json':
                    error['tg_template'] = 'pkgdb.templates.errors'
                return error

        # Map of statuscode to statusnames used in this package
        status_map = {}

        if (not eol):
            pkg_listings = pkg_listings.filter(Collection.statuscode!=STATUS['EOL'])

        pkg_listings = pkg_listings.order_by().all()

        for pkg in pkg_listings:
            pkg.json_props = {'PackageListing': ('package', 'collection',
                    'people', 'groups', 'qacontact', 'owner'),
                'PersonPackageListing': ('aclOrder', ),
                'GroupPackageListing': ('aclOrder', ),
                }

            status_map[pkg.statuscode] = pkg.status.locale['C'].statusname
            status_map[pkg.collection.statuscode] = \
                    pkg.collection.status.locale['C'].statusname

            for person in pkg.people:
                # Setup acls to be accessible via aclName
                person.aclOrder = {}
                for acl in acl_names:
                    person.aclOrder[acl] = None
                for acl in person.acls:
                    statusname = acl.status.locale['C'].statusname
                    status_map[acl.statuscode] = statusname
                    if statusname != 'Obsolete':
                        person.aclOrder[acl.acl] = acl

            for group in pkg.groups:
                # Setup acls to be accessible via aclName
                group.aclOrder = {}
                for acl in acl_names:
                    group.aclOrder[acl] = None
                for acl in group.acls:
                    status_map[acl.statuscode] = \
                            acl.status.locale['C'].statusname
                    group.aclOrder[acl.acl] = acl

        status_map[pkg_listings[0].package.statuscode] = \
                pkg_listings[0].package.status.locale['C'].statusname

        return dict(title=_('%(title)s -- %(pkg)s') % {
            'title': self.app_title, 'pkg': package.name},
            packageListings=pkg_listings, statusMap = status_map,
            aclNames=acl_names, aclStatus=acl_status_translations)

    @expose(template='pkgdb.templates.userpkgs', allow_json=True)
    @paginate('pkgs', limit=75, default_order='name', max_limit=None,
            max_pages=13) #pylint:disable-msg=C0322
    def orphans(self, eol=None):
        '''List orphaned packages.

        :kwarg eol: If set, list packages that are in EOL distros.
        :returns: A list of packages.
        '''
        ### FIXME: Replace with a validator
        if not eol or eol.lower() in ('false', 'f', '0'):
            eol = False
        else:
            eol = bool(eol)

        page_title = _('%(app)s -- Orphaned Packages') % {'app': self.app_title}

        #pylint:disable-msg=E1101
        query = Package.query.join('listings2').distinct().filter(
                    PackageListing.statuscode==STATUS['Orphaned'])
        #pylint:enable-msg=E1101
        if not eol:
            # We don't want EOL releases, filter those out of each clause
            #pylint:disable-msg=E1101
            query = query.join(['listings2', 'collection']).filter(
                    Collection.statuscode!=STATUS['EOL'])
        pkg_list = []
        for pkg in query:
            pkg.json_props = {'Package':('listings',)}
            pkg_list.append(pkg)
        return dict(title=page_title, pkgCount=len(pkg_list), pkgs=pkg_list,
                fasname='orphan', eol=eol)
