

import sys, argparse, pathlib, asyncio

import uvicorn

from .iclient import ipywebclient, version

from .web.app import ipywebapp

from .web.userdata import setupdbase, setconfig, getconfig


if sys.version_info < (3, 10):
    raise ImportError('indipyweb requires Python >= 3.10')


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

    # create the client
    indiclient = ipywebclient()   ######### set indihost/port in client, still to do

    # stores indiclient so other parts of the program can retrieve it
    setconfig("indiclient", indiclient)

    host = getconfig('host')
    port = getconfig('port')

    return host, port, indiclient




async def main():

    # Read the program arguments
    host, port, indiclient = readconfig()
    app = ipywebapp()
    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    await asyncio.gather(server.serve(), indiclient.asyncrun())



if __name__ == "__main__":

    # And run main
    asyncio.run(main())
