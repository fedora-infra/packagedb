# Build Tags
# repo | build | score | tag 
% for repo in sorted(buildtags.keys()):
    % for build in sorted(buildtags[repo].keys()):
        % for tag in sorted(buildtags[repo][build].keys()):
${repo} | ${build} | ${buildtags[repo][build][tag]} | ${tag}
        % endfor
    % endfor 
% endfor

