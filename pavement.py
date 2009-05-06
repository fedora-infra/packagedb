#!/usr/bin/python -tt
__requires__ = 'TurboGears[future]'
import pkg_resources

from paver.easy import path as paver_path
from paver.easy import sh as paver_sh
from paver.easy import *
import paver.misctasks
from paver import setuputils
setuputils.install_distutils_tasks()

import sys, os
import re
import glob
import paver.doctools
from setuptools import find_packages, command
from turbogears.finddata import find_package_data

sys.path.insert(0, str(paver_path.getcwd()))

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
            'TurboGears[future] >= 1.0',
            'TurboMail',
            'python_fedora >= 0.3.7',
            'SQLAlchemy >= 0.4alpha',
            # Doesn't use setuptools so not on RHEL5
            #'python_bugzilla >= 0.4',
        ],
        scripts = ['start-pkgdb', 'pkgdb.wsgi', 'clients/pkgdb-client',
            'server-scripts/pkgdb-sync-repo',
            'server-scripts/pkgdb-sync-bugzilla'],
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
        message_extractors = {
            'pkgdb': [('**.py', 'python', None),
                ('templates/**.html', 'genshi', None),],
            },
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
        entry_points = {
            'console_scripts': [
                'start-pkgdb = pkgdb.commands:start'
            ],
        },
        ),
    sphinx = Bunch(
        docroot='.',
        builddir='build-doc',
        sourcedir='doc'
        ),
    pylint = Bunch(
        module=['pkgdb']
        ),
    publish=Bunch(
        doc_location='fedorahosted.org:/srv/web/releases/p/a/packagedb/doc/',
        tarball_location='fedorahosted.org:/srv/web/releases/p/a/packagedb/'
        ),
    i18n=Bunch(
        builddir='locale',
        domain='fedora-packagedb',
        ),
    data = Bunch(
        datafiles=['yum.repos.d'],
        localefiles=['locale'],
        docfiles=['docs'],
        conffiles=['pkgdb.cfg', 'pkgdb-client.cfg', {'httpd-pkgdb.conf': 'httpd/conf.d/pkgdb.conf'}],
        ),
    ### FIXME: Eventually, this should be tied into data and a library that
    # finds file location instead.
    installdirs = Bunch(
        prefix='/usr/local',
        execprefix='%(prefix)s',
        bindir='%(execprefix)s/bin',
        sbindir='%(execprefix)s/sbin',
        libexecdir='%(execprefix)s/libexec',
        datadir='%(prefix)s/share',
        sysconfdir='%(prefix)s/etc',
        localstatedir='%(prefix)s/var',
        includedir='%(prefix)s/include',
        infodir='%(datadir)s/info',
        mandir='%(datadir)s/man',
        localedir='%(datadir)s/locale',
        ),
    ### FIXME: Eventually, this should be tied into data and a library that
    # finds file location instead.
    substitute = Bunch(
        # Files to substitute on
        onfiles=['start-pkgdb', 'pkgdb.wsgi', 'server-scripts/pkgdb-sync-repo',
            'server-scripts/pkgdb-sync-bugzilla',
            'update-schema/pkgdb-0.3.10-0.3.11.py', 'httpd-pkgdb.conf'],
        # Strings to substitute inside the files
        patterns={'@CONFDIR@': '/usr/local/etc',
            '@DATADIR@': '/usr/local/share',
            '@SBINDIR@': '/usr/local/sbin'},
        ),
    ### FIXME: These are due to a bug in paver-1.0
    # http://code.google.com/p/paver/issues/detail?id=24
    sdist=Bunch(),
    )

#
# Publish tasks -- somewhat site specific
#

@task
@needs(['html'])
def publish_doc():
    options.order('publish', add_rest=True)
    command = 'rsync -av build-doc/html/ %s' % (options.doc_location,)
    dry(command, paver_sh, command)

@task
@needs(['sdist'])
def publish_tarball():
    options.order('publish', add_rest=True)
    tarname = '%s-%s.tar.gz' % (options.name, options.version)
    command = 'scp dist/%s %s' % (tarname, options.tarball_location)
    dry(command, paver_sh, command)

