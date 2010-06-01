CREATE TABLE migrate_version (                     
        repository_id VARCHAR(255) NOT NULL,       
        repository_path TEXT,                      
        version INTEGER,                           
        PRIMARY KEY (repository_id)                
);                                                  
GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE migrate_version TO pkgdbadmin;
GRANT SELECT ON migrate_version TO pkgdbreadonly;
INSERT INTO migrate_version (repository_id, repository_path, version) VALUES ('Fedora Package DB', 'db_repo', 0);
