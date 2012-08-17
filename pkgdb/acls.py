# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2012  Red Hat, Inc.
# Copyright (C) 2012  Frank Chiulli
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
#                           Frank Chiulli <fchiulli@fedoraproject.org>
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
from sqlalchemy import and_, case, cast, or_, select
from sqlalchemy.sql import func
from sqlalchemy.types import Integer 

from turbogears import controllers, error_handler, expose, flash, paginate
from turbogears import redirect, validate, validators 

from pkgdb.model import Package, PackageTable, Collection, CollectionTable, \
        PackageAclStatus, PackageListing, PackageListingTable
from pkgdb.dispatcher import PackageDispatcher
from pkgdb.bugs import Bugs
from pkgdb.letter_paginator import Letters
from pkgdb.lib.sort import get_collection_info
from pkgdb.lib.utils import STATUS
from pkgdb import _

from fedora.tg.tg1utils import request_format

COLLECTION = 21

#
# collection.id = 8 => Fedora devel
#
COLLECTION_ID = 8


#
# Exceptions.
#
class InvalidCollection(Exception):
    '''The entity specified is not a valid collection shortname.
    '''
    pass


#
# Validators
#
class AclEol(validators.Schema):
    '''Validator for the eol argument'''
    # validator schemas don't have methods (R0903, W0232)
    #pylint:disable=R0903,W0232
    eol = validators.StringBool()

