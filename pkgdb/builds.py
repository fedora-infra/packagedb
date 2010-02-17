# -*- coding: utf-8 -*-
#
# Copyright © 2009  Red Hat, Inc.
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
# Red Hat Project Author(s): Martin Bacovsky <mbacovsk@redhat.com>
#
'''
Controller for displaying PackageBuild related information
'''
#
#pylint Explanations
#

# :E1101: SQLAlchemy monkey patches database fields into the mapper classes so
#   we have to disable this when accessing an attribute of a mapped class.

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import and_, or_, literal_column, union
from sqlalchemy import Text, Integer

from turbogears import controllers, expose, identity, redirect, flash
from turbogears import paginate
from turbogears.database import session

from pkgdb.model import Repo, PackageBuild, RpmFiles, RpmProvides
from pkgdb.model import RpmRequires, PackageBuildDepends
from pkgdb import release, _

from fedora.tg.util import request_format

from operator import itemgetter
import re

import logging
log = logging.getLogger('pkgdb.builds')

class BuildsController(controllers.Controller):
    
    def __init__(self, app_title=None):
        '''Create an Builds Controller

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title


    @expose(template='pkgdb.templates.builds')
    def default(self):
        '''Builds Home Page
        '''

        redirect('/apps/name/list/a*')

    
    @expose(template='pkgdb.templates.builds_search')
    @paginate('build_list', limit=90, default_order=('-score','name'), max_limit=None,
            max_pages=13) #pylint:disable-msg=C0322
    def search(self, *pattern):
        '''Builds search result

        :arg pattern: pattern to be looked for in apps.

        Search is performed on name, license, architecture, version, release,
        provides, requires, obsoletes, depends and files. Results are sorted according 
        to relevancy. Parts where pattern was recognized are shown
        in listing.
        '''

        pattern = '/'.join(pattern)

        build_base = {}

        if len(pattern) == 0:
            flash('Insert search pattern...')

        s_pattern = self._parse_pattern(pattern)

        builds_raw = self._builds_search_query(s_pattern).statement.execute()

        for b in builds_raw:
            build_base[b.id] = self._score_build(b, s_pattern, build_base.get(b.id, None))

        #build_list = sorted(build_base.values(), key=itemgetter('score'), reverse=True)

                
        return dict(title=self.app_title, version=release.VERSION,
            pattern=pattern, s_pattern=s_pattern, build_list=build_base.values())

    
    def _score_build(self, b, pattern, update=None):
        result = {
            'name': b.name,
            'epoch': b.epoch,
            'release': b.release,
            'version': b.version,
            'arch': b.architecture,
            'repo': b.repo,
            'license': b.license,
            'committer': b.committer,
            'score': 0,
            'obsoletes': [],
            'provides': [],
            'requires': [],
            'conflicts': [],
            'depends': [],
            'files': [],
        }

        score = 0

        if pattern.has_key('default'):
            for p in pattern['default']:
                p = p.lower()
                if p in b.name.lower():
                    score += 5
                if p in b.license.lower():
                    score += 1
                if p in b.committer.lower():
                    score += 2

        if pattern.has_key('arch:'):
            for p in pattern['arch:']:
                if p.lower() in b.architecture.lower():
                    score += 3
            
        if pattern.has_key('repo:'):
            for p in pattern['repo:']:
                if p.lower() in b.repo.lower():
                    score += 3

        if pattern.has_key('file:'):
            result['files'] = [b.files]
            score += 3

        if pattern.has_key('provides:'):
            result['provides'] = [b.provides]
            score += 3

        if pattern.has_key('requires:'):
            result['requires'] = [b.requires]
            score += 3

        if pattern.has_key('depends:'):
            result['depends'] = [b.depends]
            score += 3

        result['score'] = score

        if update:
            result['score'] += update['score']
            result['files'].extend(update['files'])
            result['provides'].extend(update['provides'])
            result['requires'].extend(update['requires'])
            result['depends'].extend(update['depends'])

        return result
        
    
    def _parse_pattern(self, pattern):
        p = re.compile(r'\s+')
        s_pattern = {}
        for pat in  p.sub(' ', pattern).split(' '):
            found = False
            for prefix in ['repo:', 'arch:', 'file:', 'provides:', 'requires:', 'depends:']:
                if pat.startswith(prefix):
                    tmp = s_pattern.get(prefix, [])
                    tmp.append(pat[len(prefix):])
                    s_pattern[prefix] = tmp
                    found = True
                    break
            if not found:
                tmp = s_pattern.get('default', [])
                tmp.append(pat)
                s_pattern['default'] = tmp

        return s_pattern


    def _builds_search_query(self, pattern):
                
        columns = [
            PackageBuild.id,
            PackageBuild.name,
            PackageBuild.epoch,
            PackageBuild.version,
            PackageBuild.release,
            PackageBuild.architecture,
            PackageBuild.license,
            PackageBuild.committer,
            Repo.shortname.label('repo'),
        ]

        join = [PackageBuild.repos]

        filter = []

        if pattern.has_key('default'):
            filter.extend(
                (or_(
                    PackageBuild.name.ilike('%%%s%%' % p),
                    PackageBuild.license.ilike('%%%s%%' % p),
                    PackageBuild.committer.ilike('%%%s%%' % p))
                    for p in pattern['default'])
            )
        if pattern.has_key('arch:'):
            filter.append(
                or_(*(PackageBuild.architecture.ilike(p.replace('*', '%')) for p in pattern['arch:'])))

        if pattern.has_key('repo:'):
            filter.append(
                or_(*(Repo.shortname.ilike(p.replace('*', '%')) for p in pattern['repo:'])))

        if pattern.has_key('file:'):
            filter.append(
                or_(*(RpmFiles.name.ilike(p.replace('*', '%')) for p in pattern['file:'])))
            join.append(RpmFiles)
            columns.append(RpmFiles.name.label('files'))

        if pattern.has_key('provides:'):
            filter.append(
                or_(*(RpmProvides.name.ilike(p.replace('*', '%')) for p in pattern['provides:'])))
            join.append(RpmProvides)
            columns.append(RpmProvides.name.label('provides'))

        if pattern.has_key('requires:'):
            filter.append(
                or_(*(RpmRequires.name.ilike(p.replace('*', '%')) for p in pattern['requires:'])))
            join.append(RpmRequires)
            columns.append(RpmRequires.name.label('requires'))

        if pattern.has_key('depends:'):
            filter.append(
                or_(*(PackageBuildDepends.packagebuildname.ilike(p.replace('*', '%')) for p in pattern['depends:'])))
            join.append(PackageBuildDepends)
            columns.append(PackageBuildDepends.packagebuildname.label('depends'))

        builds_query = session.query(*columns)\
            .join(*join)\
            .filter(and_(*filter))

        return builds_query


    @expose(template='pkgdb.templates.builds')
    @paginate('build_list', limit=50, default_order='name', max_limit=None,
            max_pages=13) #pylint:disable-msg=C0322
    def name(self, searchwords='a*' ):
        '''Builds view by name

        :arg searchwords: filter used by letter_paginator
        '''
        
        pattern = searchwords.replace('*','%')
        #pylint:disable-msg=E1101
        build_list = session.query(PackageBuild)\
                .filter(
                    PackageBuild.name.ilike(pattern))
        #pylint:enable-msg=E1101

        return dict(title=self.app_title, version=release.VERSION,
            searchwords=searchwords, list_type='name',
            build_list=build_list, pattern='')


    @expose(template='pkgdb.templates.build')
    def show(self, shortname, buildname, epoch, version, rel, arch):
        
        try:
            repo = session.query(Repo).filter_by(shortname=shortname).one()
        except NoResultFound:
            flash('Repo "%s" was not found' % shortname)
            redirect('/builds')

        try:
            build = session.query(PackageBuild)\
                .join(PackageBuild.repos)\
                .filter(and_(
                    PackageBuild.name==buildname,
                    PackageBuild.epoch==epoch,
                    PackageBuild.version==version,
                    PackageBuild.release==rel,
                    PackageBuild.architecture==arch,
                    Repo.id==repo.id))\
                .one()
        except NoResultFound:
            flash('Build (%s-%s:%s-%s.%s) was not found' % (buildname, epoch, version, rel, arch))
            redirect('/builds')

        return dict(title=self.app_title, version=release.VERSION,
            build=build)
            

                
        


