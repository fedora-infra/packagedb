from unittest import TestCase
from nose.tools import *

from sqlalchemy import create_engine, MetaData, select, text, func
from sqlalchemy import Table, Column, Integer, String, ForeignKey
from pkgdb.lib.db import View, initial_data
from pkgdb.lib.test import create_stuff_table, create_more_stuff_table, slow, bound_metadata

class TestLibDB(TestCase):


    def create_stuff_view(self, metadata, stuff, more_stuff):
        return View("stuff_view", metadata,
                        select([
                            stuff.c.id.label('id'), 
                            stuff.c.data.label('data'), 
                            more_stuff.c.data.label('moredata')]).\
                        select_from(stuff.join(more_stuff)).\
                        where(stuff.c.data.like(text("'orange%%'"))
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
        metadata = bound_metadata()

        stuff = create_stuff_table(metadata)
        more_stuff = create_more_stuff_table(metadata)
        stuff_view = self.create_stuff_view(metadata, stuff, more_stuff)
        
        # the ORM would appreciate this
        assert_equals(stuff_view.primary_key, [stuff_view.c.id])

        cplx_stuff_view = self.create_complex_stuff_view(metadata, stuff, more_stuff)

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

        metadata.create_all()
        
        data = [r[0:2] for r in metadata.bind.execute(select([stuff_view.c.data, stuff_view.c.moredata])).fetchall()]
        # view works as expected
        assert_equals(set(data), set([('oranges', 'foobar'), ('orange julius', 'foobar')]))

        result = metadata.bind.execute(select([cplx_stuff_view.c.data, cplx_stuff_view.c.count])).fetchall()[0]
        # even aggregate functions are supported in the views
        assert_equals(result, ('foobar', 2))
 
        metadata.drop_all()


    def test_initial_data(self):
        metadata = bound_metadata()
        
        stuff = create_stuff_table(metadata)
        initial_data(stuff, 
            ('id', 'data'),
            (1, lambda: 'test'),
            (2, 'another_test'))

        metadata.create_all()

        # check if the table was intialized with the data
        results = metadata.bind.execute(select([stuff.c.data]).order_by(stuff.c.id)).fetchall()
        assert_equals(results[0][0], 'test')
        assert_equals(results[1][0], 'another_test')

        metadata.drop_all()



