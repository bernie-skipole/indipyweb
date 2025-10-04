

import sys, argparse, pathlib, asyncio

import uvicorn

from .iclient import ipywebclient, version

from .web.app import ipywebapp

from .web.userdata import setupdbase

from .register import read_configuration


if sys.version_info < (3, 10):
    raise ImportError('indipyweb requires Python >= 3.10')


def getconfig():

    parser = argparse.ArgumentParser(usage="indipyweb [options]",
                                     description="Web server to communicate to an INDI service.")
    parser.add_argument("--config", help="Path to configuration file.")
    parser.add_argument("--version", action="version", version=version)
    args = parser.parse_args()

    if not args.config:
        # No configfile given, defaults will be used
        return

    message = read_configuration(args.config)
    if message:
        print(f"Error: {message}")
        sys.exit(1)



async def main():

    iclient = ipywebclient()
    app = ipywebapp(iclient)

    config = uvicorn.Config(app=app, port=8000, log_level="info")
    server = uvicorn.Server(config)

    await asyncio.gather(server.serve(), iclient.asyncrun())



if __name__ == "__main__":
    # Read the program arguments, and the configuration file
    getconfig()
    # Once configuration file is read, setup the database
    setupdbase()
    # And run main
    asyncio.run(main())
