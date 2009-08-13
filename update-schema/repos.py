'''Populate database with repos

This script is used to create a postgresql INSERT statement that will populate
the database with all the known fedora, epel and olpc repos.

Right now it is missing: SRPMS, OLPC releases and Fedora 1 and 2 releases.
'''

groups = [
    [['F', 'Fedora'],
     [[11, 21], [10, 19], [9, 15]],
     ['i386', 'x86_64', 'ppc', 'ppc64'],
     [['', '', 'releases/%(ver)s/Everything/%(arch)s/os/'],
      ['-d', ' - Debug', 'releases/%(ver)s/Everything/%(arch)s/debug/'],
      ['-u', ' - Updates', 'updates/%(ver)s/%(arch)s/'],
      ['-ud', ' - Updates - Debug', 'updates/%(ver)s/%(arch)s/debug/'],
      ['-tu', ' - Test Updates', 'updates/testing/%(ver)s/%(arch)s/'],
      ['-tud',' - Test Updates Debug','updates/testing/%(ver)s/%(arch)s/debug/']
      ],
     'http://download.fedoraproject.org/pub/fedora/linux/'
     ],
    [['F', 'Fedora'],
     [[9, 15]],
     ['ia64', 'sparc', 'sparc64'],
     [['', '', 'releases/%(ver)s/Everything/%(arch)s/os/'],
      ['-d', ' - Debug', 'releases/%(ver)s/Everything/%(arch)s/debug/'],
      ['-u', ' - Updates', 'updates/%(ver)s/%(arch)s/'],
      ['-ud', ' - Updates - Debug', 'updates/%(ver)s/%(arch)s/debug/'],
      ['-tu', ' - Test Updates', 'updates/testing/%(ver)s/%(arch)s/'],
      ['-tud',' - Test Updates Debug','updates/testing/%(ver)s/%(arch)s/debug/']
      ],
     'http://secondary.fedoraproject.org/pub/fedora-secondary/'
     ],
    [['F', 'Fedora'],
     [[8, 14], [7, 3]],
     ['i386', 'x86_64', 'ppc', 'ppc64'],
     [['', '', 'releases/%(ver)s/Everything/%(arch)s/os/'],
      ['-d', ' - Debug', 'releases/%(ver)s/Everything/%(arch)s/debug/'],
      ['-u', ' - Updates', 'updates/%(ver)s/%(arch)s/'],
      ['-ud', ' - Updates - Debug', 'updates/%(ver)s/%(arch)s/debug/'],
      ['-tu', ' - Test Updates', 'updates/testing/%(ver)s/%(arch)s/'],
      ['-tud',' - Test Updates Debug','updates/testing/%(ver)s/%(arch)s/debug/']
      ],
     'http://archive.fedoraproject.org/pub/archive/fedora/linux/'
     ],
    [['EL', 'Extra Packages for Enterprise Linux'],
     [[4, 12], [5, 13]],
     ['i386', 'x86_64', 'ppc'],
     [['', '', '%(ver)s/%(arch)s/'],
      ['-d', ' - Debug', '%(ver)s/%(arch)s/debug/'],
      ['-t', ' - Testing', 'testing/%(ver)s/%(arch)s/'],
      ['-td', ' - Testing - Debug', 'testing/%(ver)s/%(arch)s/debug/']
      ],
     'http://download.fedoraproject.org/pub/epel/'
     ],
    [['FC', 'Fedora'],
    [[6, 4], [5, 1], [4, 2], [3, 6]],
    ['i386', 'x86_64'],
    [['', ' Core', 'core/%(ver)s/%(arch)s/os/'],
     ['-d', ' Core - Debug', 'core/%(ver)s/%(arch)s/debug'],
     ['-e', ' Extras', 'extras/%(ver)s/%(arch)s/'],
     ['-ed', ' Extras - Debug', 'extras/%(ver)s/%(arch)s/debug'],
     ['-u', ' Core - Updates', 'core/updates/%(ver)s/%(arch)s/'],
     ['-ud', ' Core - Updates - Debug', 'core/updates/%(ver)s/%(arch)s/debug'],
     ['-ut', ' Core - Updates - Testing',
      'core/updates/testing/%(ver)s/%(arch)s/'],
     ],
     'http://archives.fedoraproject.org/pub/archive/fedora/linux/'
     ],
    ]
# this works for newer postgresqls, but not the one on publictest3 (8.1.11)
#
# s = 'INSERT INTO REPOS (shortname, name, collectionid, url, mirror) VALUES \n'
# for group in groups:
#     [[sname, lname], vers, arches, urlschemes, mirror] = group
#     for ver in vers:
#         for arch in arches:
#             for url in urlschemes:
#                 s += "('%(sname)s-%(ver)s-%(arch)s%(sdesc)s',"\
#                      "'%(lname)s %(ver)s - %(arch)s%(ldesc)s', "\
#                      "%(coll)s, \n"\
#                      "'%(urlpart)s', "\
#                      "'%(mirror)s'),\n\n" % {
#                         'lname':lname, 'sname':sname,
#                         'ver':ver[0], 'coll': ver[1],
#                         'arch':arch, 'sdesc':url[0], 'ldesc':url[1],
#                         'urlpart': url[2] % {
#                             'ver':ver[0], 'arch':arch}, 'mirror':mirror}
# # replace the two newlines and comma
# s = s[:-3] + ';'
# print s

# this is suboptimal. It generates a separate insert statement for every row.
# Please use the above version where possible.
s = ''
for group in groups:
    [[sname, lname], vers, arches, urlschemes, mirror] = group
    for ver in vers:
        for arch in arches:
            for url in urlschemes:
                s += "INSERT INTO REPOS (shortname, name, collectionid,"\
                     "url, mirror) VALUES \n"\
                     "('%(sname)s-%(ver)s-%(arch)s%(sdesc)s',"\
                     "'%(lname)s %(ver)s - %(arch)s%(ldesc)s', "\
                     "%(coll)s, \n"\
                     "'%(urlpart)s', "\
                     "'%(mirror)s');\n\n" % {
                        'lname':lname, 'sname':sname,
                        'ver':ver[0], 'coll': ver[1],
                        'arch':arch, 'sdesc':url[0], 'ldesc':url[1],
                        'urlpart': url[2] % {
                            'ver':ver[0], 'arch':arch}, 'mirror':mirror}
print s
