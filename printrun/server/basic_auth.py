import tornado.ioloop
import tornado.web
import tornado.websocket
import base64
import logging
import logging.config
import tornado.httpserver
import tornado.ioloop
import tornado.web

log = logging.getLogger("root")

def authenticate(realm, authenticator,user_extractor) :
    """
    This is a basic authentication interceptor which 
    protects the desired URIs and requires 
    authentication as per configuration
    """
    def wrapper(self, transforms, *args, **kwargs):
        def _request_basic_auth(self):
            if self._headers_written:
                raise Exception('headers have already been written')

            # If this is a websocket accept parameter-based (user/password) auth:
            if hasattr(self, 'stream'):
              """
              self.stream.write(tornado.escape.utf8(
                "HTTP/1.1 401 Unauthorized\r\n"+
                "Date: Wed, 10 Apr 2013 02:09:52 GMT\r\n"+
                "Content-Length: 0\r\n"+
                "Content-Type: text/html; charset=UTF-8\r\n"+
                "Www-Authenticate: Basic realm=\"auth_realm\"\r\n"+
                "Server: TornadoServer/3.0.1\r\n\r\n"
              ))
              self.stream.close()
              """
            # If this is a restful request use the standard tornado methods:
            else:
              self.set_status(401)
              self.set_header('WWW-Authenticate','Basic realm="%s"' % realm)
              self._transforms = []
              self.finish()

            return False
        request = self.request
        format = ''
        clazz = self.__class__
        log.debug('intercepting for class : %s', clazz)
        try:
          auth_hdr = request.headers.get('Authorization')

          if auth_hdr == None:
              return _request_basic_auth(self)
          if not auth_hdr.startswith('Basic '):
              return _request_basic_auth(self)

          auth_decoded = base64.decodestring(auth_hdr[6:])
          username, password = auth_decoded.split(':', 2)

          user_info = authenticator(realm, unicode(username), password)
          if user_info :
              self._user_info = user_info
              self._current_user = user_extractor(user_info)
              log.debug('authenticated user is : %s',
                        str(self._user_info))
          else:
              return _request_basic_auth(self)
        except Exception, e:
            return _request_basic_auth(self)
        return True
    return wrapper

def interceptor(func):
    """
    This is a class decorator which is helpful in configuring
    one or more interceptors which are able to intercept, inspect,
    process and approve or reject further processing of the request
    """
    def classwrapper(cls):
        def wrapper(old):
            def inner(self, transforms, *args, **kwargs):
                log.debug('Invoking wrapper %s',func)
                ret = func(self,transforms,*args,**kwargs)
                if ret :
                    return old(self,transforms,*args,**kwargs)
                else :
                    return ret
            return inner
        cls._execute = wrapper(cls._execute)
        return cls
    return classwrapper
