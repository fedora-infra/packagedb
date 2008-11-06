===============
Dojo BaseClient
===============

:Author: Toshio Kuratomi
:Date: 21 Oct, 2008
:For Version: 0.1.x

Dojo BaseClient is a JavaScript port of the python-fedora BaseClient.  It
isn't a 100% compatible implementation, instead aiming to utilize techniques
that will make sense for a Dojo programmer.

.. contents::

-------------
Instantiating
-------------
Creating a new JavaScript :class:`fedora.dojo.BaseClient` is very similar to
creating a python :class:`fedora.client.BaseClient`.  The differences are
largely due to the JavaScript `BaseClient` using the browser's native
facilities for saving authentication tokens.  Cookies are managed by the
browser instead of being saved and restored by the library.

This is how you create a new BaseClient instance::

    pkgdb = new BaseClient('https://admin.fedoraproject.org/pkgdb',
        {useragent: 'My DojoClient/0.1', username: 'admin', password: 'admin'});

The first argument to the :class:`BaseClient` constructor is the base_url of
the `Fedora Service`_.  Then there are a collection of optional keyword
arguments which are placed in a dictionary.  The other params are used to
change the options that configure the :class:`BaseClient`.

.. _`Fedora Service`: http://fedorahosted.org/wiki/doc/service.html

-------------
start_request
-------------

python-fedora's `BaseClient` has a method named `send_request()`.  That method
performs a blocking call to the server, returning data from the server or
raising an error.  :class:`fedora.dojo.BaseClient`'s equivalent method is
:meth:`start_request()`.  It's been renamed because it is an asynchronous,
non-blocking method rather than a synchronous request.  We may create a
`send_request()` at a later date that processes events synchronously but we
encourage you to use :meth:`start_request()` instead.  The asynchronous call
is more powerful and useful for writing dynamic, event driven applications.

this is how you invoke :meth:start_request::

    action = pkgdb.start_request('/packages/name/kernel',
        {req_params: {collectionName: 'Fedora', collectionVersion: 'devel'}});
    action.addCallback(process_data);

This is the basic method of invokng :meth:`start_request`.  You give it the
`method` and any mandatory, positional arguments as the first parameter.
Other, optional parameters are passed in a dictionary.  One of the most useful
of these is the `req_params` parameter.  In this example it is sending two
optional, keyword arguments to the Fedora Service method.

Unlike :meth:`send_request`, :meth:`start_request` does not immediately
return any data.  Instead it returns a Dojo Deferred.  This is an object
that processes the network request asynchronously and then calls a chain of
callbacks assigned to it once the data is available.  This is much like WSGI's
idea of pipes of data.  The design makes it possible for the caller to
layer multiple callbacks and error handlers that operate on the data once it
is returned.

---
API
---

.. module:: fedora.dojo.BaseClient
    :synopsis: Make communicating with Fedora Services easy.

.. moduleauthor:: Toshio Kuratomi <toshio@fedoraproject.org>

.. class:: BaseClient(base_url[, useragent='Fedora DojoClient/VERSION', username=null, password=null, debug=false])

    Create a client configured for a particular service.

    :arg base_url: Base of every URL used to contact the server
    :kwarg useragent: useragent string to use
    :kwarg username: Username to use when establishing an authenticated
        connection
    :kwarg password: Password to use with authenticated connections
    :kwarg debug: If true, log extra debug information

    .. attribute:: base_url

        Base of every URL used to contact the server.

    .. attribute:: useragent

        Useragent string to use

    .. attribute:: username

        Username to use when establishing an authenticated connection

    .. attribute:: password

        Password to use with authenticated connections

    .. attribute:: debug

        If true, log extra debug information

    .. method:: start_request(method[, req_params={}, auth=false, timeout=600000])-> dojo.Deferred

        The given method is called with any parameters set in ``req_params``.
        If auth is True, then the request is made with an authenticated
        session cookie.  Note that path parameters should be set by adding
        onto the method, not via ``req_params``.

        :arg method: Method to call on the server.  It's a url fragment that
            comes after the base_url set in __init__().  Note that any
            parameters set as extra path information should be listed here,
            not in ``req_params``.
        :kwarg req_params: Dict containing extra parameters to send to the
            server
        :kwarg auth: If True, perform authentication to the server
        :kwarg timeout: Milliseconds to wait for a response.  Default 600000:
            10 minutes
        :returns: Deferred that will give data back to the function.  Set a
            callback on the Deferred using .addCallback().  Set an error
            handler using.addErrorback().
        :rtype: dojo.Deferred

    .. method:: logout()

        Logout from the server.

        :returns: Deferred so you can attach a callback/errorback if you want
            to do something special after the logout is processed.
        :rtype: dojo.Deferred
