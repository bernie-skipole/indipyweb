
"""
Provides ipywebclient, version
"""

import asyncio

import indipyclient as ipc

from .web.userdata import DEFINE_EVENT, MESSAGE_EVENT, get_indiclient, getconfig, setconfig, get_device_event, get_vector_event

version = "0.0.4"



def ipywebclient():
    "Create and store an instance of IPyWebClient"

    indihost = getconfig("indihost")
    indiport = getconfig("indiport")
    indiclient = IPyWebClient(indihost=indihost, indiport=indiport)
    indiclient.BLOBfolder = getconfig("blobfolder")
    setconfig("indiclient", indiclient)


def do_startup():
    """Start the client, called from Litestar app, the task is set into
       the global config to ensure a strong reference to it remains"""
    iclient = get_indiclient()
    runclient = asyncio.create_task(iclient.asyncrun())
    setconfig("runclient", runclient)

async def do_shutdown():
    "Stop the client, called from Litestar app"
    iclient = get_indiclient()
    iclient.shutdown()
    await iclient.stopped.wait()


class IPyWebClient(ipc.IPyClient):

    async def rxevent(self, event):

        if event.eventtype == "getProperties":
            return

        if event.eventtype in ("Define", "Delete", "ConnectionMade", "ConnectionLost"):
            DEFINE_EVENT.set()
            DEFINE_EVENT.clear()
            if event.devicename:
                dme = get_device_event(event.devicename)
                dme.set()
                dme.clear()
            return

        if event.devicename and not event.vectorname:
            # Probably a device message
            dme = get_device_event(event.devicename)
            dme.set()
            dme.clear()

        if event.vectorname:
            dve = get_vector_event(event.devicename)
            if event.eventtype == "TimeOut":
                event.vector.user_string = "Response has timed out"
                event.vector.state = 'Alert'
                event.vector.timestamp = event.timestamp
            else:
                event.vector.user_string = ""
            dve.set()
            dve.clear()
