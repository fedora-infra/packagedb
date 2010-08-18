dblist:
	tg-admin -c pkgdb.cfg sql list

test:
	nosetests -w . pkgdb/tests/unit -a \!slow

testall:
	nosetests -w . pkgdb/tests/

testfunc:
	nosetests -w . pkgdb/tests/functional -a \!slow

testfuncd:
	nosetests -v -w . pkgdb/tests/functional -a \!slow --pdb

testv:
	nosetests -v -s -w . pkgdb/tests/unit

testd:
	nosetests -v -w . pkgdb/tests/unit --pdb

shell:	
	tg-admin --config=test.cfg shell

build:
	paver build

resetdb:
	sudo -u postgres dropdb test
	sudo -u postgres createdb -O test test
