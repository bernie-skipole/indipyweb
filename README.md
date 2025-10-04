# indipyweb
Web server, providing browser client connections to an INDI service

Currently Under Construction

Requires Python >=3.10 and a virtual environment with:

pip install indipyclient

pip install litestar[standard]

pip install litestar[mako]

Then to run the server:

python -m indipyweb

This will create an sqlite file holding user information in the working directory, and will run a server on localhost:8000. Connect with a browser, and initially use the default created user, with username admin and password password! - note the exclamation mark.

This server will attempt to connect to an INDI service on localhost:7624, and the user browser should (eventually) be able to view and set devices, vectors and member values.
