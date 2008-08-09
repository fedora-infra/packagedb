%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?pyver: %define pyver %(%{__python} -c "import sys ; print sys.version[:3]")}

Name:           fedora-packagedb
Version:        0.3.7
Release:        1%{?dist}
Summary:        Keep track of ownership of packages in Fedora

Group:          Development/Languages
License:        GPLv2
URL:            http://fedorahosted.org/packagedb
Source0:        http://toshio.fedorapeople.org/fedora/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
Requires: python-TurboMail
Requires: python-sqlalchemy >= 0.4
Requires: python-psycopg2
Requires: python-genshi
Requires: python-fedora >= 0.2.99.7
Requires: python-bugzilla

BuildRequires: python-devel
BuildRequires: python-genshi
BuildRequires: TurboGears
BuildRequires:  python-setuptools-devel

%description
The Fedora Packagedb tracks who owns a package in the Fedora Collection.

%prep
%setup -q


%build
%{__python} setup.py build --install-conf=%{_sysconfdir} \
    --install-data=%{_datadir}


%install
rm -rf %{buildroot}
%{__python} setup.py install --skip-build --install-conf=%{_sysconfdir} \
    --install-data=%{_datadir} --root %{buildroot}
install -d %{buildroot}%{_sbindir}
mv %{buildroot}%{_bindir}/start-pkgdb %{buildroot}%{_sbindir}/

mkdir -p -m 0755 %{buildroot}/%{_localstatedir}/log/pkgdb

%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc README COPYING AUTHORS NEWS ChangeLog
%{_datadir}/fedora-packagedb/
%{_sbindir}/start-pkgdb
%{_bindir}/*
%config(noreplace) %{_sysconfdir}/pkgdb.cfg
%attr(-,apache,root) %{_localstatedir}/log/pkgdb

%changelog
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
