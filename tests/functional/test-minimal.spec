Name:           test-minimal
Version:        1.0
Release:        1
Summary:        Summary

Group:          Development/Testing
License:        GPL
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch

%description
Description

%prep

%build

%install
rm -rf %{buildroot}

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)

%changelog
* Thu Sep 02 2010 Martin Bacovsky <mbacovsk@redhat.com> - 1.0-1
- Initial package
