# -*- coding: utf-8 -*-
#
# Copyright © 2009  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.  You should have
# received a copy of the GNU General Public License along with this program;
# if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
# Fifth Floor, Boston, MA 02110-1301, USA. Any Red Hat trademarks that are
# incorporated in the source code or documentation are not subject to the GNU
# General Public License and may only be used or replicated with the express
# permission of Red Hat, Inc.
#
# Red Hat Project Author(s): Martin Bacovsky <mbacovsk@redhat.com>
#
'''
Various profiling utilites
'''
import os
import sys

import logging
log = logging.getLogger('profiler')

def label(code):
    if isinstance(code, str):
        return ('~', 0, code)    # built-in functions ('~' sorts at the end)
    else:
        return '%s %s:%d' % (code.co_name,
                             code.co_filename,
                             code.co_firstlineno)

# KCacheGrind taken from lsprofcalltree.py: lsprof output which is readable by kcachegrind
# David Allouche
# Jp Calderone & Itamar Shtull-Trauring
# Johan Dahlin
class KCacheGrind(object):
    def __init__(self, profiler):
        self.data = profiler.getstats()
        self.out_file = None

    def output(self, out_file):
        self.out_file = out_file
        print >> out_file, 'events: Ticks'
        self._print_summary()
        for entry in self.data:
            self._entry(entry)

    def _print_summary(self):
        max_cost = 0
        for entry in self.data:
            totaltime = int(entry.totaltime * 1000)
            max_cost = max(max_cost, totaltime)
        print >> self.out_file, 'summary: %d' % (max_cost,)

    def _entry(self, entry):
        out_file = self.out_file

        code = entry.code
        #print >> out_file, 'ob=%s' % (code.co_filename,)
        if isinstance(code, str):
            print >> out_file, 'fi=~'
        else:
            print >> out_file, 'fi=%s' % (code.co_filename,)
        print >> out_file, 'fn=%s' % (label(code),)

        inlinetime = int(entry.inlinetime * 1000)
        if isinstance(code, str):
            print >> out_file, '0 ', inlinetime
        else:
            print >> out_file, '%d %d' % (code.co_firstlineno, inlinetime)

        # recursive calls are counted in entry.calls
        if entry.calls:
            calls = entry.calls
        else:
            calls = []

        if isinstance(code, str):
            lineno = 0
        else:
            lineno = code.co_firstlineno

        for subentry in calls:
            self._subentry(lineno, subentry)
        print >> out_file

    def _subentry(self, lineno, subentry):
        out_file = self.out_file
        code = subentry.code
        #print >> out_file, 'cob=%s' % (code.co_filename,)
        print >> out_file, 'cfn=%s' % (label(code),)
        if isinstance(code, str):
            print >> out_file, 'cfi=~'
            print >> out_file, 'calls=%d 0' % (subentry.callcount,)
        else:
            print >> out_file, 'cfi=%s' % (code.co_filename,)
            print >> out_file, 'calls=%d %d' % (
                subentry.callcount, code.co_firstlineno)

        totaltime = int(subentry.totaltime * 1000)
        print >> out_file, '%d %d' % (lineno, totaltime)


class Profiler(object):
    """Performance anlyzer
    
    collects profiling data, that are saved as kcachegrind profile (.kcg suffix). Optionaly it can 
    store captured sql statements (.sql) (sqlalchemy log has to be set to INFO level)
    and some memory stats (.mem). The memory statistics shows reachable and unreachable objects
    that remain in memory after function call.

    Output is stored to selected directory, files have name derived from 
    name of decorated function.

    Usage:
   
    p = Profiler(directory='/tmp/profiles')
    p.profileit(some_function, *args, **kvargs)

    """

    def __init__(self, directory='/var/tmp/profileit', sql=True, mem=True):
        """Profiler constructor

        :args directory: directory where the output is stored
        :args sql: capture sql statements
        :args mem: analyze memory
        """

        self.directory = directory
        self.sql = sql
        self.mem = mem

        # create directory if it does not exist
        if not os.path.exists(directory):
            os.makedirs(directory)


    def filename(self, func_name):
        filename = os.path.join(self.directory, func_name)
        suffix = 0
        while os.path.isfile('%s%s.kcg' % (filename, ('', '_%s' % suffix)[suffix>0])):
            suffix += 1

        return '%s%s' % (filename, ('', '_%s' % suffix)[suffix>0])


    
    def profileit(self, func, *args, **kvargs):
        """Wraps method in cprofiler call and collects data

        :args func: function 
        :args args: arguments
        :args kvargs: keyvalue arguments
        """

        filename = self.filename(func.__name__)
        prof_res = open('%s.kcg' % filename, 'w')

        if self.sql:
            # get ready sql handler
            sql_log = logging.FileHandler('%s.sql' % filename)
            sql_log.setLevel(logging.INFO)
            formatter = logging.Formatter('%(message)s')
            sql_log.setFormatter(formatter)
            logging.getLogger('sqlalchemy.engine.base.Engine').addHandler(sql_log)

        # profile
        import cProfile
        p = cProfile.Profile()

        # setup memory profiler
        if self.mem:
            from guppy import hpy
            hp = hpy()
            # the following sequence seems to set consistent results 
            # it would be nice to know why ;)
            hp.setref()
            hp.setref()
            start = hp.heap().size
            hp.setref()

        # call the function
        res = p.runcall(func, *args, **kvargs)

        # store memory data
        if self.mem:
            heap = hp.heap()
            mem_diff = heap.size - start
            stat = hp.heapu()
            mem_res = open('%s.mem' % filename, 'w')
            print >> mem_res, "Memory difference: %s" % mem_diff
            print >> mem_res, heap 
            print >> mem_res, stat
            mem_res.close()

        # stop sql capturing
        if self.sql:
            logging.getLogger('sqlalchemy.engine.base.Engine').removeHandler(sql_log)

        # format profiling data
        k = KCacheGrind(p)
        k.output(prof_res)
        prof_res.close()

        return res


def profileit(directory='/var/tmp/profileit', sql=True, mem=True):
    """Performance anlyzer decorator
    
    Wraps method in cprofiler call and collects data,
    that are saved as kcachegrind profile (.kcg suffix). Optionaly it can 
    store captured sql statements (.sql) (sqlalchemy log has to be set to INFO level)
    and some memory stats (.mem). The memory statistics shows reachable and unreachable objects
    that remain in memory after function call.

    Output is stored to selected directory, files have name derived from 
    name of decorated function.

    Usage:
    
    @expose()
    @profileit()
    @expose(template='pkgdb.templates.index')
    def index(self):
        ...

    :args directory: directory where the output is stored
    :args sql: capture sql statements
    :args mem: analyze memory
    """

    def _my(func):
        def _func(*args, **kvargs):
            prof = Profiler(directory, sql, mem)
            res = prof.profileit(func, *args, **kvargs)
            return res
        return _func
    return _my
