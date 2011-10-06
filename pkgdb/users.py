# -*- coding: utf-8 -*-
#
# Copyright (C) 2007  Nigel Jones
# Copyright (C) 2007, 2009-2011  Red Hat, Inc.
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
# Author(s): Nigel Jones <nigelj@fedoraproject.org>
#            Toshio Kuratomi <tkuratom@redhat.com>
#            Frank Chiulli <fchiulli@fedoraproject.org>
#
'''
Controller to show information about packages by user.
'''

#
# PyLint Explanation
#

# :E1101: SQLAlchemy monkey patches the db fields into the class mappers so we
#   have to disable this check wherever we use the mapper classes.
# :C0322: Disable space around operator checking in multiline decorators
import itertools

import urllib

import sqlalchemy
from sqlalchemy import and_, select, union
from sqlalchemy.exceptions import InvalidRequestError
from sqlalchemy.orm import lazyload

from turbogears import config, controllers, expose, flash, identity, paginate
from turbogears import redirect, validate, validators
from turbogears.database import session

from pkgdb.model import Collection, Package, PackageListing, \
        PersonPackageListing, PersonPackageListingAcl
from pkgdb.model import CollectionTable, PackageTable, PackageListingTable, \
        PersonPackageListingAclTable

from pkgdb.lib.utils import STATUS, LOG

from pkgdb import _

from fedora.tg.tg1utils import request_format, tg_url


#
# Validators.
#
class UsersEol(validators.Schema):
    '''Validator for the eol argument'''
    # validator schemas don't have methods (R0903
    #pyling:disable-msg=R0903,W0232
    eol = validators.StringBool()


