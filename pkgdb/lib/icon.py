#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
#
# Copyright © 2010  Red Hat, Inc.
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
# Author(s): Martin Bacovsky <mbacovsk@redhat.com>
#
'''
icon manipulation library
'''
import Image
import re
import base64
from StringIO import StringIO

RE_THEME_IN_PATH = re.compile(r'share/icons/([^/]*)/')
RE_NAME_IN_PATH = re.compile(r'/([^/]+)\.png$')


class Icon(object):
    """Class represents icon image with name and theme.

    It can parse name and theme from filepath.
    Export with resize is available.
    """

    def __init__(self, name, data, theme='default'):
        self.img = Image.open(data)
        self.name = name
        self.theme = theme


    @classmethod
    def from_filename(self, filename, data):
        """Create Icon object.

        Try to guess theme and icon name from filepath

        :arg filename: full filename (with path)
        :arg data: open file that holds PNG image
        :returns: Icon onject
        """
        # theme
        match = RE_THEME_IN_PATH.search(filename)
        if match:
            theme = match.groups()[0]
        else:
            theme = 'default'

        # name
        match = RE_NAME_IN_PATH.search(filename)
        name = match.groups()[0]

        return self(name, data, theme)


    def __str__(self):
        return 'Icon(%r, theme=%r, size=%r)' % (
            self.name, self.theme, self.size)
       

    def export(self, size=None):
        """Export Icon 

        :arg size: (optional) if specified, resize during export.
        :returns: open file with PNG image
        """
        if size is None:
            size = self.size

        data = StringIO()

        if self.size == size:
            ex_img = self.img
        else:
            ex_img = self.img.copy()
            ex_img.thumbnail((48, 48), Image.ANTIALIAS)

        ex_img.save(data, "PNG")
        data.seek(0)

        return data
    
    @property
    def size(self):
        return max(self.img.size)


    def check(self):
        """Check if we can process the image.
        """
        self.img.load()
    
    @property
    def group_key(self):
        return "%s:%s" % (self.name, self.theme)


def noicon_png():
    return base64.b64decode(
		"iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAA"
		"N1wAADdcBQiibeAAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAW4SURBVGiB7Z"
		"rPaxNNGMc/2WySDUkN5k2wiPFn43uw0aJQ9WKjoMJ78VSQHgQ9iSAieHz/AEEUzx5706u8UCyF4EWJp"
		"dbW5m0j2miMpuQ3Kdmk6e6+hzZLsk1qou/7mry8XxhmntmZ4fvs88w8szNrikajJsADeDdzD/CLIXcB"
		"ls0k1uViG3UmQN1MWgdlBSgAuc2UNZRX/H7/hAj8CvxJD+Ldu3d2Adj5s4n8ALwiLRQwm816EgQBAJP"
		"JpOetys3qNE1rGLtdWVEUVFVtyBVF2V6B/fv3I4qiTqCbUK1WicVi9VWeLQpYLJZ/k1NHMJvNxipvwx"
		"youUq3QhAEo2c0KtBEw66DgaOn1xXwCmwEKaD7XQi2cHQJgK5SN648Rhg4WgSg+197a4gCG3uVnoHBA"
		"mJbFtA0jWKxSLVaBUCWZdbW1rbto6oqkUiESqXyA3S34rtcqFQqcffuXR4/fgzA+Pg4L1682LaPqqrM"
		"zMwgy/IP0P0mRJE6F/rWJI7FYsTjcV2uVqtMTk7y/v17Dhw4wIULF7BarfrzfD6PoiisrKwQCoWIx+O"
		"cP3+effv2MTU1RTKZ5MiRIwSDQSYmJigUCqRSKXw+H5cuXWrK4btcqIYzZ87w7NkzXY5EIiwtLXHt2j"
		"WWl5eZm5vTn2maxtevX1lfX2dychKr1crt27fx+/28fPkSWZa5cuUKoVCIRCJBLpejUCgwOjpKOBymU"
		"Ci0o4Clo0k8ODhIpVIhmUwCUC6XsdlsOBwOJEmiVCo17SfLMi6XC7PZjCRJyLKM0+nE6XRiNpt1N9uz"
		"Zw9ut1sfuw10ZgGTycTFixf1CRwIBLDZbNy7dw+A48ePN+0XDAaZn5/n4cOHhMNhTp48SSKR4P79+ww"
		"MDHDo0KF2KWyxgCkajYaAEYC+vj76+/vbHqwGRVHa2oZUKhVsNlvH/eqRSqXI5/M1ceFviQPtkqgn30"
		"m/bdCZC3UD/vGtRCaTYWJiAoBQKMTnz5+btnv16hXRaLShbnp6mqWlpW3Hb7aMtowDxWKRYrGoy+VyG"
		"VVVG8rlcplcLqd/xwqCgCRJALx+/ZpUKoWmaRQKhYagFolEiMfjDSvX4uIiHz9+1OU2gqAotnry6dMn"
		"pqamUFUVWZa5ceMGjx494vTp0wwMDPDgwQPu3LnDkydPsNvtJJNJLl++zNraGqFQiGAwqI/15s0b5uf"
		"nWV1dxeVyMTY2ptfPzc1htVq5fv263r5UKjE+Po7FYqFSqXD16lXsdnszmiYBWK9J9acDHo8Hn8+nk4"
		"vFYgwPDzM7O8vs7CyHDx/G5XJx9OhRrFYr6+vrDYGsHj6fD6/XiyRJLCws6FY9ePAgt27dIpPJsLy83"
		"KBwNpvF4/GQy+V4+/Ztq/estlRgZmaGaDTKuXPnMJlMVCoVhoaG+PLlC+FwmOHhYdLpNE+fPmVkZIQd"
		"O3a03Lg9f/6cfD7PqVOnAPR22WyWVCpFtVrF6XTq7WtB79ixY4yOjm63tKvmmzdvjgGHAKxWK319fQB"
		"IksSHDx/IZDI4HA78fj8ej0c/lzl79ix2u51MJsPCwgJerxePx8OuXbvIZDIMDQ2RSCTYu3cv/f39LC"
		"4uoigKoigSCATI5/NIksT09DQnTpwgEAiwsrKC2+1mcHAQRVEIh8MkEgn8fr/Oq1Qq1UfpvCkajf4B/"
		"AbgcDjYvXt3K227Aul0mlwuVxOXW7pQj0ARgOrPZtEJDC+59STuEag9ZwED/hsW6CkFms2BXnYhpecs"
		"YMD/LvSzoQjAak3qQQusCkCmJhku0LoSBo65BgU0TdO/uLoVzRRIb9Og67CtBZo06DoYPCQrYlAglUp"
		"hsVgaLrnNZnPTg19jXStZ0zR98nVSrr/crr/wrkNOxOBC5XK53XPJbkBO8Pv9MtD8VLb7ka8dq/wO+A"
		"A3G7/YuOvKO9n4deafhMbGjmCdjcBaywtAajOlDeUsEP4L/cjW2K2b0/EAAAAASUVORK5CYII=")
