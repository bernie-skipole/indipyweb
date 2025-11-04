# indipyweb
Web server, providing browser client connections to an INDI service.

This does not include the INDI server, this is an INDI client.

INDI defines a protocol for the remote control of instruments.

INDI - Instrument Neutral Distributed Interface.

See https://en.wikipedia.org/wiki/Instrument_Neutral_Distributed_Interface

The INDI protocol defines the format of the data sent, such as light, number, text, switch or BLOB (Binary Large Object). The client is general purpose, taking the format of switches, numbers etc., from the protocol.

indipyweb can be installed from Pypi with:

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

This server will attempt to connect to an INDI service on localhost:7624, and the user browser should be able to view and set devices, vectors and member values.

The package help is:

    usage: indipyweb [options]

    Web server to communicate to an INDI service.

    options:
      -h, --help   show this help message and exit
      --port PORT  Listening port of the web server.
      --host HOST  Hostname/IP of the web server.
      --db DB      Folder where the database will be set.
      --version    show program's version number and exit

On startup, if an INDI service is not running you will see failed attemps to connect on your console. These can be ignored, and you can still use your browser to connect to the web service to create initial settings - though no devices will be available.

Having logged in as admin, choose edit and change your password, you can also choose the system setup to set web and INDI hosts, ports and a folder where any BLOBs sent by the INDI service will be saved. These values will be saved in the database file and read on future startups.

This web service should work with any INDI service, however associated packages by the same author are:

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
