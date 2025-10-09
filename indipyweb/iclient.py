
"""
Provides ipywebclient, version
"""

import asyncio

import indipyclient as ipc

from .register import DEFINE_EVENT, MESSAGE_EVENT, getconfig, get_device_event, get_vector_event

version = "0.0.1"



def ipywebclient():
    "Create and return an instance of IPyWebClient"

    indihost = getconfig("indihost")
    indiport = getconfig("indiport")
    return IPyWebClient(indihost=indihost, indiport=indiport)


class IPyWebClient(ipc.IPyClient):

    async def rxevent(self, event):
        if event.eventtype in ("Define", "Delete", "ConnectionMade", "ConnectionLost"):
            DEFINE_EVENT.set()
            DEFINE_EVENT.clear()
        elif event.eventtype == "Message":
            MESSAGE_EVENT.set()
            MESSAGE_EVENT.clear()
            if event.devicename:
                dme = get_device_event(event.devicename)
                dme.set()
                dme.clear()

        if event.eventtype == "Delete":
            if event.devicename:
                # set a message event, so if the device is deleted
                # when client sends an updatemessages it forces a redirect
                dme = get_device_event(event.devicename)
                dme.set()
                dme.clear()

        if event.devicename and event.vectorname:
           # set vector event when a vector is updated
           ve = get_vector_event(event.devicename, event.vectorname)
           ve.set()
           ve.clear()
