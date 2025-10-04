
"""
Provides ipywebclient, version
"""

import asyncio

import indipyclient as ipc

from .register import DEFINE_EVENT, MESSAGE_EVENT, getconfig, get_device_messages_event

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

        if event.eventtype == "Message":
            MESSAGE_EVENT.set()
            MESSAGE_EVENT.clear()
            if event.devicename:
                dme = get_device_messages_event(devicename)
                dme.set()
                dme.clear()
