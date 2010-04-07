from cherrypy import request
from turbogears import config, url
from fedora.tg.util import tg_url

# this is taken from turbogears 1.1 branch
def get_server_name():
    """Return name of the server this application runs on.

    Respects 'Host' and 'X-Forwarded-Host' header.

    See the docstring of the 'absolute_url' function for more information.

    """
    get = config.get
    h = request.headers
    host = get('tg.url_domain') or h.get('X-Forwarded-Host', h.get('Host'))
    if not host:
        host = '%s:%s' % (get('server.socket_host', 'localhost'),
            get('server.socket_port', 8080))
    return host


def tg_absolute_url(tgpath='/', params=None, **kw):
    """Return absolute URL (including schema and host to this server).

    Tries to account for 'Host' header and reverse proxying
    ('X-Forwarded-Host').

    The host name is determined this way:

    * If the config setting 'tg.url_domain' is set and non-null, use this value.
    * Else, if the 'base_url_filter.use_x_forwarded_host' config setting is
      True, use the value from the 'Host' or 'X-Forwarded-Host' request header.
    * Else, if config setting 'base_url_filter.on' is True and
      'base_url_filter.base_url' is non-null, use its value for the host AND
      scheme part of the URL.
    * As a last fallback, use the value of 'server.socket_host' and
      'server.socket_port' config settings (defaults to 'localhost:8080').

    The URL scheme ('http' or 'http') used is determined in the following way:

    * If 'base_url_filter.base_url' is used, use the scheme from this URL.
    * If there is a 'X-Use-SSL' request header, use 'https'.
    * Else, if the config setting 'tg.url_scheme' is set, use its value.
    * Else, use the value of 'cherrypy.request.scheme'.

    """
    get = config.get
    use_xfh = get('base_url_filter.use_x_forwarded_host', False)
    if request.headers.get('X-Use-SSL'):
        scheme = 'https'
    else:
        scheme = get('tg.url_scheme')
    if not scheme:
        scheme = request.scheme
    base_url = '%s://%s' % (scheme, get_server_name())
    if get('base_url_filter.on', False) and not use_xfh:
        base_url = get('base_url_filter.base_url').rstrip('/')
    return '%s%s' % (base_url, tg_url(tgpath, params, **kw))

def absolute_url(tgpath='/', params=None, **kw):
    return url(tg_absolute_url(tgpath, params, **kw))
