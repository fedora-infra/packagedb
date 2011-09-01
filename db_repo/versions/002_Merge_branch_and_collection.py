from sqlalchemy import *
from pkgdb.lib.db import Grant_RW
from migrate import *
from migrate.changeset import *
import re
import migrate.changeset

# have we sqlalchemy-migrate > 0.5?
if hasattr(migrate.changeset.constraint, 'UniqueConstraint'):
    migrate_engine=None

metadata = MetaData(migrate_engine)


CollectionTable = Table('collection', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
    Column('branchname', Text(), unique=True, nullable=True), # later make not null
    Column('disttag', Text(),  nullable=True) # later make not null
)


BranchTable = Table('branch', metadata,
    Column('collectionid', Integer(), autoincrement=False, nullable=False),
    Column('branchname', String(32), unique=True, nullable=False),
    Column('gitbranchname', Text(), nullable=False),
    Column('disttag', String(32),  nullable=False),
    Column('parentid', Integer()),
    PrimaryKeyConstraint('collectionid', name='branch_pkey'),
    ForeignKeyConstraint(['collectionid'],['collection.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['parentid'],['collection.id'],
        onupdate="CASCADE", ondelete="SET NULL"),
)
DDL('ALTER TABLE branch CLUSTER ON branch_pkey', on='postgres')\
    .execute_at('after-create', BranchTable)
Grant_RW(BranchTable)   

def git_to_cvs(gitbranchname):
    if gitbranchname == 'master':
        return 'devel'
    else:
        return re.sub(r'(\d+)$', r'-\1', gitbranchname.upper())


def upgrade(migrate_engine=migrate_engine):
    metadata.bind = migrate_engine

    # add branch columns to collection
    CollectionTable.create_column('disttag')
    CollectionTable.create_column('branchname')

    # collect branch data 
    s = BranchTable.select()
    u = CollectionTable.update()
    rs = migrate_engine.execute(s)
    for row in rs:
        # store branch data
        branch_name = row[BranchTable.c.branchname].lower().replace('-', '')
        if branch_name == 'devel':
            branch_name = 'master'
        migrate_engine.execute(u\
            .where(CollectionTable.c.id==row[BranchTable.c.collectionid])\
            .values(disttag=row[BranchTable.c.disttag], branchname=branch_name))

    # update constraints
    CollectionTable.c.disttag.alter(nullable=False)
    CollectionTable.c.branchname.alter(nullable=False)

    # drop branch table
    BranchTable.drop()


def downgrade(migrate_engine=migrate_engine):
    metadata.bind = migrate_engine
    
    # create branch table 
    BranchTable.create()

    # collect branch data 
    s = CollectionTable.select()
    i = BranchTable.insert()
    rs = migrate_engine.execute(s)

    for row in rs:
        # store branch data
        migrate_engine.execute(i\
            .values(
                collectionid=row[CollectionTable.c.id],
                disttag=row[CollectionTable.c.disttag], 
                branchname=git_to_cvs(row[CollectionTable.c.branchname]),
                gitbranchname=row[CollectionTable.c.branchname]))

    # drop redundant columns
    CollectionTable.drop_column('disttag')
    CollectionTable.drop_column('branchname')

