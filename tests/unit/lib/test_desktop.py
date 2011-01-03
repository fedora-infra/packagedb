from unittest import TestCase
from nose.tools import *
from StringIO import StringIO

from pkgdb.lib.desktop import Desktop

class TestDesktop(TestCase):

    def test_from_file(self):
        
        desktop = """
[Desktop Entry]
Name=Specto
Comment=Be notified of everything
Comment[fr]=Soyez alerte
Categories=GNOME;Utility;
Exec=specto
Icon=specto
StartupNotify=true
Terminal=false
Type=Application
X-Desktop-File-Install-Version=0.16
"""
        f_desktop = StringIO(desktop)
        d = Desktop.from_file(f_desktop)

        assert_equals(d.command, u'specto')
