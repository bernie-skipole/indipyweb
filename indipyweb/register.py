import asyncio

from pathlib import Path


_PARAMETERS = {

                "indihost":"localhost",
                "indiport":7624

              }

DEFINE_EVENT = asyncio.Event()

MESSAGE_EVENT = asyncio.Event()


def read_configuration(config):
    "Return None on success, message on failure"
    ### read the config file here and update _PARAMETERS
    try:
        configfile = pathlib.Path(config).expanduser().resolve()
    except Exception:
        return "If given, the config file must exist"
    if not configfile.is_file():
        return "If given, the config file must exist"
    ### read the config file here and update _PARAMETERS
    return


def getconfig(parameter):
    return _PARAMETERS.get(parameter)

def indihostport():
    "Returns the string 'hostname:port' for the INDI server"
    return f"{_PARAMETERS['indihost']}:{_PARAMETERS['indiport']}"


def userdbase_location():
    return Path.cwd()


def userdbase_file():
    return userdbase_location() / "users.sqlite"
