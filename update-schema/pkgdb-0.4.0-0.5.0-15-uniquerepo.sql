ALTER TABLE repos ADD CONSTRAINT repos_shortname UNIQUE (shortname);
ALTER TABLE repos ADD CONSTRAINT repos_name UNIQUE (name);
ALTER TABLE repos ADD CONSTRAINT repos_url UNIQUE (url);

