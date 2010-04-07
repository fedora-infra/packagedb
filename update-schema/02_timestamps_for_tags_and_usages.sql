ALTER TABLE packagebuild ADD imported timestamp with time zone not null default NOW();
ALTER TABLE applicationsusages ADD time timestamp with time zone not null default NOW();
ALTER TABLE applicationstags ADD time timestamp with time zone not null default NOW();
    
