# indipyweb

This indipyweb package provides a web service, which in turn connects to an INDI server, allowing you to view and control your instrument from a browser session.

INDI defines a protocol for the remote control of instruments.

INDI - Instrument Neutral Distributed Interface.

See https://en.wikipedia.org/wiki/Instrument_Neutral_Distributed_Interface

The INDI protocol defines the format of the data sent, such as light, number, text, switch or BLOB (Binary Large Object). The client is general purpose, taking the format of switches, numbers etc., from the protocol.

A typical session would look like:

![Browser screenshot](https://raw.githubusercontent.com/bernie-skipole/indipyweb/main/indipyweb.png)

indipyweb is typically installed into a virtual environment with:

pip install indipyweb

The Pypi site being:

https://pypi.org/project/indipyweb

Or if you use uv, it can be loaded and run with:

uvx indipyweb

If installed into a virtual environment, it can be run with:

indipyweb [options]

or with

python -m indipyweb [options]

This will create a database file holding user information in the working directory, and will run a web server on localhost:8000. Connect with a browser, and initially use the default created user, with username admin and password password! - note the exclamation mark.

This server will attempt to connect to an INDI service on localhost:7624, and the user should be able to view and control devices.

The package help is:

    usage: indipyweb [options]

    Web server to communicate to an INDI service.

    options:
      -h, --help                   show this help message and exit
      --port PORT                  Listening port of the web server.
      --host HOST                  Hostname/IP of the web server.
      --dbfolder DBFOLDER          Folder where the database will be set.
      --securecookie SECURECOOKIE  Set True to enforce https only for cookies.
      --version                    show program's version number and exit

    The host and port set here have priority over values set in the database.
    If not given, and not set in the database, 'localhost:8000' is used.
    The database file holds user and INDI port configuration, and can be
    populated via browser using the 'edit' button.
    If it does not already exist, a database file will be created in the
    given db folder, or if not set, the current working directory will be used.
    A newly generated database file will contain a single default username
    and password 'admin' and 'password!'. These should be changed as soon as
    possible and the INDI host/port set (default localhost:7624).
    The securecookie argument is 'False' by default, if using a reverse
    proxy providing https connectivity, set securecookie to the string 'True'
    to ensure loggedin cookies can only pass over https.

You should start by connecting with a browser, on localhost:8000 unless you have changed the port with the above command line options.

On startup, if an INDI service is not running, or not present on localhost:7624 you will see failed connection attemps in the initial web page and no devices will be available. You can still login to add users and create initial settings, including setting the host and port where the INDI service can be found. These values will be saved in the database file and read on future startups.

As the web service by default listens on 'localhost' only a browser running on the same machine will be able to connect. Set the host to '0.0.0.0' to listen on all interfaces.

## importing indipyweb

indipyweb is normally run as 'python -m indipyweb'

In which case it creates an app and runs it with uvicorn.

However if indipyweb is imported into your own script, then three functions are available.

indipyweb.make_app(dbfolder=None, securecookie = False)  returns an app, ready to be run with uvicorn

indipyweb.get_dbhost()    returns the web host from the database

indipyweb.get_dbport()    returns the web port from the database

You may want to use this host and port, or you may want to choose your own, and ignore the database values, the choice is yours.

So you could create your own script main.py:

    from indipyweb import make_app

    app = make_app()


And you could then run uvicorn directly with

uvicorn main:app


## Security

The database file holds hashes of user passwords, if obtained by an attacker, the original passwords would be difficult to extract. However a brute force dictionary attack is possible, so complex passwords, not used elsewhere, should be encouraged. The site requires passwords with at least 8 characters and one special character. Usernames and long names are held in the database in clear text.

It is envisioned this server will be used on local LAN's rather than on the internet. If it is used on a more open system, then it should be served behind a reverse proxy which provides certificates/https. Setting the command line argument 'securecookie' to 'True' enforces cookies will only be sent by browsers over https, unless the connection is to 'localhost'. This is set to False as default so initial development and home usage without a reverse proxy is easy.

This package does not provide the INDI service, that requires drivers to interface with your instrumentation, and a server implementation to run the drivers. This web service connects to such a service, and acts as an INDI 'client'. It should operate with any INDI service that follows the INDI spec, however associated packages by the same author are:

## indipyserver

https://github.com/bernie-skipole/indipyserver

https://pypi.org/project/indipyserver/

https://indipyserver.readthedocs.io

## indipydriver

https://github.com/bernie-skipole/indipydriver

https://pypi.org/project/indipydriver

https://indipydriver.readthedocs.io

## indipyterm

https://github.com/bernie-skipole/indipyterm

https://pypi.org/project/indipyterm/
