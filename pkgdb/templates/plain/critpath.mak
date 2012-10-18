% for collection in sorted(pkgs):
== ${collection} ==
  % for pkg in sorted(pkgs[collection]):
* ${pkg}
  % endfor

% endfor
