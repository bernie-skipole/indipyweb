

import sys, argparse, pathlib, asyncio, logging

import uvicorn

from .iclient import ipywebclient, version

from .web.app import ipywebapp

from .web.userdata import setupdbase, setconfig, getconfig, get_indiclient


if sys.version_info < (3, 10):
    raise ImportError('indipyweb requires Python >= 3.10')


logger = logging.getLogger("indipyclient")
logger.setLevel("INFO")
# The above logger generates logs for the INDI client part of the program



def readconfig():

    parser = argparse.ArgumentParser(usage="indipyweb [options]",
                                     description="Web server to communicate to an INDI service.")
    parser.add_argument("--port", type=int, help="Listening port of the web server.")
    parser.add_argument("--host", help="Hostname/IP of the web server.")
    parser.add_argument("--db", help="Folder where the database will be set.")
    parser.add_argument("--version", action="version", version=version)
    args = parser.parse_args()


    if args.db:
        try:
            dbfolder = pathlib.Path(args.db).expanduser().resolve()
        except Exception:
            print("Error: If given, the database folder should be an existing directory")
            sys.exit(1)
        else:
            if not dbfolder.is_dir():
                print("Error: If given, the database folder should be an existing directory")
                sys.exit(1)
    else:
        dbfolder = pathlib.Path.cwd()

    setupdbase(args.host, args.port, dbfolder)

    # create the client, store it for later access with get_indiclient()
    ipywebclient()

    host = getconfig('host')
    port = getconfig('port')
    app = ipywebapp()

    return app, host, port


async def indipywebrun():
    "Read the program arguments, setup the database and run the webserver"
    app, host, port = readconfig()
    print(f"indipyweb version {version} serving on {host}:{port}")
    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
    # the log_level here sets the logging for the uvicorn web server


def main():
    "Run the program"
    asyncio.run(indipywebrun())


if __name__ == "__main__":
    # And run main
    main()
