Name:           fedora-packagedb
Version:        0.6.0
Release:        1%{?dist}
Summary:        Keep track of ownership of packages in Fedora

Group:          Development/Languages
License:        GPLv2+
URL:            http://fedorahosted.org/packagedb
Source0:        http://fedorahosted.org/releases/p/a/packagedb/%{name}-%{version}.tar.bz2
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
Requires: python-TurboMail
%if 0%{?rhel} <= 5
Requires: python-sqlalchemy0.5
%else
Requires: python-sqlalchemy >= 0.5
%endif
Requires: python-psycopg2
Requires: python-genshi
Requires: python-mako
Requires: python-fedora >= 0.3.18
Requires: python-bugzilla >= 0.5
Requires: python-argparse
Requires: koji
Requires: mod_wsgi
Requires: python-cpio
Requires: python-memcached
Requires: fedmsg

BuildRequires: python2-devel
BuildRequires: python-genshi
BuildRequires: TurboGears
%if 0%{?rhel} || 0%{?fedora} >= 13
BuildRequires: python-setuptools
%else
BuildRequires: python-setuptools-devel
%endif
BuildRequires: python-paver

%description
The Fedora Packagedb tracks who owns a package in the Fedora Collection.

%package clients
Summary:        Keep track of ownership of packages in Fedora
Group:          Development/Tools
License:        GPLv2+
Requires: python-fedora >= 0.3.18
Requires: python-configobj

%description clients
Command line script to communicate with the Fedora PackageDB

%prep
%setup -q


%build
%if 0%{?fedora} >= 14 || 0%{?rhel} >= 5
export PYTHONPATH=%{python_sitelib}/CherryPy-2.3.0-py2.6.egg:%{python_sitelib}/TurboJson-1.3.2-py2.6.egg
%endif
paver build --install-conf=%{_sysconfdir} --install-data=%{_datadir} \
    --install-sbin=%{_sbindir}


%install
rm -rf %{buildroot}
# We don't currently have a paver target for this to work.
%{__python} setup.py install --skip-build --install-conf=%{_sysconfdir} \
    --install-data=%{_datadir} --root %{buildroot}
install -d %{buildroot}%{_sbindir}
mv %{buildroot}%{_bindir}/start-pkgdb %{buildroot}%{_sbindir}/
mv %{buildroot}%{_bindir}/pkgdb.wsgi %{buildroot}%{_sbindir}/

install -d %{buildroot}%{_sysconfdir}/httpd/conf.d
install -m 0644 httpd-pkgdb.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/pkgdb.conf

