from nose.tools import *
from unittest import TestCase
from minimock import Mock
import os

from pkgdb.lib.rpmlib import RPM, YumProxy
import pkgdb
from yum.packages import YumAvailablePackage

class TestRPMLib(TestCase):
    
    def test_executables(self):
        EXECUTABLE_MODE = 33261L

        yum = YumProxy()
        yum.add_repo('pkgdb-basic', 'file://%s/' % pkgdb.__path__[0], '../tests/repo-basic/')

        build = yum.builds_by_name('pkgdb-basic', ['specto'])[0]

        rpm = RPM(build, yum.yumbase)
        
        exe = rpm.executables
        assert_equals(list(exe), ['/usr/bin/specto'])

        # fake filelist with false positives
        rpm._hdr = {
            'filenames': [
                '/usr/bin/specto',
                '/usr/lib/libgdkmm-3.0.so.1',
                '/usr/lib64/liblastfm.so.0',
                '/usr/share/gnome/help/evolution/sl/figures/plus.png',
                '/usr/lib64/ImageMagick-6.6.5/modules-Q16/coders/yuv.la'],
            'filemodes': [EXECUTABLE_MODE] * 5
        }

        exe = rpm.executables
        assert_equals(list(exe), ['/usr/bin/specto'])

        # recover from non-utf8 filenames
        rpm._hdr = {
            'filenames': [
                '/usr/bin/specto',
                '/data/zub\u0159\xedk'],
            'filemodes': [EXECUTABLE_MODE] * 2
        }

        exe = rpm.executables
        assert_equals(list(exe), ['/usr/bin/specto'])
