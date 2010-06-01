dblist:
	tg-admin -c pkgdb.cfg sql list

test:
	nosetests -w . pkgdb/tests/ -a \!slow

testall:
	nosetests -w . pkgdb/tests/

testv:
	nosetests -v -s -w . pkgdb/tests/

testd:
	nosetests -v -w . pkgdb/tests/ --pdb

shell:	
	tg-admin --config=test.cfg shell

build:
	paver build
