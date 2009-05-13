# -*- coding: utf-8 -*-
#
# Copyright © 2007-2008  Red Hat, Inc. All rights reserved.
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
# Red Hat Author(s):        Toshio Kuratomi <tkuratom@redhat.com>
# Fedora Project Author(s): Ionuț Arțăriși <mapleoin@fedoraproject.org>
#
'''
Controller for displaying Package Information.
'''

#
# Pylint Explanations
#

# :E1101: SQLAlchemy monkey patches the database fields into the mapper
#   classes so we have to disable these checks.

from sqlalchemy.orm import eagerload
from turbogears import controllers, expose, config, redirect, identity, \
        paginate

from pkgdb.model import Package, Collection, PackageAclStatus, PackageListing, \
        PackageListingTable
from pkgdb.dispatcher import PackageDispatcher
from pkgdb.bugs import Bugs
from pkgdb.letter_paginator import Letters
from pkgdb.utils import admin_grp, STATUS
from pkgdb import _

from fedora.tg.util import request_format

from cherrypy import request

class Packages(controllers.Controller):
    '''Display information related to individual packages.
    '''

    def __init__(self, app_title=None):
        '''Create a Packages Controller.

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title
        self.bugs = Bugs(app_title)
        self.index = Letters(app_title)
        self.dispatcher = PackageDispatcher()

    @expose(template='pkgdb.templates.pkgpage', allow_json=True)
    def name(self, packageName, collectionName=None, collectionVersion=None):
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
        '''
        # pylint: disable-msg=E1101
        # Return the information about a package.
        package = Package.query.filter(
                Package.c.statuscode!=STATUS['Removed'].statuscodeid
                ).filter_by(name=packageName).first()
        # pylint: enable-msg=E1101
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
            # pylint: disable-msg=E1101
            collection = Collection.query.filter_by(name=collectionName)
            # pylint: enable-msg=E1101
            if collectionVersion:
                collection = collection.filter_by(version=collectionVersion)
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
        # pylint: disable-msg=E1101
        # Possible statuses for acls:
        acl_status = PackageAclStatus.query.options(
                eagerload('locale')).all()
        # pylint: enable-msg=E1101
        acl_status_translations = ['']
        for status in acl_status:
            ### FIXME: At some point, we have to pull other translations out,
            # not just C
            if acl_status_translations != 'Obsolete':
                acl_status_translations.append(
                        status.locale['C'].statusname)

        # pylint: disable-msg=E1101
        # Fetch information about all the packageListings for this package
        pkg_listings = PackageListing.query.options(
                eagerload('people2.acls2.status.locale'),
                eagerload('groups2.acls2.status.locale'),
                eagerload('status.locale'),
                eagerload('collection.status.locale'),
                ).filter(PackageListingTable.c.packageid==package.id)
        # pylint: enable-msg=E1101
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

        pkg_listings = pkg_listings.all()

        # Check for shouldopen perms
        if identity.current.user == None:
            # Anonymous users cannot set shouldopen
            can_set_shouldopen = False
        else:
            # admins and owners of any branch can set shouldopen
            can_set_shouldopen = admin_grp in identity.current.groups or \
                    identity.current.user_name in [
                            x.owner for x in pkg_listings]
            if not can_set_shouldopen:
                # Set up a bunch of generators to iterate through the acls
                # on this package

                # Each iteration, retrieve a list of people with acls on this
                # package.
                people_lists = (listing.people for listing in pkg_listings)
                while True:
                    try:
                        # Each iteration, retrieve a set of people from the
                        # list
                        people = people_lists.next()
                        # Retrieve all the lists of acls for the current user
                        # for each PackageListing
                        acl_lists = (p.acls for p in people \
                                    if p.username == identity.current.user_name)
                        # For each list of acls...
                        for acls in acl_lists:
                            # ...check each acl
                            for acl in acls:
                                if acl.acl == 'approveacls' and acl.statuscode \
                                        == STATUS['Approved'].statuscodeid:
                                    # If the user has approveacls we're done
                                    can_set_shouldopen = True
                                    raise StopIteration
                    except StopIteration:
                        # When we get StopIteration because the peopleList is
                        # exhausted or we've found a match, exit the loop
                        break

        for pkg in pkg_listings:
            pkg.json_props = {'PackageListing': ('package', 'collection',
                    'people', 'groups', 'qacontact', 'owner'),
                'PersonPackageListing': ('aclOrder', 'user'),
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
            aclNames=acl_names, aclStatus=acl_status_translations,
            can_set_shouldopen=can_set_shouldopen)

    @expose(template='pkgdb.templates.pkgpage')
    # :C0103: id is an appropriate name for this method
    def id(self, package_id): # pylint: disable-msg=C0103
        '''Return the package with the given id

        :arg package_id: Numeric id of the package to return information for
        '''
        try:
            package_id = int(package_id)
        except ValueError:
            return dict(tg_template='pkgdb.templates.errors', status=False,
                    title=_('%(app)s -- Invalid Package Id') % {
                        'app': self.app_title},
                    message=_('The packageId you were linked to is not a valid'
                    ' id.  If you received this error from a link on the'
                    ' fedoraproject.org website, please report it.'))

        # pylint: disable-msg=E1101
        pkg = Package.query.filter_by(id=package_id).first()
        # pylint: enable-msg=E1101
        if not pkg:
            return dict(tg_template='pkgdb.templates.errors', status=False,
                    title=_('%(app)s -- Unknown Package') % {
                        'app': self.app_title},
                    message=_('The packageId you were linked to, %(pkg)s, does'
                    ' not exist. If you received this error from a link on the'
                    ' fedoraproject.org website, please report it.') % {
                        'pkg': package_id})

        raise redirect(config.get('base_url_filter.base_url') +
                '/packages/name/' + pkg.name)

    @expose(template='pkgdb.templates.userpkgs', allow_json=True)
    @paginate('pkgs', limit=75, default_order='name',
            max_limit=None, max_pages=13)
    def orphans(self, eol=None):
        '''List orphaned packages.

        :kwarg eol: If set, list packages that are in EOL distros.
        :returns: A list of packages.
        '''
        if not eol or eol.lower() in ('false','f','0'):
            eol = False
        else:
            eol = bool(eol)

        page_title = _('%(app)s -- Orphaned Packages') % {'app': self.app_title}

        query = Package.query.join('listings2').distinct().filter(
                    PackageListing.statuscode==STATUS['Orphaned'].statuscodeid)
        if not eol:
            # We don't want EOL releases, filter those out of each clause
            query = query.join(['listings2', 'collection']).filter(
                    Collection.c.statuscode!=STATUS['EOL'].statuscodeid)
        pkg_list = []
        for pkg in query:
            pkg.json_props = {'Package':('listings',)}
            pkg_list.append(pkg)
        return dict(title=page_title, pkgCount=len(pkg_list), pkgs=pkg_list,
                fasname='orphan', eol=eol)
