
"""
Provides ipywebclient, version
"""

import asyncio

import indipyclient as ipc

from .web.userdata import DEFINE_EVENT, MESSAGE_EVENT, getconfig, setconfig, get_device_event, get_vector_event

version = "0.0.1"



def ipywebclient():
    "Create and store an instance of IPyWebClient"

    indihost = getconfig("indihost")
    indiport = getconfig("indiport")
    indiclient = IPyWebClient(indihost=indihost, indiport=indiport)
    indiclient.BLOBfolder = getconfig("blobfolder")
    setconfig("indiclient", indiclient)



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

        if event.vector:
           if event.eventtype == "TimeOut":
               event.vector.user_string = "Response has timed out"
               event.vector.state = 'Alert'
               event.vector.timestamp = event.timestamp
           else:
               event.vector.user_string = ""
           # set vector event when a vector is updated
           ve = get_vector_event(event.devicename, event.vectorname)
           ve.set()
           ve.clear()