@task
@needs(['publish_doc', 'publish_tarball'])
def publish():
    pass

#
# convenience tasks to create all messages catalogs instead of one at a time
#

try:
    import babel.messages.frontend
    has_babel = True
except ImportError:
    has_babel = False

if has_babel:
    @task
    def make_catalogs():
        '''Compile all message catalogs for release'''
        options.order('i18n', add_rest=True)
        for po_file in glob.glob('po/*.po'):
            locale, ext = os.path.splitext(os.path.basename(po_file))
            build_dir = paver_path(options.builddir)
            build_dir = build_dir.joinpath(locale, 'LC_MESSAGES')

            build_dir.makedirs(mode=0755)
            if 'compile_catalog' in options.keys():
                defaults = options.compile_catalog
            else:
                defaults = Bunch(domain=options.domain,
                        directory=options.builddir)
                options.compile_catalog = defaults

            defaults.update({'input-file': po_file, 'locale': locale})
            ### FIXME: compile_catalog cannot handle --dry-run on its own
            dry('paver compile_catalog -D %(domain)s -d %(directory)s'
                    ' -i %(input-file)s --locale %(locale)s' % defaults,
                    paver_sh, 'paver compile_catalog -D %(domain)s' \
                        ' -d %(directory)s -i %(input-file)s' \
                        ' --locale %(locale)s' % defaults)
            ### FIXME: Need to get call_task to call this repeatedly
            # because options.compile_catalog has changed
            #dry('paver compile_catalog -D %(domain)s -d %(directory)s'
            #        ' -i %(input-file)s --locale %(locale)s' % defaults,
            #        call_task, 'babel.messages.frontend.compile_catalog', options)

#
# Install tasks
#

### Backends ###

def _apply_root(args, path):
    '''Add the root value to the start of the path'''
    if 'root' in args:
        if path.startswith('/'):
            path = path[1:]
        path = paver_path(os.path.join(args['root'], path))
    else:
        path = paver_path(path)
    return path

def _install_catalogs(args, paths):
    '''Install message catalogs in their proper location on the filesystem.

    Note: To use this with non-default commandline arguments, you must use 
    '''
    # Rebuild message catalogs
    if 'skip_build' not in args and 'skip-build' not in args:
        call_task('make_catalogs')

    options.order('i18n', add_rest=True)

    # Setup the install_dir
    cat_dir = _apply_root(args, paths.localedir)

    for catalog in paver_path(options.builddir).walkfiles('*.mo'):
        locale_dir = catalog.dirname()
        path = paver_path('.')
        for index, nextpath in enumerate(locale_dir.splitall()):
            path = path.joinpath(nextpath)
            if paver_path(options.builddir).samefile(path):
                install_locale = cat_dir.joinpath(os.path.join(
                        *locale_dir.splitall()[index + 1:]))
                install_locale.makedirs(mode=0755)
                install_locale = install_locale.joinpath(catalog.basename())
                if install_locale.exists():
                    install_locale.remove()
                dry('cp %s %s'%  (catalog, install_locale),
                        catalog.copy, install_locale)
                dry('chmod 0644 %s'%  install_locale,
                        install_locale.chmod, 0644)

def _install_conf(args, paths):
    '''Install configuration files'''
    options.order('setup', add_rest=True)
    if 'skip_build' not in args and 'skip-build' not in args:
        call_task('substitute')

    options.order('data', add_rest=True)
    # Setup the install_dir
    conf_dir = apply_root(args, paths.sysconfdir)

    conf_dir.joinpath(options.name)
    if not conf_dir.exists():
        conf_dir.makedirs(mode=0755)

    for conf_file in options.data.conffiles:
        conf_file = paver_path(conf_file)
        installfile = conf_dir.joinpath(conf_file)
        dry('cp %s %s'%  (conf_file, installfile),
                conf_file.copy, install_file)
                dry('chmod 0644 %s'%  install_locale,
                        install_locale.chmod, 0644)

    for catalog in paver_path(options.builddir).walkfiles('*.mo'):
        locale_dir = catalog.dirname()
        path = paver_path('.')
        for index, nextpath in enumerate(locale_dir.splitall()):
            path = path.joinpath(nextpath)
            if paver_path(options.builddir).samefile(path):
                install_locale = cat_dir.joinpath(os.path.join(
                        *locale_dir.splitall()[index + 1:]))
                install_locale.makedirs(mode=0755)
                install_locale = install_locale.joinpath(catalog.basename())
                if install_locale.exists():
                    install_locale.remove()
                dry('cp %s %s'%  (catalog, install_locale),
                        catalog.copy, install_locale)
                dry('chmod 0644 %s'%  install_locale,
                        install_locale.chmod, 0644)
    pass

