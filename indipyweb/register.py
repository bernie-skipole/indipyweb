import asyncio

from pathlib import Path


_PARAMETERS = {

                "indihost":"localhost",
                "indiport":7624,
                "indiclient":None

              }

DEFINE_EVENT = asyncio.Event()

MESSAGE_EVENT = asyncio.Event()

DEVICE_MESSAGES = {}



def set_indiclient(iclient):
    global _PARAMETERS
    _PARAMETERS["indiclient"] = iclient

def get_indiclient():
    global _PARAMETERS
    return _PARAMETERS["indiclient"]


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


def localtimestring(t):
    "Return a string of the local time (not date)"
    localtime = t.astimezone(tz=None)
    # convert microsecond to integer between 0 and 100
    ms = localtime.microsecond//10000
    return f"{localtime.strftime('%H:%M:%S')}.{ms:0>2d}"


def get_device_messages_event(device):
    global DEVICE_MESSAGES
    if device not in DEVICE_MESSAGES:
        DEVICE_MESSAGES[device] = asyncio.Event()
    return DEVICE_MESSAGES[device]
