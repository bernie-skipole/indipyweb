"""
indipyweb is normally run as 'python -m indipyweb'

In which case it creates an app and runs it with uvicorn.


However if indipyweb is imported into your own script, then three functions are available

indipyweb.make_app(dbfolder=None, securecookie = False)  returns an app, ready to be run with uvicorn

indipyweb.get_dbhost()    returns the web host from the database

indipyweb.get_dbport()    returns the web port from the database

You may want to use this host and port, or you may want to choose your own, and ignore the
database values, the coice is yours.

So you could create your own script main.py:

--------------------------------
from indipyweb import make_app

app = make_app()
--------------------------------

And you could then run uvicorn directly with

uvicorn main:app

"""


import sys, pathlib

from .iclient import ipywebclient

from .web.userdata import getconfig



def make_app(dbfolder=None, securecookie = False):
    "Sets the database folder and securecookie flag, returns the ASGI app"
    if dbfolder:
        try:
            dbfolder = pathlib.Path(dbfolder).expanduser().resolve()
        except Exception:
            print("Error: If given, the database folder should be an existing directory")
            sys.exit(1)
        else:
            if not dbfolder.is_dir():
                print("Error: If given, the database folder should be an existing directory")
                sys.exit(1)
    else:
        dbfolder = pathlib.Path.cwd()

    # create the asgi app
    return ipywebclient('', '', dbfolder, securecookie)


def get_dbhost():
    """Returns the web listenning host as set in the database file
       Should only be called after 'make_app' is called"""
    return getconfig('host')

def get_dbport():
    """Returns the web listenning port as set in the database file
       Should only be called after 'make_app' is called"""
    return getconfig('port')
