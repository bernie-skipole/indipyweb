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

You should start by connecting with a browser, on localhost:8000 unless you have changed the port with the above command line options.

On startup, if an INDI service is not running, or not present on localhost:7624 you will see failed connection attemps in the initial web page and no devices will be available. You can still login to add users and create initial settings, including setting the host and port where the INDI service can be found. These values will be saved in the database file and read on future startups.

As the web service by default listens on 'localhost' only a browser running on the same machine will be able to connect. Set the host to '0.0.0.0' to listen on all interfaces.

A typical session would look like:

![Browser screenshot](https://raw.githubusercontent.com/bernie-skipole/indipyweb/main/indipyweb.png)


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
