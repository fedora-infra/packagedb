from unittest import TestCase
from nose.tools import *

from sqlalchemy import create_engine, MetaData, select, text
from sqlalchemy import Table, Column, Integer, String, ForeignKey
from pkgdb.lib.db import View, add_dependency, reset_dependencies

class TestDB(TestCase):

    def create_stuff(self, metadata):
        return Table('stuff', metadata, 
            Column('id', Integer, primary_key=True),
            Column('data', String(50)),
        )


    def create_more_stuff(self, metadata):
        return Table('more_stuff', metadata, 
            Column('id', Integer, primary_key=True),
            Column('stuff_id', Integer, ForeignKey('stuff.id')),
            Column('data', String(50)),
        )

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

    def test_reset_dependencies(self):
        import pkgdb.lib.db as db
        import sqlalchemy.sql.util as sautil

        metadata = 'metadata'
        # set deps to something
        db._dependencies = {}

        assert_not_equals(sautil.sort_tables, db._sort_tables) 

        add_dependency(metadata, 'a', 'b')

        assert_equals(sautil.sort_tables, db._sort_tables) 

        reset_dependencies(metadata)

        # check
        assert_false(str(metadata) in db._dependencies)
        assert_not_equals(sautil.sort_tables, db._sort_tables) 



    def test_add_dependency(self):
        import pkgdb.lib.db as db
        import sqlalchemy.sql.util as sautil

        engine = create_engine('sqlite:///:memory:', echo=True)
        metadata = MetaData(engine)
        reset_dependencies(metadata)

        add_dependency(metadata, 'A', 'B')

        assert_equals(db._dependencies[str(metadata)], [('B','A')])

        reset_dependencies(metadata)
        assert_not_equals(sautil.sort_tables, db._sort_tables)


    def test_dependencies(self):
        import pkgdb.lib.db as db
        import sqlalchemy.sql.util as sautil
        engine = create_engine('sqlite:///:memory:', echo=True)
        #engine = create_engine('postgres://test:test@127.0.0.1/test', echo=True)
        metadata = MetaData(engine)

        more_stuff = self.create_more_stuff(metadata)
        stuff = self.create_stuff(metadata)
        stuff_view = self.create_stuff_view(metadata, stuff, more_stuff)

        add_dependency(metadata, stuff_view, stuff)
        add_dependency(metadata, stuff_view, more_stuff)

        assert_equals([stuff.name, more_stuff.name, stuff_view.name], 
            [t.name for t in metadata.sorted_tables])

        reset_dependencies(metadata)


    def test_View(self):
        engine = create_engine('sqlite:///:memory:', echo=True)
        #engine = create_engine('postgres://test:test@127.0.0.1/test', echo=True)
        metadata = MetaData(engine)

        stuff = self.create_stuff(metadata)
        more_stuff = self.create_more_stuff(metadata)
        stuff_view = self.create_stuff_view(metadata, stuff, more_stuff)
        
        add_dependency(metadata, stuff_view, stuff)
        add_dependency(metadata, stuff_view, more_stuff)

        # the ORM would appreciate this
        assert_equals(stuff_view.primary_key, [stuff_view.c.id])

        metadata.create_all()
        
        stuff.insert().execute(
            {'data':'apples'},
            {'data':'pears'},
            {'data':'oranges'},
            {'data':'orange julius'},
            {'data':'apple jacks'},
        )

        more_stuff.insert().execute(
            {'stuff_id':3, 'data':'foobar'},
            {'stuff_id':4, 'data':'foobar'}
        )
        
        assert set(
                r[0:2] for r in engine.execute(select([stuff_view.c.data, stuff_view.c.moredata])).fetchall()
            ) == set([('oranges', 'foobar'), ('orange julius', 'foobar')])
 
        
        metadata.drop_all()

        reset_dependencies(metadata)
        

