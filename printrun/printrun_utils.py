import os
import gettext

# Set up Internationalization using gettext
# searching for installed locales on /usr/share; uses relative folder if not found (windows)
def install_locale(domain):
    if os.path.exists('/usr/share/pronterface/locale'):
        gettext.install(domain, '/usr/share/pronterface/locale', unicode=1)
    elif os.path.exists('/usr/local/share/pronterface/locale'):
        gettext.install(domain, '/usr/local/share/pronterface/locale', unicode=1)
    else: 
        gettext.install(domain, './locale', unicode=1)

def imagefile(filename):
    for prefix in ['/usr/local/share/pronterface/images', '/usr/share/pronterface/images']:
      candidate = os.path.join(prefix, filename)
      if os.path.exists(candidate):
         return candidate
    local_candidate = os.path.join(os.path.dirname(__file__), "images", filename)
    if os.path.exists(local_candidate):
        return local_candidate
    else:
        return os.path.join(os.path.split(os.path.split(__file__)[0])[0], "images", filename)

def lookup_file(filename, prefixes):
    for prefix in prefixes:
      candidate = os.path.join(prefix, filename)
      if os.path.exists(candidate):
         return candidate
    return filename

def pixmapfile(filename):
    return lookup_file(filename, ['/usr/local/share/pixmaps', '/usr/share/pixmaps'])

def sharedfile(filename):
    return lookup_file(filename, ['/usr/local/share/pronterface', '/usr/share/pronterface'])

def configfile(filename):
    return lookup_file(filename, [os.path.expanduser("~/.printrun/"),])
