from unittest import TestCase
from nose.tools import *
from nose.plugins.logcapture import MyMemoryHandler
import sys
from StringIO import StringIO
import logging

from sqlalchemy import create_engine, MetaData, select, text, func
from sqlalchemy import Table, Column, Integer, String, ForeignKey
from pkgdb.lib.db import View, initial_data, Grant_RW
from pkgdb.lib.test import create_stuff_table, create_more_stuff_table, slow, bound_metadata

from turbogears import config

class TestLibDB(TestCase):

    def setUp(self):
        self.matadata = None

    def tearDown(self):
        if self.metadata:
            self.metadata.drop_all()

    def create_stuff_view(self, metadata, stuff, more_stuff):
        return View("stuff_view", metadata,
                        select([
                            stuff.c.id.label('id'), 
                            stuff.c.data.label('data'), 
                            more_stuff.c.data.label('moredata')]).\
                        select_from(stuff.join(more_stuff)).\
                        where(stuff.c.data.like(text("'orange%'"))
                        )
                    )


    def create_complex_stuff_view(self, metadata, stuff, more_stuff):
        return View("complex_stuff_view", metadata,
                        select([
                            more_stuff.c.data.label('data'), 
                            func.count().label('count')]).\
                        select_from(stuff.join(more_stuff)).\
                        group_by(more_stuff.c.data)
                    )


    def test_View(self):
        self.metadata = bound_metadata()

        stuff = create_stuff_table(self.metadata)
        more_stuff = create_more_stuff_table(self.metadata)
        stuff_view = self.create_stuff_view(self.metadata, stuff, more_stuff)
        
        # the ORM would appreciate this
        assert_equals(stuff_view.primary_key, [stuff_view.c.id])

        cplx_stuff_view = self.create_complex_stuff_view(self.metadata, stuff, more_stuff)

        initial_data(stuff,
            ('id', 'data'),
            (1, 'apples'),
            (2, 'pears'),
            (3, 'oranges'),
            (4, 'orange julius'),
            (5, 'apple jacks'))

        initial_data(more_stuff,
            ('stuff_id', 'data'),
            (3, 'foobar'),
            (4, 'foobar'))

        self.metadata.create_all()
        
        data = [r[0:2] for r in self.metadata.bind.execute(select([stuff_view.c.data, stuff_view.c.moredata])).fetchall()]
        # view works as expected
        assert_equals(set(data), set([('oranges', 'foobar'), ('orange julius', 'foobar')]))

        result = self.metadata.bind.execute(select([cplx_stuff_view.c.data, cplx_stuff_view.c.count])).fetchall()[0]
        # even aggregate functions are supported in the views
        assert_equals(result, ('foobar', 2))
 

    def test_initial_data(self):
        self.metadata = bound_metadata(echo=True)
        
        stuff = create_stuff_table(self.metadata)
        initial_data(stuff, 
            ('id', 'data'),
            (1, lambda: 'test'),
            (2, 'another_test'))

        self.metadata.create_all()

        # check if the table was intialized with the data
        results = self.metadata.bind.execute(select([stuff.c.data]).order_by(stuff.c.id)).fetchall()
        assert_equals(results[0][0], 'test')
        assert_equals(results[1][0], 'another_test')


    def test_grant_rw(self):
        self.metadata = bound_metadata(echo=True)

        common_user = config.get('database.common_user')
        readonly_user = config.get('database.readonly_user')
        
        stuff = create_stuff_table(self.metadata)
        Grant_RW(stuff)

        self.metadata.create_all()

        conn = self.metadata.bind.connect()
        res = conn.execute(
            "SELECT relname,relacl FROM pg_catalog.pg_class WHERE relname='stuff'")

        results = res.fetchall()

        print results

        assert_true('%s=arwd/' % common_user in results[0][1])
        assert_true('%s=r/' % readonly_user in results[0][1])

        res = conn.execute(
            "SELECT relname,relacl FROM pg_catalog.pg_class WHERE relname='stuff_id_seq'")

        results = res.fetchall()

        print results

        assert_true('%s=rw/' % common_user in results[0][1])
        assert_true('%s=r/' % readonly_user in results[0][1])