def _install_data(args, paths):
    pass

def _install_sbin(args, paths):
    pass

# Any install target needs to first look in:
# Commandline
# Default config
#
@task
def install_doc():
    pass

@task
def install_public_code():
    pass

@task
def install_private_code():
    pass

### Frontends -- these are what you invoke with paver ###
@task
@cmdopts([('root=', None, 'Base root directory to install into'),
    ('install-catalogs=', None, 'directory that locale catalogs go in'),
    ('skip-build', None, 'Skip directly to installing'),
    ])
def install_catalogs():
    _install_catalogs(options.install_catalogs)
    pass

### FIXME: setuptools.command.install does not respond to --dry-run
@task
@needs(['setuptools.command.install'])
def install():
    '''Override the setuptools install.'''
    # First override any paths
    for arg in options.install:
        if arg in options.installdirs.keys():
            options.installdirs[arg] = options.install[arg]

    # Then expand all paths
    new = Bunch()
    num_unexpanded = 0
    for path_type in options.installdirs:
        options.installdirs[path_type] = options.installdirs[path_type] % \
                options.installdirs
        new[path_type] = options.installdirs[path_type]

    while num_unexpanded != len(options.installdirs):
        num_unexpanded = len(options.installdirs)
        for path_type in options.installdirs.keys():
            options.installdirs[path_type] = options.installdirs[path_type] % \
                    new
            if new[path_type] == options.installdirs[path_type]:
                del options.installdirs[path_type]
            else:
                new[path_type] = options.installdirs[path_type]

    if num_unexpanded:
        raise PavementError('%s unexpanded path variables.  Correct these in pavement.py installdirs: %s' % (num_unexpanded, options.installdirs))

    # Then call each individual piece of installation
    _install_catalogs(options.install, new)
    _install_conf(options.install, new)
    _install_data(options.install, new)
    _install_sbin(options.install, new)

@task
@needs(['make_catalogs', 'setuptools.command.sdist'])
def sdist():
    pass

#
# Generic Tasks
#

### Substitute path variables ###
@task
@cmdopts([
    ('install-conf=', None, 'Installation directory for configuration files'),
    ('install-data=', None, 'Installation directory for data files'),
    ('install-sbin=', None, 'Installation directory for daemons')
    ])
def substitute():
    options.order('substitutions', add_rest=True)
    substitutions = options.patterns
    if hasattr(options.substitute, 'install_conf'):
        substitutions['@CONFDIR@'] = options.substitute.install_conf
    if hasattr(options.substitute, 'install_data'):
        substitutions['@DATADIR@'] = options.substitute.install_data
    if hasattr(options.substitute, 'install_sbin'):
        substitutions['@SBINDIR@'] = options.substitute.install_sbin

    subRE = re.compile('('+'|'.join(options.patterns.keys())+')+')

    for filename in options.onfiles:
        infile = paver_path(filename + '.in')
        if not infile.exists():
            raise PavementError('Nonexistent file listed in substitute: %s' % infile)
        outf = paver_path(filename)
        contents = []
        for line in infile.lines(encoding='utf8'):
            matches = subRE.search(line)
            if matches:
                for pattern in substitutions:
                    line = line.replace(pattern, substitutions[pattern])
            contents.append(line)
        outf.write_lines(contents, encoding='utf8')

@task
@needs(['substitute', 'setuptools.command.build'])
def build():
    pass

### Pylint ###

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
