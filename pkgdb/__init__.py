'''
Fedora Package Database

A web application that manages ownership information for the packages in the
Fedora Collection.
'''
import gettext
translation = gettext.translation('fedora-packagedb', '/usr/share/locale',
                fallback=True)
_ = translation.ugettext

# Assign a gettext function to "_" so that we can use it for i18n work.
# :W0611: we have to import turbogears so we get access to the builtin _
# :W0622: _ is assigned to a builtin by turbogears but we want to be able to
#   access it from code that might not import TurboGears
# :E0601: _ is defined as a builtin by the turbogears import
# pylint: disable-msg=W0611,W0622,E0601
### FIXME: Disable this for now because it causes problems for creating the
# initial egg_info.  After we get an actual method of switching catalogs,
# revisit whether we must use the TG catalogs or canuse gettext.
#import turbogears
#_ = _
# pylint: enable-msg=W0611,W0622,E0601

from pkgdb import release
__version__ = release.VERSION
