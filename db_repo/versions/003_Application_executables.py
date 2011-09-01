from sqlalchemy import *
from pkgdb.lib.db import Grant_RW
from migrate import *
from migrate.changeset import *
import migrate.changeset

# is sqlalchemy-migrate > 0.5
if hasattr(migrate.changeset.constraint, 'UniqueConstraint'):
    migrate_engine=None
    from pkgdb.lib.migratelib import UniqueConstraint

metadata = MetaData(migrate_engine)


CollectionTable = Table('collection', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
)

PackageTable = Table('package', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
)

PackageBuildTable = Table('packagebuild', metadata,
    Column('id', Integer(),  primary_key=True, autoincrement=True, nullable=False),
)

ExecutablesTable = Table('executables', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True,
        nullable=False),    
    Column('executable', Text, unique=True, nullable=False),
)
Grant_RW(ExecutablesTable)

ApplicationsTable = Table('applications', metadata, 
    Column('id', Integer, primary_key=True, autoincrement=True,
        nullable=False),    
    Column('command', Text, nullable=True),
    Column('commandargs', Text, nullable=True),
    Column('executableid', Integer, nullable=True),
    ForeignKeyConstraint(['executableid'],['executables.id'], 
        onupdate="CASCADE", ondelete="SET NULL")
)
AppCommandU = UniqueConstraint(ApplicationsTable.c.command, ApplicationsTable.c.commandargs)

AppCollectionsTable = Table('appcollections', metadata,
    Column('applicationid', Integer, primary_key=True, autoincrement=False, nullable=False),
    Column('collectionid', Integer, primary_key=True, autoincrement=False, nullable=False),
    Column('packageid', Integer, primary_key=True, autoincrement=False, nullable=False),
    Column('name', Text, nullable=False),
    ForeignKeyConstraint(['applicationid'], ['applications.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['collectionid'], ['collection.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
    ForeignKeyConstraint(['packageid'], ['package.id'], onupdate="CASCADE",
        ondelete="CASCADE"),
)
Grant_RW(AppCollectionsTable)


PkgBuildExecutablesTable = Table('pkgbuildexecutables', metadata,
    Column('executableid', Integer, primary_key=True, autoincrement=False, nullable=False),
    Column('packagebuildid', Integer, primary_key=True, autoincrement=False, nullable=False),
    Column('path', Text, primary_key=True, nullable=True),
    ForeignKeyConstraint(['executableid'], ['executables.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['packagebuildid'], ['packagebuild.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
)
Grant_RW(PkgBuildExecutablesTable)

PackageBuildApplicationsTable = Table('packagebuildapplications', metadata,
    Column('applicationid', Integer, primary_key=True, autoincrement=False, nullable=False),
    Column('packagebuildid', Integer, primary_key=True, autoincrement=False, nullable=False),
    ForeignKeyConstraint(['applicationid'], ['applications.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
    ForeignKeyConstraint(['packagebuildid'], ['packagebuild.id'],
        onupdate="CASCADE", ondelete="CASCADE"),
)
Grant_RW(PackageBuildApplicationsTable)

def upgrade(migrate_engine=migrate_engine):
    metadata.bind = migrate_engine

    ExecutablesTable.create()
    PkgBuildExecutablesTable.create()
    AppCollectionsTable.create()
    ApplicationsTable.create_column('command')
    ApplicationsTable.create_column('commandargs')
    ApplicationsTable.create_column('executableid')
    AppCommandU.create()

    # inreversible
    PackageBuildApplicationsTable.drop()

def downgrade(migrate_engine=migrate_engine):
    metadata.bind = migrate_engine

    ApplicationsTable.drop_column('command')
    ApplicationsTable.drop_column('commandargs')
    ApplicationsTable.drop_column('executableid')
    PkgBuildExecutablesTable.drop()
    ExecutablesTable.drop()
    AppCollectionsTable.drop()

    PackageBuildApplicationsTable.create()
