from sqlalchemy import *
from migrate import *
from pkgdb.lib.db import Grant_RW

meta = MetaData(migrate_engine)

# just to be referenced
CollectionTable = Table('collection', meta,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
)

CollectionSetTable = Table('collectionset', meta,
    Column('overlay', Integer(),  primary_key=True, autoincrement=False, nullable=False),
    Column('base', Integer(),  primary_key=True, autoincrement=False, nullable=False),
    Column('priority', Integer(), PassiveDefault(text('0'))),
    ForeignKeyConstraint(['overlay'],['collection.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['base'],['collection.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
)
Grant_RW(CollectionSetTable)

def upgrade():
    CollectionSetTable.drop()

def downgrade():
    CollectionSetTable.create()