# fc class AclName(validators.Schema):
class AclName(AclEol):
    '''Validator for the acls.name method'''
    # validator schemas don't have methods (R0903, W0232)
    #pylint:disable=R0903,W0232
    packageName = validators.UnicodeString(not_empty=True, strip=True)
    collectionName = validators.UnicodeString(not_empty=False, strip=True)
    collectionVersion = validators.UnicodeString(not_empty=False, strip=True)

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

    @expose(template='pkgdb.templates.pkgs_adv_search')
    @validate(validators = {'searchwords':
              validators.UnicodeString(not_empty=False, strip=True)})
    @paginate('pkg_list', limit=50, default_order=('name'), max_limit=None,
              max_pages=13)
    #pylint:disable-msg=C0322
    def adv_search(self, searchwords, operator='AND',
                   collection_id=COLLECTION_ID, searchon='both'):
        '''Package advanced search result

        :arg searchwords: one or more words to search for.
        :arg operator: 'AND'/'OR' as applied to searchwords.
        :arg collection_id: collection to search
        :arg searchon: 'name', 'description' or 'both'

        Search is performed on name, description.
        Results are sorted according to name.
        Parts where pattern was recognized are shown in listing.
        '''

        pkg_list = []

        #
        # Do some validation.
        #
        if len(searchwords) == 0:
            flash('Specify one or more keywords...')

        if ((operator != 'AND') and (operator != 'OR')):
            flash('Invalid operator (%s).  "AND"/"OR" are acceptable' %
                  operator)

        if ((searchon != 'name') and (searchon != 'description') and
            (searchon != 'both')):
            flash('Invalid search on (%s).  Valid options: "name", ' +
                  '"description" or "both"' % searchon)

        #
        # case insensitive
        #
        swords = searchwords.lower()
        swords = swords.split()

        pkg_query = select((Package.name, Package.description),
                           and_(Package.id == PackageListing.packageid,
                                PackageListing.collectionid == collection_id,
                                Package.statuscode != STATUS['Removed']),
                           use_labels=True)

        if operator == 'OR':
            clauses = []
            for searchword in swords:
                pattern = '%' + searchword + '%'
                if searchon == 'description':
                    #pylint:disable=E1101
                    clauses.append(func.lower(Package.description).\
                                              like(pattern))
                    #pylint:enable=E1101

                elif searchon in ['name', 'both']:
                    clauses.append(func.lower(Package.name).\
                                              like(pattern))
                    if searchon == 'both':
                        #pylint:disable=E1101
                        clauses.append(func.lower(Package.description).\
                                                  like(pattern))
                        #pylint:enable=E1101

            pkg_query = pkg_query.where(and_(or_(*clauses)))

        else: # AND operator
            for searchword in swords:
                pattern = '%' + searchword + '%'
                clauses = []
                if searchon == 'description':
                    #pylint:disable=E1101
                    clauses.append(func.lower(Package.description).\
                                              like(pattern))
                    #pylint:enable=E1101

                elif searchon in ['name', 'both']:
                    clauses.append(func.lower(Package.name).like(pattern))
                    if searchon == 'both':
                        #pylint:disable=E1101
                        clauses.append(func.lower(Package.description).\
                                                  like(pattern))
                        #pylint:enable=E1101

                pkg_query = pkg_query.where(or_(*clauses))

        #
        # Build a dictionary.
        # pkg[<pkg_name>]
        #
        pkgs = {}
        for row in pkg_query.execute():
            pkg_name = row[PackageTable.c.name]
            pkg_desc = row[PackageTable.c.description]
            if not pkgs.has_key(pkg_name):
                pkgs[pkg_name] = []
                pkgs[pkg_name].append(pkg_desc)

        result = select((CollectionTable,),
                        and_(Collection.id == collection_id)).execute()
        active_collection = result.fetchone()

        #
        # @paginate does not like dictionaries.  But it does like a list of
        # dictionaries.
        #
        pkg_list = []
        pkg_names = pkgs.keys()
        pkg_names.sort()
        for name in pkg_names:
            pkg_info = {}
            pkg_info['name'] = name
            pkg_info['desc'] = pkgs[name][0]

            pkg_list.append(pkg_info)

        collection_list = []
        collection_list = get_collection_info()

        return dict(title=self.app_title,  searchwords=searchwords,
                    operator=operator, collections=collection_list,
                    collection_id=int(collection_id), searchon=searchon,
                    pkg_list=pkg_list, count=len(pkg_list))


    @validate(validators=AclName())
    @error_handler()
    @expose(template='pkgdb.templates.pkgpage', allow_json=True)
    def name(self, packageName, collectionName=None, collectionVersion=None,
             eol=False, tg_errors=None):
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

        if tg_errors:
            message = 'Validation errors'
            for arg, msg in tg_errors.items():
                message = message + ': ' + arg + ' - ' + msg
                if arg == 'eol':
                    eol = False
            flash(message)
            if request_format() == 'json':
                return dict(exc='ValidationError')

        #pylint:disable=E1101
        # Return the information about a package.
        package = Package.query.filter(
                Package.statuscode!=STATUS['Removed']
                ).filter_by(name=packageName).first()
        #pylint:enable=E1101
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
            #pylint:disable=E1101
            collection = Collection.query.filter_by(name=collectionName)
            #pylint:enable=E1101
            if collectionVersion:
                collection = collection.filter_by(version=collectionVersion)
            if (not eol):
                collection = collection.filter(Collection.statuscode!=\
                                 STATUS['EOL'])
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
        acl_status = PackageAclStatus.query.options( #pylint:disable=E1101
                eagerload('locale')).all()
        acl_status_translations = ['']
        for status in acl_status:
            ### FIXME: At some point, we have to pull other translations out,
            # not just C
            if acl_status_translations != 'Obsolete':
                acl_status_translations.append(
                        status.locale['C'].statusname)

        #pylint:disable=E1101
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
        #pylint:enable=E1101
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
            pkg_listings = pkg_listings.filter(Collection.statuscode!=\
                               STATUS['EOL'])

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
              max_pages=13)
    #pylint:disable=C0322
    def orphans(self, collctn=None, tg_errors=None):
        '''List orphaned packages.

        :kwarg collctn: A list of collections to which the search is limited.
        :returns: A list of packages.
        '''

        if tg_errors:
            message = 'Validation errors'
            for arg, msg in tg_errors.items():
                message = message + ': ' + arg + ' - ' + msg
            flash(message)
            if request_format() == 'json':
                return dict(exc='ValidationError')

        page_title = _('%(app)s -- Orphaned Packages') % \
                     {'app': self.app_title}

        collctn_list = None
        if collctn:
            if (isinstance(collctn, tuple)):
                collctn_list = list(collctn)

            else:
                if (isinstance(collctn, list)):
                    collctn_list = collctn
                else:
                    collctn_list = [collctn]

            if ('devel' in collctn_list):
                collctn_list[collctn_list.index('devel')] = 'master'

        #
        # Get a list of valid collections.
        #
        valid_collctns = {}
        valid_shortname_list = []
        collctn_query = select((Collection.name,
                                Collection.branchname),
                               and_(Collection.statuscode != STATUS['EOL']),
                               use_labels=True)
        for row in collctn_query.execute():
            collctn_name = row[CollectionTable.c.name]
            branch_name = row[CollectionTable.c.branchname]
            valid_shortname_list.append(branch_name)
            if (not valid_collctns.has_key(collctn_name)):
                valid_collctns[collctn_name] = {}

            if (not valid_collctns[collctn_name].has_key(branch_name)):
                if (collctn_list):
                    valid_collctns[collctn_name][branch_name] = \
                        branch_name in collctn_list
                else:
                    valid_collctns[collctn_name][branch_name] = True

        #
        # Validate user-specified collections.
        #
        if (collctn_list):
            invalid_collctn_list = []
            for collection in collctn_list:
                if not collection in valid_shortname_list:
                    invalid_collctn_list.append(collection)

            if (len(invalid_collctn_list) > 0): 
                message = "The following are not valid collection names:  "
                for collection in invalid_collctn_list:
                    message += "%s  " % collection

                pkgs = []
                flash(message)
                if request_format() == 'json':
                    #
                    # Do not remove the extra arguments after exc.
                    # They are required for paginate.
                    #
                    return dict(exc='InvalidCollection', pkgCount=0, pkgs=pkgs)
                else:
                    for collctn_name in valid_collctns.keys():
                        for branch_name in valid_collctns[collctn_name].keys():
                           valid_collctns[collctn_name][branch_name] = False
                           
                    return dict(title=page_title, pkgCount=0, pkgs=pkgs,
                                collections=valid_collctns, eol=False,
                                fasname='orphan')
                

        pkg_query = select((Package.name,
                            Package.description,
                            Package.summary,
                            Collection.name,
                            Collection.version,
                            Collection.branchname,
                            PackageListing.statuscode),
                           and_(PackageListing.packageid == Package.id,
                                PackageListing.collectionid == Collection.id,
                                PackageListing.statuscode == \
                                    STATUS['Orphaned'],
                                Collection.statuscode != STATUS['EOL']),
                           use_labels=True
                          )

        if collctn_list:
            pkg_query = pkg_query.where(Collection.branchname.in_(collctn_list))

        pkg_list = {}
        for row in pkg_query.execute():
            pkg_name = row[PackageTable.c.name]
            pkg_desc = row[PackageTable.c.description]
            pkg_summary = row[PackageTable.c.summary]
            cname = row[CollectionTable.c.name]
            cver = row[CollectionTable.c.version]
            cbname = row[CollectionTable.c.branchname]
            statuscode = row[PackageListingTable.c.statuscode]
            if not pkg_list.has_key(pkg_name):
                pkg_list[pkg_name] = []
                pkg_list[pkg_name].append(pkg_desc)
                pkg_list[pkg_name].append(pkg_summary)
                pkg_list[pkg_name].append({})

            if not pkg_list[pkg_name][2].has_key(cname):
                pkg_list[pkg_name][2][cname] = {}

            if not pkg_list[pkg_name][2][cname].has_key(cver):
                pkg_list[pkg_name][2][cname][cver] = {}

            if not pkg_list[pkg_name][2][cname][cver].has_key(cbname):
                pkg_list[pkg_name][2][cname][cver][cbname] = statuscode

        #
        # @paginate does not like dictionaries.  But it does like a list of
        # dictionaries.
        #
        pkgs = []
        pkg_names = pkg_list.keys()
        pkg_names.sort()
        for pkg_name in pkg_names:
            pkg_info = {}
            pkg_info['name'] = pkg_name
            pkg_info['desc'] = pkg_list[pkg_name][0]
            pkg_info['summary'] = pkg_list[pkg_name][1]
            pkg_info['collections'] = pkg_list[pkg_name][2]
            pkgs.append(pkg_info)

        return dict(title=page_title, pkgCount=len(pkgs), pkgs=pkgs,
                    collections=valid_collctns, eol=False, fasname='orphan')

    @validate(validators=AclEol())
    @expose(template='pkgdb.templates.userpkgs', allow_json=True)
    @paginate('pkgs', limit=75, default_order='name', max_limit=None,
              max_pages=13)
    #pylint:disable=C0322
    def retired(self, eol=False, tg_errors=None):
        '''List retired packages.

        :kwarg eol: If True, list packages that are in EOL distros.
        :returns: A list of packages.
        '''

        if tg_errors:
            message = 'Validation errors'
            for arg, msg in tg_errors.items():
                message = message + ': ' + arg + ' - ' + msg
                if arg == 'eol':
                    eol = False
            flash(message)
            if request_format() == 'json':
                return dict(exc='ValidationError')

        page_title = _('%(app)s -- Retired Packages') % {'app': self.app_title}

        pkg_query = select((Package.name,
                            Package.description,
                            Package.summary,
                            Collection.name,
                            Collection.version,
                            Collection.branchname,
                            PackageListing.statuscode),
                           and_(PackageListing.packageid == Package.id,
                                PackageListing.collectionid == Collection.id,
                                PackageListing.statuscode == STATUS['Retired']
                               ),
                           use_labels=True
                          )
        if not eol:
            # We don't want EOL releases, filter those out of each clause
            pkg_query = pkg_query.where(Collection.statuscode != STATUS['EOL'])

        pkg_list = {}
        for row in pkg_query.execute():
            pkg_name = row[PackageTable.c.name]
            pkg_desc = row[PackageTable.c.description]
            pkg_summary = row[PackageTable.c.summary]
            cname = row[CollectionTable.c.name]
            cver = row[CollectionTable.c.version]
            cbname = row[CollectionTable.c.branchname]
            statuscode = row[PackageListingTable.c.statuscode]
            if not pkg_list.has_key(pkg_name):
                pkg_list[pkg_name] = []
                pkg_list[pkg_name].append(pkg_desc)
                pkg_list[pkg_name].append(pkg_summary)
                pkg_list[pkg_name].append({})

            if not pkg_list[pkg_name][2].has_key(cname):
                pkg_list[pkg_name][2][cname] = {}

            if not pkg_list[pkg_name][2][cname].has_key(cver):
                pkg_list[pkg_name][2][cname][cver] = {}

            if not pkg_list[pkg_name][2][cname][cver].has_key(cbname):
                pkg_list[pkg_name][2][cname][cver][cbname] = statuscode

        #
        # @paginate does not like dictionaries.  But it does like a list of
        # dictionaries.
        #
        pkgs = []
        pkg_names = pkg_list.keys()
        pkg_names.sort()
        for pkg_name in pkg_names:
            pkg_info = {}
            pkg_info['name'] = pkg_name
            pkg_info['desc'] = pkg_list[pkg_name][0]
            pkg_info['summary'] = pkg_list[pkg_name][1]
            pkg_info['collections'] = pkg_list[pkg_name][2]
            pkgs.append(pkg_info)

        return dict(title=page_title, pkgCount=len(pkg_list.keys()), pkgs=pkgs,
                    fasname='retired', eol=eol)

    @expose()
    def update_orphans(self, collections=''):
        if not isinstance(collections, (list, tuple)):
            collections = [collections]

        if (len(collections) == 1) and (collections[0] == ''):
            message = "Please select at least one collection."
            flash(message)
            url = '/acls/orphans'
            redirect(url)

        param = '&collctn='.join(collections)
        url = '/acls/orphans?collctn=' + param
        redirect(url)

