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

periods = ['year', 'month', 'day', 'hour', 'minute', 'second', 'millisecond', 'microsecond']

periods_short = {
    'year':'y', 
    'month':'m', 
    'day':'d', 
    'hour':'h',
    'minute':'min',
    'second': 's',
    'millisecond': 'ms',
    'microsecond': 'us'
    }

periods_long = dict(((p,p) for p in periods))

def fancy_delta(dt, precision=2, short=False, now=None, verbose=True, gran='minute'):
    """a FancyDateTimeDelta formatter wrapper
    """

    delta = FancyDateTimeDelta(dt, now=now)
    return delta.format(precision=precision, short=short, verbose=verbose, gran=gran)

class FancyDateTimeDelta(object):
    """
    Format the date / time difference between the supplied date and
    the current time using approximate measurement boundaries
    
       delta = FancyDateTimeDelta(datetime(2009,10,10,23,30))
       delta.format()
       >>> 1 day, 7 hours ago
    """

    def __init__(self, dt, now=None):
        """
        computes the difference between now and dt

        :args dt: datetime object
        :kargs now: datetime > dt, datetime.now() is used by default
        """
        if now is None:
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
        self.second = delta.seconds - (60 * self.minute)
        self.millisecond = delta.microseconds / 1000
        self.microsecond = delta.microseconds - (1000 * self.millisecond)

    def format(self, precision=2, short=False, verbose=True, gran='minute'):
        """
        format the computed difference

        :kargs precision: how many pieces will be displayed 
        :kargs short: whether units are displayed in short form second -> s
        :kargs verbose: more freeform feel
        :kargs gran: granularity of the results, smallest computed unit, default 'minute'
        :returns: formated diferrence
        """

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
                if not short:
                    unit = ' ' + unit
                fmt.append("%s%s" % (value, unit))
            if period == gran: # we reached the desired granularity
                break
        if len(fmt) > 0:
            formated = ' '.join(fmt[:precision])
            if verbose:
                formated += " ago"
        else:
            if verbose:
                formated = 'now'
            else:
                formated = ''

        return formated

