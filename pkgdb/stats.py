# -*- coding: utf-8 -*-
#
# Copyright © 2007  Ionuț Arțăriși
# Copyright © 2007  Red Hat, Inc.
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
# Author(s): Ionuț Arțăriși <mapleoin@lavabit.com>
#            Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Controller to show general stats about packages.
'''

import sqlalchemy
from sqlalchemy.sql import func, desc, and_, or_, not_

from turbogears import controllers, expose, paginate, config, \
        redirect, identity
from turbogears.database import session
from cherrypy import request

from pkgdb import model
from fedora.tg.util import request_format

ORPHAN_ID = 9900
DEVEL = 8 # collection id
class Stats(controllers.Controller):
    '''Controller which calculates general stats about packages
   
    Things like: total packages, total orphaned packages, most packages owned 
    '''

    def __init__(self, fas, appTitle):
        '''Create a Stats Controller.

        :fas: Fedora Account System object.
        :appTitle: Title of the web app.
        '''
        self.fas = fas
        self.appTitle = appTitle

    @expose(template='pkgdb.templates.stats')
    def index(self):
        if identity.current.anonymous:
           own = 'need to be logged in'
        else:
           own = model.PackageListing.query.filter_by(owner=fasid).count()
        
        # most packages owned in DEVEL collection
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

        # most packages owned or comaintained in DEVEL collection
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
            maintain_names.append(self.fas.cache[
                int(listing.userid)]['username'])
        
        # total number of packages in pkgdb
        total = model.PackageListing.query.count()
        # number of packages with no comaintainers
        no_comaintainers = sqlalchemy.select([model.PackageListing.id], 
            and_(model.PackageListing.id==model.
            PersonPackageListing.packagelistingid,
            model.PackageListing.collectionid==DEVEL, 
            model.PersonPackageListingAcl.
                personpackagelistingid==model.PersonPackageListing.id, 
            not_(or_(model.PersonPackageListingAcl.acl=='commit', 
            model.PersonPackageListingAcl.acl=='approveacls')))).group_by(
            model.PackageListing.id).execute().rowcount    
        # orphan packages in DEVEL 
        orphan_devel = model.PackageListing.query.filter_by(
            owner=ORPHAN_ID, collectionid=DEVEL).count()
        # orphan packages in fedora 8
        orphan_eight = model.PackageListing.query.filter_by(
            owner=ORPHAN_ID, collectionid=14).count()    
        return dict(title=self.appTitle + ' -- Package Stats',
            total=total,
            no_comaintainers=no_comaintainers,
            orphan_devel=orphan_devel, orphan_eight=orphan_eight,
            own=own,
            top_owners_names=top_owners_names, 
            top_owners_list=top_owners_select.execute(),
            maintain_names=maintain_names,
            maintain_list=maintain_select.execute())
 
