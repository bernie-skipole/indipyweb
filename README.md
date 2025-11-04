# indipyweb
Web server, providing browser client connections to an INDI service.

This does not include the INDI server, this is an INDI client.

Requires Python >=3.10 and a virtual environment with:

pip install indipyweb

Then to run the server:

python -m indipyweb

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

Having logged in as admin, choose edit and change your password, you can also choose the system setup to set web and INDI hosts, ports and a folder where any BLOBs sent by the INDI service will be saved. These values will be saved in the database file and read on startup.
