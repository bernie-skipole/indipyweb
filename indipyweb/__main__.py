

import sys, argparse, pathlib, asyncio, logging

import uvicorn

from .iclient import ipywebclient, version

from .web.userdata import getconfig


if sys.version_info < (3, 10):
    raise ImportError('indipyweb requires Python >= 3.10')


logger = logging.getLogger("indipyclient")
logger.setLevel("ERROR")
# The above logger generates logs for the INDI client part of the program



def readconfig():

    parser = argparse.ArgumentParser(usage="indipyweb [options]",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description="Web server to communicate to an INDI service.",
                                     epilog="""
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
""")

    parser.add_argument("--port", type=int, help="Listening port of the web server.")
    parser.add_argument("--host", help="Hostname/IP of the web server.")
    parser.add_argument("--dbfolder", help="Folder where the database will be set.")
    parser.add_argument("--securecookie", default="False", help="Set True to enforce https only for cookies.")
    parser.add_argument("--version", action="version", version=version)
    args = parser.parse_args()


    if args.dbfolder:
        try:
            dbfolder = pathlib.Path(args.dbfolder).expanduser().resolve()
        except Exception:
            print("Error: If given, the database folder should be an existing directory")
            sys.exit(1)
        else:
            if not dbfolder.is_dir():
                print("Error: If given, the database folder should be an existing directory")
                sys.exit(1)
    else:
        dbfolder = pathlib.Path.cwd()

    if args.securecookie == "True":
        securecookie = True
    else:
        securecookie = False

    # create the client, store it for later access with get_indiclient()
    app = ipywebclient(args.host, args.port, dbfolder, securecookie)
    host = getconfig('host')
    port = getconfig('port')
    return app, host, port


async def indipywebrun():
    "Read the program arguments, setup the database and run the webserver"
    app, host, port = readconfig()
    print(f"indipyweb version {version} serving on {host}:{port}")
    config = uvicorn.Config(app=app, host=host, port=port, log_level="error")
    server = uvicorn.Server(config)
    await server.serve()
    # the log_level here sets the logging for the uvicorn web server


def main():
    "Run the program"
    asyncio.run(indipywebrun())


if __name__ == "__main__":
    # And run main
    main()