class Users(controllers.Controller):
    '''Controller for all things user related.

    Status Ids to use with queries.
    '''
    allAcls = (('owner', 'owner'), ('approveacls', 'approveacls'),
            ('commit', 'commit'),
            ('watchcommits', 'watchcommits'),
            ('watchbugzilla', 'watchbugzilla'))

    def __init__(self, app_title):
        '''Create a User Controller.

        :arg app_title: Title of the web app.
        '''
        self.app_title = app_title

    def _send_log_msg(self, msg, subject, author, recipients):
        '''Send a log message to interested parties.

        This takes a message and sends it to the recipients.

        :arg msg: The log message to send
        :arg subject: A textual description or summary of the content of the
            message.
        :arg author: Email address or addresses of the author(s)
        :arg recipients: Email address or address which should receive the
            message (To header)

        All email addresses can be given either as a string or as a tuple
        ('Full Name', 'name@example.com').
        '''

        if config.get('mail.on', False):
            email = turbomail.Message(author, recipients,
                        '[pkgdb] %s' % (subject,))
            email.plain = msg
            turbomail.enqueue(email)
        else:
            LOG.debug(_('Would have sent: %(subject)s') % {
                        'subject': subject.encode('ascii', 'replace')})
            LOG.debug('To: %s' % recipients)
            LOG.debug('From: %s %s' %
                      (author[0].encode('ascii', 'replace'),
                       author[1].encode('ascii', 'replace')))
            LOG.debug('%s' % msg.encode('ascii', 'replace'))

    @expose(template='pkgdb.templates.useroverview')
    def index(self):
        '''Dish some dirt on the requesting user
        '''
        raise redirect('/users/info/')

    @validate(validators=UsersEol())
    @expose(template='pkgdb.templates.userpkgs', allow_json=True)
    @paginate('pkgs', limit=100, default_order='name', max_limit=None,
              max_pages=13)
    #pylint:disable=C0322
    def packages(self, fasname=None, acls=None, eol=False, tg_errors=None):
        '''List packages that the user is interested in.

        This method returns a list of packages owned by the user in current,
        non-EOL distributions.  The user has the ability to filter this to
        provide more or less information by adding query params for acls and
        EOL.

        :kwarg fasname: The name of the user to get the package list for.
                  Default: The logged in user.
        :kwarg acls: List of acls to select.
               Note: for backwards compatibility, this can also be a comma
               separated string of acls.
               Default: all acls.
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

        # For backward compat, redirect the orphan user to the orphan page
        if fasname == 'orphan':
            params = {}
            if eol:
                params['eol'] = True
            if request_format() == 'json':
                params['tg_format'] = 'json'
            url = '/acls/orphans'
            if params:
                url = url + '?' + urllib.urlencode(params, True)

            raise redirect(url)

        if not acls:
            # Default to all acls
            acls = [k[0] for k in self.allAcls]
        elif isinstance(acls, basestring):
            # For backwards compatibility, make acls into a list if it's a
            # comma separated string of values
            acls = acls.split(',')

        # Create a list with the following information:
        #   acl name,
        #   boolean indicating whether the acl is currently being filtered for,
        #   the label to use to display the acl.
        acl_list = [(a[0], a[0] in acls, a[1]) for a in self.allAcls]

        # Have to either get fasname from the URL or current user
        if fasname == None:
            if identity.current.anonymous:
                raise identity.IdentityFailure(
                        _('You must be logged in to view your information'))
            else:
                fasname = identity.current.user_name

        page_title = _('%(app)s -- %(name)s -- Packages') % {
                       'app': self.app_title, 'name': fasname}

        # pylint: disable=E1101
        query = select((Package.name,
                        Package.description,
                        Package.summary,
                        Collection.name,
                        Collection.version,
                        Collection.branchname,
                        PackageListing.statuscode),
                       and_(PackageListing.packageid == Package.id,
                            PackageListing.collectionid == Collection.id),
                       use_labels=True
                      )

        if not eol:
            # We don't want EOL releases, filter those out of each clause
            query = query.where(Collection.statuscode != STATUS['EOL'])

        queries = []
        if 'owner' in acls:
            # Return any package for which the user is the owner
            queries.append(query.where(
                                 and_(Package.statuscode.in_((
                                          STATUS['Approved'],
                                          STATUS['Awaiting Review'],
                                          STATUS['Under Review'])),
                                      PackageListing.owner==fasname,
                                      PackageListing.statuscode.in_((
                                          STATUS['Approved'],
                                          STATUS['Awaiting Branch'],
                                          STATUS['Awaiting Review']))
                          )))
            del acls[acls.index('owner')]

        if acls:
            # Return any package on which the user has an Approved acl.
            queries.append(query.where(
                                 and_(Package.statuscode.in_((
                                          STATUS['Approved'],
                                          STATUS['Awaiting Review'],
                                          STATUS['Under Review'])),
                                      PackageListing.id == \
                                          PersonPackageListing.packagelistingid,
                                      PersonPackageListing.username == fasname,
                                      PersonPackageListing.id == \
                                          PersonPackageListingAcl.personpackagelistingid,
                                      PersonPackageListingAcl.statuscode == \
                                          STATUS['Approved'],
                                      PackageListing.statuscode.in_((
                                          STATUS['Approved'],
                                          STATUS['Awaiting Branch'],
                                          STATUS['Awaiting Review']))
                          )).distinct())

            # Return only those acls which the user wants listed
            queries[-1] = queries[-1].where(
                                      PersonPackageListingAcl.acl.in_(acls))

        # pylint: enable=E1101
        pkg_list = {}
        for query in queries:
            for row in query.execute():
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
                    acls=acl_list, fasname=fasname, eol=eol)

    @expose(template='pkgdb.templates.useroverview')
    def info(self, fasname=None):
        '''Return some info and links for the user.

        Currently this page does nothing.  Eventually we want it to return an
        overview of what the user can do.  A TODO queue of people/packages
        they need to approve.  Links to FAS. Etc.

        :kwarg fasname: If given, the name of hte user to display information
            for.  Defaults to the logged in user.
        '''
        # If fasname is blank, ask for auth, we assume they want their own?
        if fasname == None:
            if identity.current.anonymous:
                raise identity.IdentityFailure(
                        _('You must be logged in to view your information'))
            else:
                fasname = identity.current.user_name

        page_title = _('%(app)s -- %(name)s -- Info') % {
                'app': self.app_title, 'name': fasname}
        return dict(title=page_title, fasname=fasname)

    @expose(template='pkgdb.templates.pendingpkgs', allow_json=True)
    def pending(self, owner=None):
        '''List packages that are awaiting approval.

        This method returns a list of packagelistings whose status is Awaiting
        Review.

        :kwarg owner: The owner of the packagelistings.
               Default is the current user.

        :returns: A dictionary of the owner, package information andi
                  can_approve.
        '''

        #
        # if user is logged in
        #     if owner specified
        #         can_appprove = (user == owner)
        #     else
        #        owner = user
        #        can_approve = True
        # else
        #     if owner specified
        #         can_approve = False
        #     else
        #         Error!
        #
        can_approve = False
        if not identity.current.anonymous:
            user = identity.current.user_name
            if owner != None:
                can_approve = (user == owner)
            else:
                owner = user
                can_approve = True
        else:
            if owner != None:
                can_approve = False
            else:
                message = "Either login or specify an owner"
                flash(message)
                if request_format() == 'json':
                    return dict(exc='IdentityFailure')
                else:
                    return dict(title="Error", pkgs={})

        page_title = _('%(app)s -- %(name)s -- Packages') % {
                       'app': self.app_title, 'name': owner}

        #
        # Build a query to get packagelistings owned by 'owner'.
        #
        pkgsOwned_query = select((PackageListing.id,),
                                 and_(PackageListing.owner == owner,
                                      PackageListing.statuscode ==
                                          STATUS['Approved'],
                                      PackageListing.packageid == Package.id,
                                      Package.statuscode == STATUS['Approved'],
                                      PackageListing.collectionid ==
                                          Collection.id,
                                      Collection.statuscode ==
                                          STATUS['Active']))

        #
        # Build a query to get packagelistings for which 'owner' has
        # approveacls.
        #
        pkgsAcls_query = select((PackageListing.id,),
                                and_(PersonPackageListingAcl.acl ==
                                         'approveacls',
                                     PersonPackageListingAcl.statuscode ==
                                         STATUS['Approved'],
                                     PersonPackageListingAcl.\
                                         personpackagelistingid ==
                                         PersonPackageListing.id,
                                     PersonPackageListing.username == owner,
                                     PersonPackageListing.packagelistingid ==
                                         PackageListing.id,
                                     PackageListing.packageid == Package.id,
                                     Package.statuscode == STATUS['Approved'],
                                     PackageListing.collectionid ==
                                         Collection.id,
                                     Collection.statuscode == STATUS['Active'],
                                     PackageListing.statuscode ==
                                         STATUS['Approved']))

        pkglistings = {}
        for record in itertools.chain(pkgsOwned_query.execute(),
                                      pkgsAcls_query.execute()):
            pkg_listing_id = record[0]
            pkglistings[pkg_listing_id] = 1

        pkg_listing_ids = pkglistings.keys()
        pkgsPending_query = select((Package.name,
                                    Collection.name,
                                    Collection.version,
                                    PersonPackageListing.username,
                                    PersonPackageListingAcl.acl,
                                    PersonPackageListingAcl.id),
                                   and_(PackageListing.id.in_(pkg_listing_ids),
                                        PackageListing.collectionid == 
                                            Collection.id,
                                        PackageListing.packageid ==
                                            Package.id,
                                        PackageListing.id == 
                                            PersonPackageListing.\
                                                packagelistingid,
                                        PersonPackageListing.id ==
                                            PersonPackageListingAcl.\
                                                personpackagelistingid,
                                        PersonPackageListingAcl.statuscode ==
                                            STATUS['Awaiting Review']))
        pkgs = {}
        for record in pkgsPending_query.execute():
            pkg_name = record[0]
            collection = record[1] + ' ' + record[2]
            acl_owner = record[3]
            acl = record[4]
            acl_id = record[5]

            if (not pkgs.has_key(pkg_name)):
                pkgs[pkg_name] = {}
            if (not pkgs[pkg_name].has_key(collection)):
                pkgs[pkg_name][collection] = {}
            pkgs[pkg_name][collection][acl] = []
            pkgs[pkg_name][collection][acl].append(acl_owner)
            pkgs[pkg_name][collection][acl].append(acl_id)

        return dict(title=page_title, owner=owner, pkgs=pkgs,
                    can_approve=can_approve)

    @expose(allow_json=True)
    def approvepending(self, owner, acls=''):
        '''Approve selected packagelistings.

        :arg owner: The owner of the packagelistings.

        '''

        if not isinstance(acls, (list, tuple)):
            acls = [acls]

        if identity.current.anonymous:
            message = "You must be logged in to approve."
            flash(message)
            url = '/users/pending/%s/' % owner
            redirect(url)

        else:
           user = identity.current.user_name

        if not user == owner:
            message = "You must be the owner to approve."
            flash(message)
            url = '/users/pending/%s/' % owner
            redirect(url)

        if (len(acls) == 1) and (acls[0] == ''):
            message = "Please select at least one packagelisting to approve."
            flash(message)
            url = '/users/pending/%s/' % owner
            redirect(url)

        emsg = '%s has approved the following acls. ' \
               ' You are receiving this email because either you are the' \
               ' owner of one or more of the packages or you have an' \
               ' approveacls on one or more of the packages or your acl is' \
               ' being approved.  You do not need to do anything at this' \
               ' time.\n' % (owner)

        email_recipients = {}
        email_recipients[owner] = owner + "@fedoraproject.org"
        email_recipients[owner] = email_recipients[owner].\
                                      encode('ascii', 'replace')
        for acl_id in acls:
            try:
                PersonPackageListingAclTable.update().\
                    where(PersonPackageListingAclTable.c.id == acl_id).\
                    values(statuscode=STATUS['Approved']).execute()
                session.flush()
            except InvalidRequestError, e:
                session.rollback()  #pyling:disable-msg=E1101
                flash(_('Approving ACL failed for id %d with error: %s') %
                    acl_id, e)
                url = '/users/pending/%s/' % owner
                redirect(url)

            pkgs_query = select((Package.name,
                                 PackageListing.id,
                                 PackageListing.owner,
                                 Collection.name,
                                 Collection.version,
                                 PersonPackageListing.username,
                                 PersonPackageListingAcl.acl),
                                and_(PersonPackageListingAcl.id == acl_id,
                                     PersonPackageListingAcl.\
                                         personpackagelistingid ==
                                         PersonPackageListing.id,
                                     PersonPackageListing.packagelistingid ==
                                         PackageListing.id,
                                     PackageListing.collectionid ==
                                         Collection.id,
                                     PackageListing.packageid == Package.id))
            for record in pkgs_query.execute():
                pkgname = record[0]
                pkglistingid = record[1]
                pkgowner = record[2]
                collection = record[3] + ' ' + record[4]
                acl_owner = record[5]
                acl = record[6]
                email_recipients[pkgowner] = pkgowner + "@fedoraproject.org"
                email_recipients[pkgowner] = email_recipients[pkgowner].\
                                                 encode('ascii', 'replace')
                email_recipients[acl_owner] = acl_owner + "@fedoraproject.org"
                email_recipients[acl_owner] = email_recipients[acl_owner].\
                                                  encode('ascii', 'replace')

                emsg += '\n'
                emsg += ', '.join([pkgname, collection, acl])

                #
                # Get everyone with approveacls on this package.
                #
                app_acls_query = select((PersonPackageListing.username,),
                                        and_(PackageListing.id == pkglistingid,
                                             PackageListing.id == 
                                                 PersonPackageListing.\
                                                 packagelistingid,
                                             PersonPackageListing.id ==
                                                 PersonPackageListingAcl.id,
                                             PersonPackageListingAcl.acl ==
                                                 'approveacls',
                                             PersonPackageListingAcl.\
                                                 statuscode ==
                                                 STATUS['Approved']))
                user_list = app_acls_query.execute()
                for record2 in user_list:
                    username = record[0]

                    email_recipients[username] = \
                        username + "@fedoraproject.org"
                    email_recipients[username] = \
                        email_recipients[username].encode('ascii', 'replace')

        self._send_log_msg(emsg, 'ACL Approval',
                           ('PackageDB', 'pkgdb@fedoraproject.org'),
                           email_recipients.values())

        url = '/users/pending/%s/' % owner
        redirect(url)

        return dict(title='Testing')

