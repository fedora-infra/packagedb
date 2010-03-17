# VCS ACLs
# avail|@groups,users|rpms/Package/branch
% for pkg in sorted(packageAcls.keys()):
   % for branch in sorted(packageAcls[pkg].keys()):
<%
import itertools

acl_holders= ','.join(itertools.chain(
  ('@%s' % g for g in packageAcls[pkg][branch]['commit'].groups),
  packageAcls[pkg][branch]['commit'].people))
%>
avail | ${acl_holders} | rpms/${pkg}/${branch}\
  %endfor
%endfor

