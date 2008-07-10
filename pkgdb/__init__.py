'''
Fedora Package Database

A web application that manages ownership information for the packages in the
Fedora Collection.
'''
from pkgdb import release
__version__ = release.VERSION

# Assign a gettext function to "_" so that we can use it for i18n work.
# Note: importing turbogears assigns this to a builtin _
# pylint: disable-msg=W0611,E0601
import turbogears
_ = _
# pylint: enable-msg=W0611,E0601
