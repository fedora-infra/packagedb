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
# Red Hat Author(s): Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Controller for showing Package Collections.
'''

import sqlalchemy
from sqlalchemy.sql import func, desc, and_, or_, not_

from turbogears import controllers, expose, paginate, identity
from turbogears.database import session

from pkgdb import model
from cherrypy import request

ORPHAN_ID = 9900
DEVEL = 8 # collection id
class Collections(controllers.Controller):
    '''Controller that deals with Collections.

    These are methods that expose Collections to the users.  Collections are
    usually a specific release of a distribution.  For instance, Fedora 8.
    '''
    def __init__(self, fas, appTitle):
        '''Create a Packages Controller.

        :fas: Fedora Account System object.
        :appTitle: Title of the web app.
        '''
        self.fas = fas
        self.appTitle = appTitle

    @expose(template='pkgdb.templates.collectionoverview', allow_json=True)
    def index(self):
        '''List the Collections we know about.
        '''
        # pylint: disable-msg=E1101
        collections = model.CollectionPackage.query.order_by(
                (model.CollectionPackage.c.name,
                    model.CollectionPackage.c.version))
        # pylint: enable-msg=E1101
	
	# determine asid
#	fasname = None
#	if fasname == None:
#	    if identity.current.anonymous:
#	        raise identity.IdentityFailure(
#                        'You must be logged in to view your information')
#            else:
#                fasid = identity.current.user.id
#                fasname = identity.current.user_name
#        else:
#	    try:
#		user = self.fas.cache[fasname]
#            except KeyError:
#                error = dict(title=self.appTitle + ' -- Invalid Username',
#                        status = False, pkgs = [],
#                        message='The username you were linked to (%s) cannot' \
#                        ' be found.  If you received this error from' \
#                        ' a link on the fedoraproject.org website, please' \
#                        ' report it.' % fasname
#                    )
#		if request_format != 'json':
      #              error['tg_template'] = 'pkgdb.templates.errors'
      #          return error
      #      fasid = user['id']
	# 0WN3RZ!1
	top_owners_select = sqlalchemy.select(
		[func.count(model.PackageListing.owner).label('numpkgs'), 
		model.PackageListing.owner], and_(
		model.PackageListing.collectionid==DEVEL,
		model.PackageListing.owner!=ORPHAN_ID)).group_by(
		model.PackageListing.owner).order_by(
		desc('numpkgs')).limit(20)
	top_owners_names = []
	for listing in top_owners_select.execute():
	    top_owners_names.append(self.fas.cache[int(listing.owner)]['username'])

	# OWN or comaintain
	maintain_select = sqlalchemy.select(
        	[func.count(model.PersonPackageListing.userid).label('numpkgs'),
        	model.PersonPackageListing.userid, 
		model.PackageListing.collectionid], and_(
		model.PersonPackageListing.packagelistingid==model.
		PackageListing.id,
		model.PackageListing.collectionid==DEVEL)).group_by(
        	model.PersonPackageListing.userid,
		model.PackageListing.collectionid).order_by(
		desc('numpkgs')).limit(20)
	maintain_names =[]
	for listing in maintain_select.execute():
	    maintain_names.append(self.fas.cache[int(listing.userid)]['username'])

	total = model.PackageListing.query.count()
	no_comaintainers = sqlalchemy.select([model.PackageListing.id], 
		and_(model.PackageListing.id==model.
			PersonPackageListing.packagelistingid,
		model.PackageListing.collectionid==DEVEL, 
		model.PersonPackageListingAcl.
			personpackagelistingid==model.PersonPackageListing.id, 
		not_(or_(model.PersonPackageListingAcl.acl=='commit', 
		model.PersonPackageListingAcl.acl=='approveacls')))).group_by(
		model.PackageListing.id).execute().rowcount

	#own = model.PackageListing.query.filter_by(owner=fasid).count()
	
	orphan_devel = model.PackageListing.query.filter_by(owner=ORPHAN_ID, collectionid=DEVEL).count()
	orphan_eight= model.PackageListing.query.filter_by(owner=ORPHAN_ID, collectionid=14).count()	
        return dict(title=self.appTitle + ' -- Collection Overview',
                collections=collections,
		total=total,
		no_comaintainers=no_comaintainers,
		orphan_devel=orphan_devel, orphan_eight=orphan_eight,
		own=1337,
		top_owners_names=top_owners_names, 
		top_owners_list=top_owners_select.execute(),
		maintain_names=maintain_names,
		maintain_list=maintain_select.execute())

    @expose(template='pkgdb.templates.collectionpage', allow_json=True)
    @paginate('packages', default_order='name', limit=100,
            allow_limit_override=True, max_pages=13)
    def id(self, collectionId): # pylint: disable-msg=C0103
        '''Return a page with information on a particular Collection
        '''
        try:
            collectionId = int(collectionId)
        except ValueError:
            error = dict(status = False,
                    title = self.appTitle + ' -- Invalid Collection Id',
                    message = 'The collectionId you were linked to is not a' \
                            ' valid id.  If you received this error from a' \
                            ' link on the fedoraproject.org website, please' \
                            ' report it.')
            if request.params.get('tg_format', 'html') != 'json':
                error['tg_template'] = 'pkgdb.templates.errors'
            return error

        ### FIXME: Want to return additional info:
        # date it was created (join log table: creation date)
        # The initial import doesn't have this information, though.
        try:
            # pylint: disable-msg=E1101
            collectionEntry = model.Collection.query.filter_by(id=collectionId).one()
        except sqlalchemy.exceptions.InvalidRequestError, e:
            # Either the id doesn't exist or somehow it references more than
            # one value
            error = dict(status = False,
                    title = self.appTitle + ' -- Invalid Collection Id',
                    message = 'The collectionId you were linked to, %s, does' \
                            ' not exist.  If you received this error from a' \
                            ' link on the fedoraproject.org website, please' \
                            ' report it.' % collectionId)
            if request.params.get('tg_format', 'html') != 'json':
                error['tg_template'] = 'pkgdb.templates.errors'
            return error

        # Get ownership information from the fas
        try:
            user = self.fas.cache[collectionEntry.owner]
        except KeyError:
            user = {}
            user['human_name'] = 'Unknown'
            user['username'] = 'User ID %i' % collectionEntry.owner
            user['email'] = 'unknown@fedoraproject.org'
        ownerName = '%(human_name)s (%(username)s)' % user

        # Why do we reformat the data returned from the database?
        # 1) We don't need all the information in the collection object
        # 2) We need ownerName and statusname which are not in the specific
        #    table.
        collection = {'name': collectionEntry.name,
                'version': collectionEntry.version,
                'owner': collectionEntry.owner,
                'ownername': ownerName,
                'summary': collectionEntry.summary,
                'description': collectionEntry.description,
                'statusname': collectionEntry.status.translations[0].statusname
                }

        # Retrieve the packagelist for this collection
        packages = model.Package.query.filter(
                sqlalchemy.and_(model.PackageListing.c.collectionid==collectionId,
                    model.PackageListing.c.packageid==model.Package.c.id)
                )
        return dict(title='%s -- %s %s' % (self.appTitle, collection['name'],
            collection['version']), collection=collection, packages=packages)
