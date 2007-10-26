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
Controller for displaying Package Information.
'''

import sqlalchemy
from sqlalchemy.ext.selectresults import SelectResults
import sqlalchemy.mods.selectresults

from turbogears import controllers, expose, paginate, config, redirect
from turbogears.database import session

import bugzilla

from pkgdb import model
from dispatcher import PackageDispatcher

from cherrypy import request
import json

BZURL ='https://bugzilla.redhat.com/xmlrpc.cgi'
BZURL = 'https://bzprx.vip.phx.redhat.com/xmlrpc.cgi'

class BzBug(object):
    def __init__(self, bug):
        self.bug_id = bug.bug_id
        self.url = bug.url
        self.bug_status = unicode(bug.bug_status, 'utf-8')
        try:
            self.short_short_desc = unicode(bug.short_short_desc, 'utf-8')
        except TypeError:
            self.short_short_desc = unicode(bug.short_short_desc.data, 'utf-8')

class Packages(controllers.Controller):
    '''Display information related to individual packages.
    '''

    def __init__(self, fas=None, appTitle=None):
        '''Create a Packages Controller.

        :fas: Fedora Account System object.
        :appTitle: Title of the web app.
        '''
        self.fas = fas
        self.bzServer = bugzilla.Bugzilla(url=BZURL)
        self.appTitle = appTitle
        self.dispatcher = PackageDispatcher(self.fas)
        self.removedStatus = model.StatusTranslation.get_by(
                statusname='Removed', language='C').statuscodeid

    @expose(template='pkgdb.templates.pkgoverview')
    @paginate('packages', default_order='name', limit=100,
            allow_limit_override=True, max_pages=13)
    def index(self):
        # Retrieve the list of packages minus removed packages
        packages = SelectResults(session.query(model.Package)).select_by(
                model.Package.c.statuscode!=self.removedStatus)

        return dict(title=self.appTitle + ' -- Package Overview',
                packages=packages)

    @expose(template='pkgdb.templates.pkgbugs', allow_json=True)
    def bugs(self, packageName):
        query = {'product': 'Fedora',
                'component': packageName,
                'bug_status': ['ASSIGNED', 'NEW', 'NEEDINFO', 'MODIFIED'] }
        rawBugs = self.bzServer.query(query)
        bugs = []
        for bug in rawBugs:
            bugs.append(BzBug(bug))
        return dict(title='%s -- Open Bugs for %s' %
                (self.appTitle, packageName), package=packageName,
                bugs=bugs)

    @expose(template='pkgdb.templates.pkgpage', allow_json=True)
    def name(self, packageName, collectionName=None, collectionVersion=None):
        # Return the information about a package.
        package = model.Package.get_by(
                model.Package.c.statuscode!=self.removedStatus,
                name=packageName)
        if not package:
            error = dict(status=False,
                        title=self.appTitle + ' -- Invalid Package Name',
                        message= 'The packagename you were linked to (%s)' \
                        ' does not appear in the Package Database.' \
                        ' If you received this error from a link on the' \
                        ' fedoraproject.org website, please report it.' %
                        packageName)
            if not ('tg_format' in request.params and
                    request.params['tg_format'] == 'json'):
                error['tg_template'] = 'pkgdb.templates.errors'
            return error

        collection = None
        if collectionName:
            collection = SelectResults(session.query(model.Collection)
                    ).select_by(name=collectionName)
            if collectionVersion:
                collection = collection.select_by(version=collectionVersion)
            if not len(collection.list()):
                error = dict(status=False,
                        title=self.appTitle + ' -- Not a Collection',
                        message='%s %s is not a Collection.' %
                        (collectionName, collectionVersion or ''))
                if not ('tg_format' in request.params and
                        request.params['tg_format'] == 'json'):
                    error['tg_template'] = 'pkgdb.templates.errors'
                return error

        # Possible ACLs
        aclNames = ('watchbugzilla', 'watchcommits', 'commit', 'approveacls')
        # Possible statuses for acls:
        aclStatus = SelectResults(session.query(model.PackageAclStatus))
        aclStatusTranslations=['']
        for status in aclStatus:
            ### FIXME: At some point, we have to pull other translations out,
            # not just C
            if aclStatusTranslations != 'Obsolete':
                aclStatusTranslations.append(status.translations[0].statusname)

        # Fetch information about all the packageListings for this package
        pkgListings = SelectResults(session.query(model.PackageListing)).select(
                model.PackageListingTable.c.packageid==package.id
                )
        if collection:
            # User asked to limit it to specific collections
            pkgListings = pkgListings.select_by(
                    model.PackageListingTable.c.collectionid.in_(
                    *[c.id for c in collection]))
            if not pkgListings.count():
                error = dict(status=False,
                        title=self.appTitle + ' -- Not in Collection',
                        message='The package %s is not in Collection %s %s.' %
                        (packageName, collectionName, collectionVersion or '')
                        )
                if not ('tg_format' in request.params and
                        request.params['tg_format'] == 'json'):
                    error['tg_template'] = 'pkgdb.templates.errors'
                return error

        # Map of statuscode to statusnames used in this package
        statusMap = {}

        for pkg in pkgListings:
            statusMap[pkg.statuscode] = pkg.status.translations[0].statusname
            statusMap[pkg.collection.statuscode] = \
                    pkg.collection.status.translations[0].statusname
            # Get real ownership information from the fas
            (user, group) = self.fas.get_user_info(pkg.owner)
            ### FIXME: Handle the case where the owner is unknown
            pkg.ownername = '%s (%s)' % (user['human_name'], user['username'])
            pkg.ownerid = user['id']
            pkg.owneruser = user['username']
            if pkg.qacontact:
                (user, groups) = self.fas.get_user_info(pkg.qacontact)
                pkg.qacontactname = '%s (%s)' % (user['human_name'],
                        user['username'])
            else:
                pkg.qacontactname = ''

            for person in pkg.people:
                # Retrieve info from the FAS about the people watching the pkg
                (fasPerson, groups) = self.fas.get_user_info(person.userid)
                person.name = '%s (%s)' % (fasPerson['human_name'],
                        fasPerson['username'])
                person.user = fasPerson['username']
                # Setup acls to be accessible via aclName
                person.aclOrder = {}
                for acl in aclNames:
                    person.aclOrder[acl] = None
                for acl in person.acls:
                    statusname = acl.status.translations[0].statusname
                    statusMap[acl.statuscode] = statusname
                    if statusname != 'Obsolete':
                        person.aclOrder[acl.acl] = acl

            for group in pkg.groups:
                # Retrieve info from the FAS about a group
                fasGroup = self.fas.get_group_info(group.groupid)
                group.name = fasGroup['name']
                # Setup acls to be accessible via aclName
                group.aclOrder = {}
                for acl in aclNames:
                    group.aclOrder[acl] = None
                for acl in group.acls:
                    statusMap[acl.statuscode] = \
                            acl.status.translations[0].statusname
                    group.aclOrder[acl.acl] = acl

        statusMap[pkgListings[0].package.statuscode] = \
                pkgListings[0].package.status.translations[0].statusname
        pkgListings.jsonProps = {'PackageListing': ('package', 'collection',
                    'people', 'groups', 'qacontactname', 'owneruser'),
                'PersonPackageListing': ('aclOrder', 'name', 'user'),
                'GroupPackageListing': ('aclOrder', 'name'),
                }

        return dict(title='%s -- %s' % (self.appTitle, package.name),
                packageListings=pkgListings, statusMap = statusMap,
                aclNames=aclNames, aclStatus=aclStatusTranslations)

    @expose(template='pkgdb.templates.pkgpage')
    def id(self, packageId):
        try:
            packageId = int(packageId)
        except ValueError:
            return dict(tg_template='pkgdb.templates.errors', status=False,
                    title=self.appTitle + ' -- Invalid Package Id',
                    message='The packageId you were linked to is not a valid' \
                    ' id.  If you received this error from a link on the' \
                    ' fedoraproject.org website, please report it.'
                    )

        pkg = model.Package.get_by(id=packageId)
        if not pkg:
            return dict(tg_template='pkgdb.templates.errors', status=False,
                    title=self.appTitle + ' -- Unknown Package',
                    message='The packageId you were linked to, %s, does not' \
                    ' exist. If you received this error from a link on the' \
                    ' fedoraproject.org website, please report it.' % packageId
                    )

        raise redirect(config.get('base_url_filter.base_url') +
                '/packages/name/' + pkg.name)
