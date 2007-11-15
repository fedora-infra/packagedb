%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?pyver: %define pyver %(%{__python} -c "import sys ; print sys.version[:3]")}

Name:           fedora-packagedb
Version:        0.3.2.1
Release:        1%{?dist}
Summary:        Keep track of ownership of packages in Fedora

Group:          Development/Languages
License:        GPLv2
URL:            http://hosted.fedoraproject.org/projects/packagedb
Source0:        http://toshio.fedorapeople.org/fedora/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
Requires: python-TurboMail
Requires: python-sqlalchemy >= 0.3.10, python-sqlalchemy < 0.4
Requires: python-psycopg2
Requires: python-genshi
Requires: python-fedora-infrastructure
Requires: python-bugzilla

BuildRequires:  python-devel
BuildRequires: TurboGears
%if 0%{?fedora} >= 8
BuildRequires:  python-setuptools-devel
%else
BuildRequires: python-setuptools
%endif

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
mv %{buildroot}%{_bindir}/* %{buildroot}%{_sbindir}/
 
%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc README COPYING AUTHORS ChangeLog
%{_datadir}/fedora-packagedb/
%{_sbindir}/start-pkgdb
%config(noreplace) %{_sysconfdir}/pkgdb.cfg

%changelog
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
