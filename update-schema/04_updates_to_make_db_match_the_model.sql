ALTER TABLE appsmimetypes ADD PRIMARY KEY(applicationid, mimetypeid);
ALTER TABLE appsmimetypes DROP CONSTRAINT appsmimetypes_applicationid_fkey;
ALTER TABLE appsmimetypes ADD CONSTRAINT appsmimetypes_applicationid_fkey FOREIGN KEY (applicationid) REFERENCES applications(id) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE appsmimetypes DROP CONSTRAINT appsmimetypes_mimetypeid_fkey;
ALTER TABLE appsmimetypes ADD CONSTRAINT appsmimetypes_mimetypeid_fkey FOREIGN KEY (mimetypeid) REFERENCES mimetypes(id) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE binarypackagetags ADD PRIMARY KEY(binarypackagename, tagid);
ALTER TABLE binarypackagetags DROP CONSTRAINT binarypackagetags_binarypackagename_fkey;
ALTER TABLE binarypackagetags ADD CONSTRAINT binarypackagetags_binarypackagename_fkey FOREIGN KEY (binarypackagename) REFERENCES binarypackages(name) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE binarypackagetags DROP CONSTRAINT binarypackagetags_tagid_fkey;
ALTER TABLE binarypackagetags ADD CONSTRAINT binarypackagetags_tagid_fkey FOREIGN KEY (tagid) REFERENCES tags(id) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE tags ADD CONSTRAINT tags_name_key UNIQUE (name);
ALTER TABLE rpmprovides ALTER COLUMN packagebuildid SET NOT NULL;

ALTER TABLE packagebuildrepos ADD PRIMARY KEY(repoid, packagebuildid);
ALTER TABLE packagebuildrepos DROP CONSTRAINT packagebuildrepos_packagebuildid_fkey;
ALTER TABLE packagebuildrepos ADD CONSTRAINT packagebuildrepos_packagebuildid_fkey FOREIGN KEY (packagebuildid) REFERENCES packagebuild(id) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE packagebuildrepos DROP CONSTRAINT packagebuildrepos_repoid_fkey;
ALTER TABLE packagebuildrepos ADD CONSTRAINT packagebuildrepos_repoid_fkey FOREIGN KEY (repoid) REFERENCES repos(id) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE packagebuildapplications ADD PRIMARY KEY(applicationid, packagebuildid);
ALTER TABLE packagebuildapplications DROP CONSTRAINT packagebuildapplications_applicationid_fkey;
ALTER TABLE packagebuildapplications ADD CONSTRAINT packagebuildapplications_applicationid_fkey FOREIGN KEY (applicationid) REFERENCES applications(id) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE packagebuildapplications DROP CONSTRAINT packagebuildapplications_packagebuildid_fkey;
ALTER TABLE packagebuildapplications ADD CONSTRAINT packagebuildapplications_packagebuildid_fkey FOREIGN KEY (packagebuildid) REFERENCES packagebuild(id) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE applicationstags ADD PRIMARY KEY(applicationid, tagid);
ALTER TABLE applicationstags DROP CONSTRAINT applicationstags_applicationid_fkey;
ALTER TABLE applicationstags ADD CONSTRAINT applicationstags_applicationid_fkey FOREIGN KEY (applicationid) REFERENCES applications(id) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE applicationstags DROP CONSTRAINT applicationstags_tagid_fkey;
ALTER TABLE applicationstags ADD CONSTRAINT applicationstags_tagid_fkey FOREIGN KEY (tagid) REFERENCES tags(id) ON UPDATE CASCADE ON DELETE CASCADE;
