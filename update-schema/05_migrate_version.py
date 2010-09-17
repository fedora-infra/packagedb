import sys
from configobj import ConfigObj
from turbogears.config import config_defaults

defaults = config_defaults()
config = ConfigObj(sys.argv[1], unrepr=True)
config.merge(dict(DEFAULT=defaults))


try:
    repo_path = config['global']['database.repo']
except KeyError:
    print "'database.repo' was not defined in config file."
    sys.exit(1)

sql = """
CREATE TABLE migrate_version (                     
        repository_id VARCHAR(255) NOT NULL,       
        repository_path TEXT,                      
        version INTEGER,                           
        PRIMARY KEY (repository_id)                
);                                                  
GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE migrate_version TO pkgdbadmin;
GRANT SELECT ON migrate_version TO pkgdbreadonly;
INSERT INTO migrate_version (repository_id, repository_path, version) VALUES ('Fedora Package DB', '%s', 0);
"""

print sql % repo_path
