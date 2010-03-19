% for pkg in sorted(packages.keys()):
${pkg}|${','.join(sorted(packages[pkg]))}
% endfor
