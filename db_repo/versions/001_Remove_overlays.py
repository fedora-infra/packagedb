from sqlalchemy import *
from migrate import *
from pkgdb.lib.db import Grant_RW
import migrate.changeset

# is sqlalchemy-migrate > 0.5
if hasattr(migrate.changeset.constraint, 'UniqueConstraint'):
    migrate_engine=None

metadata = MetaData(migrate_engine)


# just to be referenced
CollectionTable = Table('collection', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
)

CollectionSetTable = Table('collectionset', metadata,
    Column('overlay', Integer(),  primary_key=True, autoincrement=False, nullable=False),
    Column('base', Integer(),  primary_key=True, autoincrement=False, nullable=False),
    Column('priority', Integer(), PassiveDefault(text('0'))),
    ForeignKeyConstraint(['overlay'],['collection.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['base'],['collection.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
)
Grant_RW(CollectionSetTable)

def upgrade(migrate_engine=migrate_engine):
    metadata.bind = migrate_engine
    CollectionSetTable.drop()

def downgrade(migrate_engine=migrate_engine):
    metadata.bind = migrate_engine
    CollectionSetTable.create()
