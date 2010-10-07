dblist:
	tg-admin -c pkgdb.cfg sql list

test:
	nosetests -w . tests/unit -a \!slow

testcurr:
	nosetests -v -w . tests/ -a current

testall:
	nosetests -w . tests/

testfunc:
	nosetests -w . tests/functional -a \!slow

testfuncd:
	nosetests -v -w . tests/functional -a \!slow --pdb

testv:
	nosetests -v -s -w . tests/unit

testd:
	nosetests -v -w . tests/unit --pdb

shell:	
	tg-admin --config=test.cfg shell

build:
	paver build

resetdb:
	sudo -u postgres dropdb test
	sudo -u postgres createdb -O test test

pylint-model:
	pylint -e -i y -f colorized pkgdb/model/

coverage:
	nosetests -w . tests/unit -v  --with-coverage --cover-erase --cover-inclusive --cover-package=pkgdb --with-xunit

coveragehtml:
	nosetests -w . tests/unit -v  --with-coverage --cover-erase --cover-inclusive --cover-package=pkgdb --cover-html

