

import sys, argparse, pathlib, asyncio

import uvicorn

from .iclient import ipywebclient, version

from .web.app import ipywebapp

from .web.userdata import setupdbase

from .register import set_configuration, set_indiclient


if sys.version_info < (3, 10):
    raise ImportError('indipyweb requires Python >= 3.10')


def getconfig():

    parser = argparse.ArgumentParser(usage="indipyweb [options]",
                                     description="Web server to communicate to an INDI service.")
    parser.add_argument("--port", type=int, help="Listening port of the web server.")
    parser.add_argument("--host", help="Hostname/IP of the web server.")
    parser.add_argument("--db", help="Folder where the database will be set.")
    parser.add_argument("--version", action="version", version=version)
    args = parser.parse_args()


    if args.db:
        try:
            dbfolder = pathlib.Path(args.dbfolder).expanduser().resolve()
        except Exception:
            print("Error: If given, the database folder should be an existing directory")
            return 1
        else:
            if not dbfolder.is_dir():
                print("Error: If given, the database folder should be an existing directory")
                return 1
    else:
        dbfolder = pathlib.Path.cwd()

    set_configuration(args.host, args.port, dbfolder)




async def main():

    # create the client, and set it into register.py
    indiclient = ipywebclient()
    set_indiclient(indiclient)

    app = ipywebapp()
    config = uvicorn.Config(app=app, port=8000, log_level="info")
    server = uvicorn.Server(config)

    await asyncio.gather(server.serve(), indiclient.asyncrun())



if __name__ == "__main__":
    # Read the program arguments, and the configuration file
    getconfig()
    # Once configuration file is read, setup the database
    setupdbase()
    # And run main
    asyncio.run(main())