install -m 0755 -d %{buildroot}%{_datadir}/fedora-packagedb/update-schema
cp -pr update-schema/*.py %{buildroot}%{_datadir}/fedora-packagedb/update-schema
cp -pr update-schema/*.sql %{buildroot}%{_datadir}/fedora-packagedb/update-schema

%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc README COPYING AUTHORS NEWS ChangeLog
%{_datadir}/fedora-packagedb/
%{_sbindir}/start-pkgdb
%{_sbindir}/pkgdb.wsgi
%{_bindir}/pkgdb-sync-bugzilla
%{_bindir}/pkgdb-sync-yum
%config(noreplace) %{_sysconfdir}/pkgdb.cfg
%config(noreplace) %{_sysconfdir}/fedmsg.d/pkgdb.py
%config(noreplace) %{_sysconfdir}/pkgdb-sync-bugzilla.cfg
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pkgdb.conf

%files clients
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/pkgdb-client.cfg
%{_bindir}/pkgdb-client

%changelog
* - 0.6.0-1
- Update to 0.6.0 which removes the application part

* Tue Dec 18 2012 Toshio Kuratomi <toshio@fedoraproject.org> - 0.5.7-1
- Add a fedmsg hook  (from threebean)

* Wed Oct 17 2012 Toshio Kuratomi <toshio@fedoraproject.org> - 0.5.6-1
- Add plain text output for critpath list
- Add ability to filter notify list by colleciton

* Sun Oct  7 2012 Toshio Kuratomi <toshio@fedoraproject.org> - 0.5.5-1
- 0.5.5 bugfix release

* Sun Sep 4 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 0.5.4
- 0.5.4 release -- don't show EOL releases

* Sat Sep 4 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 0.5.3.1-1
- 0.5.3.1 release -- fix a template.

* Fri Sep 3 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 0.5.3-1
- 0.5.3 release.
- Bug fixes

* Sat Mar 20 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 0.5.2-1
- 0.5.2 release.
- Bug fixes

* Mon Mar 15 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 0.5.1-1
- 0.5.1 release.
- Fix some cosmetic bugs and one broken link

* Fri Mar 12 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 0.5.0-1
- 0.5.x release.

* Wed Mar 10 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 0.4.92-1
- Third beta

* Sun Mar 7 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 0.4.91-1
- Second beta

* Sat Mar 6 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 0.4.90-1
- 0.4.90 is an 0.5 beta

* Wed Nov 11 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.4.1-1
- 0.4.1 bugfix release.

* Sun Jun 14 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.4.0-1
- 0.4.0 final.

* Sun Jun 14 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.10.99-1
- Release Candidate.  Mainly bug fixes.

* Sat Jun 13 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.10.93-1
- New test release.  Mainly bug fixes.

* Sat Jun 6 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.10.92-1
- New test release.  Mainly bug fixes.

* Thu May 14 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.10.91-1
- New test release.  Mainly bug fixes.

* Tue Apr 21 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.10.90-1
- Update to use mod_wsgi
- Shift to use username
- Include schema update scripts

* Wed Jan 22 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.10.1-1
- bugzilla checking fix.

* Wed Jan 21 2009 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.10-1
- Update for new provenpackager policy and bugzilla account checking.

* Wed Nov 5  2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.9.2-1
- And a few more upstream fixes related to pkgdb-client.

* Wed Nov 5  2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.9.1-1
- New upstream that fixes emailing of mass branch status.

* Tue Nov 4  2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.9-1
- New upstream with new branching code, restructured pkgdb-client,
  uberpackager renamed to provenpackager, and major speedups.

* Thu Oct 9  2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.8-2
- Install the client

* Thu Oct 9  2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.8-1
- New upstream with bugfixes and packager => uberpackager switch.

* Sat Aug 9  2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.7-1
- New upstream release. Many UI improvements and bugfixes.

* Wed Jul 16 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.6-1
- New upstream release. notify list, some search optimization, improved
  filter box and pkglist look and feel.

* Sun Jun 22 2008 Nigel Jones <dev@nigelj.com> - 0.3.5-1
- New upstream release - (Search & uberpackager)

* Tue Jun 10 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.4.1-1
- Upstream bugfix to acl code.

* Thu Jun 5 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.4-1
- New upstream release.

* Fri Apr 11 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.3.1-1
- Minor fixes.

* Fri Apr 11 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.3-1
- SQLAlchemy-0.4 release.

* Wed Mar 14 2008 Ricky Zhou <ricky@fedoraproject.org> - 0.3.2.8-1
- FAS2 compatibility release.

* Wed Mar 12 2008 Ricky Zhou <ricky@fedoraproject.org> - 0.3.2.7-1
- Another FAS2 bugfix.

* Wed Mar 12 2008 Ricky Zhou <ricky@fedoraproject.org> - 0.3.2.6-1
- Few more bugfixes.

* Wed Mar 12 2008 Ricky Zhou <ricky@fedoraproject.org> - 0.3.2.5-1
- More updates for FAS2

* Wed Mar 12 2008 Ricky Zhou <ricky@fedoraproject.org> - 0.3.2.4-1
- Update for FAS2

* Wed Jan 23 2008 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.2.3-1
- Bugfix release.

* Sat Dec 15 2007 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.2.2-1
- Bugfix release.

* Wed Nov 14 2007 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.2.1-1
- Bugfix release.

* Sun Oct 28 2007 Toshio Kuratomi <toshio@fedoraproject.org> - 0.3.2-1
- New upstream release.

* Tue Oct 9 2007 Toshio Kuratomi <a.badger@gmail.com> - 0.3.1.2-1
- New upstream release.

* Tue Oct 2 2007 Toshio Kuratomi <a.badger@gmail.com> - 0.3.1.1-1
- Add Requires.

* Tue Sep 25 2007 Toshio Kuratomi <a.badger@gmail.com> - 0.3.1-1
- Initial Build.
