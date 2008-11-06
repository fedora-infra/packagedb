from paver.defaults import *

import sys, os
import glob
import paver.doctools
import paver.runtime
import paver.path

from setuptools import find_packages
from turbogears.finddata import find_package_data

sys.path.insert(0, str(paver.runtime.path.getcwd()))

from pkgdb.release import *

options(
    setup = Bunch(
        name=NAME,
        version=VERSION,
        description=DESCRIPTION,
        author=AUTHOR,
        author_email=EMAIL,
        url=URL,
        download_url=DOWNLOAD_URL,
        license=LICENSE,
        install_requires = [
            "TurboGears[future] >= 1.0",
            "TurboMail",
            "python_fedora >= 0.3.7",
            "SQLAlchemy >= 0.4alpha",
        ],
        scripts = ["start-pkgdb", "server-scripts/pkgdb-sync-repo",
            "server-scripts/pkgdb-sync-bugzilla", "server-scripts/pkgdb-status",
            "clients/pkgdb-client"],
        zip_safe=False,
        packages=find_packages(),
        package_data = find_package_data(where='pkgdb',
                                         package='pkgdb'),
        data_files = [
            (os.path.join(NAME, 'yum.repos.d'), glob.glob('yum.repos.d/*'))
            ],
        keywords = [
            # Use keywords if you'll be adding your package to the
            # Python Cheeseshop

            # if this has widgets, uncomment the next line
            # 'turbogears.widgets',
            # if this has a tg-admin command, uncomment the next line
            # 'turbogears.command',
            'turbogears.app',
        ],
        classifiers = [
            'Development Status :: 4 - Beta',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Environment :: Web Environment',
            'Framework :: TurboGears',
            # if this is an application that you'll distribute through
            # the Cheeseshop, uncomment the next line
            'Framework :: TurboGears :: Applications',
            # if this is a package that includes widgets that you'll distribute
            # through the Cheeseshop, uncomment the next line
            # 'Framework :: TurboGears :: Widgets',
        ],
        test_suite = 'nose.collector',
        ),
    sphinx = Bunch(
        docroot='.',
        builddir='build-doc',
        sourcedir='docs'
        ),
    pylint = Bunch(
        module=['pkgdb']
        )
    )

#
# Generic Tasks
#

try:
    from pylint import lint
    has_pylint = True
except ImportError:
    has_pylint = False

if has_pylint:
    @task
    def pylint():
        '''Check the module you're building with pylint.'''
        options.order('pylint', add_rest=True)
        pylintopts = options.module
        dry('pylint %s' % (" ".join(pylintopts)), lint.Run, pylintopts)
