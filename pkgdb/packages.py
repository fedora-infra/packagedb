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
# Fedora Project Author(s): Ionuț Arțăriși <mapleoin@fedoraproject.org>
#
'''
Controller for displaying PackageBuild(Rpm) related information
'''
#
#pylint Explanations
#

# :E1101: SQLAlchemy monkey patches database fields into the mapper classes so
#   we have to disable this when accessing an attribute of a mapped class.

from turbogears import controllers, expose, redirect

from pkgdb.model import PackageBuild, Repo

from fedora.tg.util import request_format


class Package(controllers.Controller):
    '''Display general information related to PackageBuilds.
    '''

    def __init__(self, app_title=None):
        '''Create a Packages Controller

        :kwarg app_title: Title of the web app.
        '''
        self.app_title = app_title

    @expose(template='pkgdb.templates.userpkgpage', allow_json=True)
    def default(self, buildName=None, repo='F-11-i386'):
        '''Retrieve PackageBuild by their name.

        This method returns general packagebuild/rpm information about a
        package like: version, release, size, last changelog message,
        committime etc. This information comes from yum and is stored in
        the pkgdb.

        :arg buildName: Name of the packagebuild/rpm to lookup
        :arg repo: shortname of the repository to look in
        '''
        if buildName == None:
            raise redirect('/packages/list/')

        #pylint:disable-msg=E1101
        builds_query = PackageBuild.query.filter_by(name=buildName)
        #pylint:enable-msg=E1101

        # look for The One packagebuild
        try:
            #pylint:disable-msg=E1101
            build = builds_query.join(PackageBuild.repos).filter(
                Repo.shortname==repo).one()
        except:
            error = dict(status=False,
                         title=_('%(app)s -- Invalid PackageBuild Name') % {
                             'app': self.app_title},
                             message=_('The package build you were linked to'
                             ' (%(pkg)s) does not appear in the Package '
                             ' Database. If you received this error from a link'
                             ' on the fedoraproject.org website, please report'
                             ' it.') % {'pkg': buildName})
            if request_format() != 'json':
                error['tg_template'] = 'pkgdb.templates.errors'
                return error
        other_repos = []
        arches = set()
        for b in builds_query.all():
            other_repos.append(b.repo)
            arches.add(b.architecture)
        other_repos.remove(build.repo)
        


        return dict(title=_('%(title)s -- %(pkg)s') % {
            'title': self.app_title, 'pkg': buildName},
                    repo=repo, build=build, other_repos=other_repos,
                    arches=arches)

