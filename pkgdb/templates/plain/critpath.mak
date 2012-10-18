% for collection in sorted(pkgs):
== ${collection} ==
  % for pk in sorted(pkgs[collection]:
* ${pkg}
  % endfor
% endfor
