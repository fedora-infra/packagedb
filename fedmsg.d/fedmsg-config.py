""" This is an example configuration for fedmsg.

For Fedora Infrastructure, this is kept in::

    puppet/modules/fedmsg/templates/fedmsg.d/

It needs to be globally available so remote consumers know how to find the
pkgdb producer (wsgi process).
"""

import socket
hostname = socket.gethostname()

config = dict(
    endpoints={
        "relay_outbound": ["tcp://127.0.0.1:4001"],
        "pkgdb.%s" % hostname: [
            "tcp://127.0.0.1:3005",
        ],
    },

    relay_inbound="tcp://127.0.0.1:2003",
    environment="dev",
    high_water_mark=0,
    io_threads=1,
    post_init_sleep=0.2,
    irc=[],
    zmq_enabled=True,
    zmq_strict=False,

    sign_messages=False,
    validate_messages=False,
)
