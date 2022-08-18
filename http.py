from common import log as logging
import httplib
import re
import json

LOG = logging.getLogger(__name__)


class Http(object):
    """
    Base class of Http Api

    Attributes:
    refmt: the regular expresstion of http url
    protocol: the protocol of the url, like http/https
    host: the host/domain in the url
    baseurl: the root url path
    """
    refmt = re.compile('((https?)://)?([^/]+)(.*)')

    def __init__(self, url, timeout=60):
        """
        Constructor
        """
        _, protocol, host, baseurl = self.refmt.match(url).groups()
        self.protocol = protocol or 'http'
        self.baseurl = baseurl or '/'
        if self.baseurl[-1] != '/':
            self.baseurl += '/'
        self.host = host
        self.timeout = timeout

    def access(self, method='GET', url=None, body=None, headers=None):
        """access the url and return the result

        Args:
        method: the http method
        url: the url to access
        body: the post body
        headers: the http headers

        Return:
        (status, rsp_body) tuple, status is the http return code, like 200/302/404 etc.
                                  rsp_body is the http return content
        """
        if isinstance(body, dict):
            data = json.dumps(body)
        else:
            data = body

        if headers is None:
            headers = {}

        if self.protocol == 'http':
            conn = httplib.HTTPConnection(self.host, timeout=self.timeout)
        elif self.protocol == 'https':
            conn = httplib.HTTPSConnection(self.host, timeout=self.timeout)

        if url:
            url = self.baseurl[:-1] + url
        else:
            url = self.baseurl

        LOG.info("%s  %s  %s HTTP/1.1\r\n%s%s" % (self.host, method, url,
            ''.join(["%s: %s\r\n" % (k, v) for k, v in headers.items()]),
            data if data else ''))

        conn.request(method, url, data, headers)
        try:
            resp = conn.getresponse()
            status = resp.status
            rsp_body = resp.read()
            headers = dict(resp.getheaders())
            LOG.debug("HTTP/1.1 %s %s\r\n%s%s" % (status, resp.reason,
                ''.join(["%s : %s\r\n" % (k, v) for k, v in headers.items()]),
                rsp_body.decode("unicode_escape").encode('utf8')))
            conn.close()
        except Exception as e:
            LOG.error("access url %s error %s" % (url, e))
            status = -1
            rsp_body = '{}'
            headers = {}

        return (status, rsp_body, headers)


class Response(object):
    """response class"""
    def __init__(self, status, body, headers):
        self.status = status
        self.body = body
        self.headers = headers


__old_http_access = Http.access


def __hook_func(origin_list, *args, **kwargs):
    """hook http access to get return info"""
    def access(*args, **kwargs):
        """wrap function"""
        status, resp_body, headers = __old_http_access(*args, **kwargs)
        origin_list.append(Response(status, resp_body, headers))
        return status, resp_body, headers
    return access


def hook_http_access():
    """hook http access to get http response/headers etc."""
    origin_list = []
    Http.access = __hook_func(origin_list)
    return origin_list


def unhook_http_access():
    """unhook http access"""
    Http.access = __old_http_access
