# -*- coding: utf-8 -*-
#
# Copyright © 2007, 2009  Ionuț Arțăriși
# Copyright © 2007, 2010  Red Hat, Inc.
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
# Author(s): Ionuț Arțăriși <mapleoin@lavabit.com>
#            Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Controller to show general stats about packages.
'''

from sqlalchemy.sql import select, func, desc, and_, or_, not_

from turbogears import controllers, expose, identity

from pkgdb.model import PackageListing, PersonPackageListing, \
        PersonPackageListingAcl

from pkgdb.lib.utils import STATUS
from pkgdb import _

DEVEL = 8 # collection id
class Stats(controllers.Controller):
    '''Controller which calculates general stats about packages

    Things like: total packages, total orphaned packages, most packages owned 
    '''

    def __init__(self, app_title):
        '''Create a Stats Controller.

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title

    @expose(template='pkgdb.templates.stats', allow_json=True)
    def index(self):
        '''Return a  set of statistics about package ownership.
        '''
        # SQLAlchemy monkey patches the table fields into the mapper classes.
        # So we have to disable this check for any statements which use those
        # attributes on mapper classes (E1101)
        # pylint: disable-msg=E1101
        if identity.current.anonymous:
            own = _('need to be logged in')
        else:
            # SQLAlchemy mapped classes are monkey patched
            # pylint: disable-msg=E1101
            own = PackageListing.query.filter(and_(
                PackageListing.owner==identity.current.user_name,
                PackageListing.statuscode==3,
                PackageListing.collectionid==DEVEL)).count()

        # most packages owned in DEVEL collection
        top_owners_select = select(
                [func.count(PackageListing.owner).label('numpkgs'),
                    PackageListing.owner], and_(
                        PackageListing.collectionid==DEVEL,
                        PackageListing.owner!='orphan')).group_by(
                                PackageListing.owner).order_by(
                                        desc('numpkgs')).limit(20)
        top_owners_selection = top_owners_select.execute().fetchall()
        top_owners_names = []
        for listing in top_owners_selection:
            top_owners_names.append(listing.owner)

        # most packages owned or comaintained in DEVEL collection
        maintain_select = select(
                [func.count(PersonPackageListing.username).label('numpkgs'),
                PersonPackageListing.username,
                PackageListing.collectionid],
            and_(
                PersonPackageListing.packagelistingid==PackageListing.id,
                PackageListing.collectionid==DEVEL)
            ).group_by(
                PersonPackageListing.username,
                PackageListing.collectionid
            ).order_by(
                desc('numpkgs')
            ).limit(20)
        maintain_names = []
        maintain_selection = maintain_select.execute().fetchall()
        for listing in maintain_selection:
            maintain_names.append(listing.username)

        # total number of packages in pkgdb
        total = PackageListing.query.count()
        # number of packages with no comaintainers
        no_comaintainers = select(
                [PackageListing.id],
            and_(
                PackageListing.id==PersonPackageListing.packagelistingid,
                PackageListing.collectionid==DEVEL,
                PersonPackageListingAcl.
                personpackagelistingid==PersonPackageListing.id,
            not_(
                or_(
                    PersonPackageListingAcl.acl=='commit',
                    PersonPackageListingAcl.acl=='approveacls')
                )
            )).group_by(
                PackageListing.id
            ).execute().rowcount
        # orphan packages in DEVEL 
        orphan_devel = PackageListing.query.filter_by(
            statuscode=STATUS['Orphaned'], collectionid=DEVEL).count()
        # orphan packages in fedora 10
        orphan_latest = PackageListing.query.filter_by(
            statuscode=STATUS['Orphaned'], collectionid=19).count()

        return dict(title=_('%(app)s -- Package Stats') % {
            'app': self.app_title},
            total=total,
            no_comaintainers=no_comaintainers,
            orphan_devel=orphan_devel, orphan_latest=orphan_latest,
            own=own,
            top_owners_names=top_owners_names,
            top_owners_list=top_owners_selection,
            maintain_names=maintain_names,
            maintain_list=maintain_selection,
            message='Warning: Do not depend on the json data from this function remaining the same.  It could change, be moved to other functions, or go away at any time.  There is no guaranteed API stability for this function!')
