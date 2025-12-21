
"""
Provides ipywebclient, version
"""

import asyncio

import indipyclient as ipc

from .web.app import ipywebapp
from .web.userdata import LANDING_EVENT, setupdbase, get_indiclient, getconfig, setconfig, get_device_event

version = "0.1.4"



def ipywebclient(host, port, dbfolder, securecookie):
    "Create an instance of IPyWebClient, return the asgi app"

    setconfig('securecookie', securecookie)

    setupdbase(host, port, dbfolder)

    indihost = getconfig("indihost")
    indiport = getconfig("indiport")
    indiclient = IPyWebClient(indihost=indihost, indiport=indiport)
    indiclient.BLOBfolder = getconfig("blobfolder")
    setconfig("indiclient", indiclient)
    # create and return the asgi app
    return ipywebapp(do_startup, do_shutdown)


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

        if event.eventtype in ("ConnectionMade", "ConnectionLost"):
            LANDING_EVENT.set()
            LANDING_EVENT.clear()
            return

        if event.eventtype in ("Define", "Delete"):
            # for the landing page
            LANDING_EVENT.set()
            LANDING_EVENT.clear()
            # for the page showing a device
            if event.devicename:
                de = get_device_event(event.devicename)
                de.set()
                de.clear()
            return

        if event.devicename:
            if event.vectorname:
                if event.eventtype == "TimeOut":
                    event.vector.user_string = "Response has timed out"
                    event.vector.state = 'Alert'
                    event.vector.timestamp = event.timestamp
                else:
                    event.vector.user_string = ""
            de = get_device_event(event.devicename)
            de.set()
            de.clear()
        else:
            # no devicename, may be a system message
            LANDING_EVENT.set()
            LANDING_EVENT.clear()
