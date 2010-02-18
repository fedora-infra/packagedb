# -*- coding: utf-8 -*-
#
# Copyright © 2007-2009  Red Hat, Inc.
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
# Red Hat Author(s): Martin Bacovsky <mbacovsk@redhat.com>    
#

from datetime import datetime

periods = ['year', 'month', 'day', 'hour', 'minute']
periods_short = {
    'year':'y', 
    'month':'m', 
    'day':'d', 
    'hour':'h',
    'minute':'min'
    }
periods_long = dict(((p,p) for p in periods))

def fancy_delta(dt, precision=2, short=False):
    delta = FancyDateTimeDelta(dt)
    return delta.format(precision, short)

class FancyDateTimeDelta(object):
    """
    Format the date / time difference between the supplied date and
    the current time using approximate measurement boundaries
    
    delta = FancyDateTimeDelta(datetime(2009,10,10,23,30))
    delta.format()
    >>> 1 day, 7 hours ago

    """

    def __init__(self, dt):
        now = datetime.now(dt.tzinfo)
        delta = now - dt
        self.year = delta.days / 365
        self.month = delta.days / 30 - (12 * self.year)
        if self.year > 0:
            self.day = 0
        else: 
            self.day = delta.days % 30
        self.hour = delta.seconds / 3600
        self.minute = delta.seconds / 60 - (60 * self.hour)

    def format(self, precision=2, short=False):
        fmt = []
        if short:
            periods_d = periods_short
        else:
            periods_d = periods_long

        for period in periods:
            value = getattr(self, period)
            if value:
                unit = periods_d[period]
                if value > 1 and not short:
                    unit += "s"
                fmt.append("%s %s" % (value, unit))
        if len(fmt) > 0:
            formated = ", ".join(fmt[:precision]) + " ago"
        else:
            formated = 'now'

        return formated

