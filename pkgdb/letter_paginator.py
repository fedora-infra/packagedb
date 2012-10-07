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
# Fedora Project Author(s): Ionuț Arțăriși <mapleoin@fedoraproject.org>
#
'''
Module to be used for letter pagination and search.
'''
#
# PyLint Explanations
#

# :E1101: SQLAlchemy mapped classes are monkey patched.  Unless otherwise
#   noted, E1101 is disabled due to a static checker not having information
#   about the monkey patches.
# :C0322: Disable space around operator checking in multiline decorators

from sqlalchemy.sql import or_
from sqlalchemy.orm import lazyload
from turbogears import controllers, expose, paginate, config
from turbogears.database import session

from pkgdb.model import Application, Package, PackageBuild, Tag
from pkgdb.lib.utils import STATUS
from pkgdb import _

import logging
log = logging.getLogger(__name__)

from cherrypy import request

class Letters(controllers.Controller):
    '''Display package lists with letter pagination, search and links
    '''

    def __init__(self, app_title=None):
        self.app_title = app_title

    @expose(template='pkgdb.templates.pkgbugoverview', allow_json=True)
    @paginate('packages', default_order='name', limit=100, max_limit=None,
            max_pages=13) #pylint:disable-msg=C0322
    def default(self, searchwords=''):
        '''Return a list of all packages in the database.

           :kwarg searchwords: optional - string to restrict the list, can use
                * and ? as wildcards
        '''
        sql_searchwords = ''
        if searchwords:
            # Escape special chars and turn shell-style '*' and '?' wildcards
            # into sql '%' and '_' wildcards
            sql_searchwords = searchwords.replace('\\\\', '\\\\\\\\')\
                    .replace('%', '\\%').replace('_', '\\_')\
                    .replace('*', '%').replace('?', '_')

        server_webpath = config.get('server.webpath', '/pkgdb')
        if request.path.startswith("%s/acls/" % server_webpath):
            if request.path.startswith('%s/acls/bugs/' % server_webpath):
                mode = 'acls/bugs/'
                bzUrl = config.get('bugzilla.url',
                                   'https://bugzilla.redhat.com/')
            else:
                mode = 'acls/name/'
                bzUrl = ''
            if sql_searchwords != '':
                if sql_searchwords.isdigit() and int(sql_searchwords) < 10: # 0-9
                    #pylint:disable-msg=E1101
                    packages = Package.query.options(
                            lazyload('listings2'), lazyload('status')
                        ).filter(or_(Package.name.between('0','9'),
                                     Package.name.like('9%')))
                    #pylint:enable-msg=E1101
                else: 
                    #pylint:disable-msg=E1101
                    packages = Package.query.options(
                        lazyload('listings2'),
                        lazyload('status')).filter(
                            Package.name.ilike(sql_searchwords, escape='\\\\')
                            ).order_by(Package.name.asc())
                    #pylint:enable-msg=E1101
            else:
                #pylint:disable-msg=E1101
                packages = Package.query.options(lazyload('listings2'),
                            lazyload('status'))
                #pylint:enable-msg=E1101
            # minus removed packages
            #pylint:disable-msg=E1101
            packages = packages.filter(
                    Package.statuscode!=STATUS['Removed'])
            #pylint:enable-msg=E1101
        else:
            mode = 'tag/'
            bzUrl = ''
            if sql_searchwords:
                #pylint:disable-msg=E1101
                packages = session.query(Application).join('tags').filter(
                        Tag.name.ilike(sql_searchwords, escape='\\\\')).all()
                #pylint:enable-msg=E1101
            else:
                packages = PackageBuild.query.all() #pylint:disable-msg=E1101

        # generate the statusMap and collectn_map
        statuses = set()
        collectn_map = {}
        pkg_list = []
        for pkg in packages:
            pkg.json_props = {'Package':('listings',)}
            pkg_list.append(pkg)
            statuses.add(pkg.statuscode)
            for pkglisting in pkg.listings:
                if pkglisting.collection.collectionid not in collectn_map:
                    collectn_map[pkglisting.collection.collectionid] = \
                        pkglisting.collection.branchname
        statusMap = dict([(statuscode, STATUS[statuscode]) for statuscode in statuses])

        return dict(title=_('%(app)s -- Packages Overview %(mode)s') % {
            'app': self.app_title, 'mode': mode.strip('/')},
                       searchwords=searchwords, packages=pkg_list, mode=mode,
                       bzurl=bzUrl, statusMap=statusMap, collectn_map=collectn_map)
