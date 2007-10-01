import os
import distutils

import setuptools
from setuptools import setup, find_packages
from turbogears.finddata import find_package_data

execfile(os.path.join("pkgdb", "release.py"))

class build_scripts(distutils.command.build_scripts):
    '''Build the package, changing the directories in start-pkgdb.py.'''
    # Set the correct directories in start-pkgdb.py
    def run(self):
        '''Substitute special variables with our install lcoations.
        
        @CONFDIR@ => /usr/local/etc
        @DATADIR@ => /usr/local/share
        '''

        super(build_scripts, self).run()

class install(setuptools.command.install):
    '''Override setuptools and install the package in the correct place for
    an application.'''

    def run(self):
        super(install, self).run()
        pass
        # Install to datadir/pkgdb
        # Install conffile to confdir/pkgdb.cfg
        pass

class install_app(setuptools.command.install_lib):
    def run(self):
        super(install_private_lib, self).run()
        pass

setup(
    name="packagedb",
    version=version,
    
    # uncomment the following lines if you fill them out in release.py
    description=description,
    author=author,
    author_email=email,
    url=url,
    download_url=download_url,
    license=license,
    
    cmdclass={'build_scripts': build_scripts,
              'install': install,
              'install_private_lib': install_private_lib},
    install_requires = [
        "TurboGears >= 1.0",
        "SQLAlchemy >= 0.3.10, < 0.4alpha",
    ],
    scripts = ["start-pkgdb.py"],
    config_files=('pkgdb.cfg',),
    zip_safe=False,
    packages=find_packages(),
    package_data = find_package_data(where='pkgdb',
                                     package='pkgdb'),
    keywords = [
        # Use keywords if you'll be adding your package to the
        # Python Cheeseshop
        
        # if this has widgets, uncomment the next line
        # 'turbogears.widgets',
        
        # if this has a tg-admin command, uncomment the next line
        # 'turbogears.command',
        
        # if this has identity providers, uncomment the next line
        # 'turbogears.identity.provider',
    
        # If this is a template plugin, uncomment the next line
        # 'python.templating.engines',
        
        # If this is a full application, uncomment the next line
        'turbogears.app',
    ],
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Framework :: TurboGears',
        # if this is an application that you'll distribute through
        # the Cheeseshop, uncomment the next line
        'Framework :: TurboGears :: Applications',
        
        # if this is a package that includes widgets that you'll distribute
        # through the Cheeseshop, uncomment the next line
        # 'Framework :: TurboGears :: Widgets',
    ],
    test_suite = 'nose.collector',
    )
