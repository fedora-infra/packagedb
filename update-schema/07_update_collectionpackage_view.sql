CREATE OR REPLACE VIEW collectionpackage AS
SELECT c.id, c.name, c.version, c.statuscode, count(pl.id) AS numpkgs
FROM collection AS c
     LEFT OUTER JOIN packagelisting AS pl
ON pl.collectionid = c.id
WHERE pl.statuscode = 3 OR
      pl.statuscode is null
GROUP BY c.name, c.version, c.id, c.statuscode
ORDER BY c.name, c.version;

COMMIT;
