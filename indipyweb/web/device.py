"""
Handles all routes beneath /device
"""

import asyncio

from asyncio.exceptions import TimeoutError

from itertools import cycle

from litestar import Litestar, get, post, Request, Router
from litestar.plugins.htmx import HTMXTemplate, ClientRedirect
from litestar.response import Template, Redirect
from litestar.datastructures import State

from litestar.response import ServerSentEvent, ServerSentEventMessage

from .userdata import localtimestring, get_device_event, get_vector_event, get_indiclient, getuserauth, get_deviceobj

class DeviceEvent:
    """Iterate with messages whenever a device change happens.

     event devicemessages whenever a device message changes
     event vector_${vectorobj.itemid} whenever a vector changes"""

    def __init__(self, deviceobj):
        self.lasttimestamp = None
        self.deviceobj = deviceobj
        self.device_event = get_device_event(deviceobj.devicename)
        self.iclient = get_indiclient()

    def __aiter__(self):
        return self

    async def __anext__(self):
        "Whenever there is a new message, return a ServerSentEventMessage message"

        while True:
            if self.iclient.stop:
                raise StopAsyncIteration
            if not self.iclient.connected:
                await asyncio.sleep(2)
                return ServerSentEventMessage(event="devicemessages") # forces the client to send updatemessages
                                                                      # which checks status of the device
            if not self.deviceobj.enable:
                await asyncio.sleep(2)
                return ServerSentEventMessage(event="devicemessages")

            # check for message change
            if self.deviceobj.messages:
                lasttimestamp = self.deviceobj.messages[0][0]
                if (self.lasttimestamp is None) or (lasttimestamp != self.lasttimestamp):
                    # a new message is received
                    self.lasttimestamp = lasttimestamp
                    return ServerSentEventMessage(event="devicemessages")
            elif self.lasttimestamp is not None:
                # There are no deviceobj.messages, but self.lasttimestamp
                # has a value, so there has been a change
                self.lasttimestamp = None
                return ServerSentEventMessage(event="devicemessages")

            # No change, wait, at most 5 seconds, for a device message event
            try:
                await asyncio.wait_for(self.device_event.wait(), timeout=5)
            except TimeoutError:
                pass
            # either a device message event has occurred, or 5 seconds since the last has passed
            # so continue the while loop to check for any new messages


class VectorEvent:
    """Iterate whenever a device vector change happens.

     event vector_${vectorobj.itemid}"""

    def __init__(self, deviceobj, group):

        self.deviceobj = deviceobj
        self.vector_event = get_vector_event(deviceobj.devicename)
        self.iclient = get_indiclient()
        self.vectors = tuple([None, vectorobj] for vectorobj in self.deviceobj.values() if vectorobj.enable and vectorobj.group == group)
        self.number = len(self.vectors)  # number of vectors
        self.rotator = cycle(self.vectors)


    def __aiter__(self):
        return self

    async def __anext__(self):
        "Whenever there is a vector change, return a ServerSentEventMessage message"

        while True:
            if self.iclient.stop:
                raise StopAsyncIteration

            for i in range(self.number):
                nextvector = next(self.rotator)
                lasttimestamp = nextvector[0]
                currenttimestamp = nextvector[1].timestamp
                if (lasttimestamp is None) or (lasttimestamp != currenttimestamp):
                    # the vector has been updated
                    nextvector[0] = currenttimestamp
                    return ServerSentEventMessage(event= f"vector_{nextvector[1].itemid}")

            # No change, wait, at most 5 seconds, for an event
            try:
                await asyncio.wait_for(self.vector_event.wait(), timeout=5)
            except TimeoutError:
                pass
            # either a vector change has occurred, or 5 seconds since the last has passed
            # so continue the while loop to check again



# SSE Handler
@get(path="/devicechange/{deviceid:int}", exclude_from_auth=True, sync_to_thread=False)
def devicechange(deviceid:int, request: Request[str, str, State]) -> ServerSentEvent|ClientRedirect:
    deviceobj = get_deviceobj(deviceid)
    if deviceobj is None:
        return ClientRedirect("/")
    return ServerSentEvent(DeviceEvent(deviceobj))


# SSE Handler
@get(path="/vectorchange/{deviceid:int}/{group:str}", exclude_from_auth=True, sync_to_thread=False)
def vectorchange(deviceid:int, group:str, request: Request[str, str, State]) -> ServerSentEvent|ClientRedirect:
    deviceobj = get_deviceobj(deviceid)
    if deviceobj is None:
        return ClientRedirect("/")
    return ServerSentEvent(VectorEvent(deviceobj, group))



@get("/choosedevice/{deviceid:int}", exclude_from_auth=True, sync_to_thread=False)
def choosedevice(deviceid:int, request: Request[str, str, State]) -> Template|Redirect:
    """A device has been selected"""

    # have to check device exists
    deviceobj = get_deviceobj(deviceid)
    if deviceobj is None:
        return Redirect("/")
    # Check if user is logged in
    loggedin = False
    cookie = request.cookies.get('token', '')
    if cookie:
        userauth = getuserauth(cookie)
        if userauth is not None:
            loggedin = True
    iclient = get_indiclient()
    blobfolder = True if iclient.BLOBfolder else False
    groups = list(set(vectorobj.group for vectorobj in deviceobj.values() if vectorobj.enable))
    groups.sort()
    group = groups[0]
    vectorsingroup = list(vectorobj for vectorobj in deviceobj.values() if vectorobj.group == group and vectorobj.enable)
    vectorsingroup.sort(key=lambda x: x.label)   # sort by label
    context = {"device":deviceobj.devicename,
               "deviceid":deviceobj.itemid,
               "group":group,
               "groups":groups,
               "loggedin":loggedin,
               "vectors": vectorsingroup,
               "blobfolder":blobfolder}

    return Template(template_name="devicepage.html", context=context)


@get("/updatemessages/{deviceid:int}", exclude_from_auth=True, sync_to_thread=False)
def updatemessages(deviceid:int, request: Request[str, str, State]) -> Template|ClientRedirect:
    "Updates the messages on the device page, and redirects to / if device deleted"
    deviceobj = get_deviceobj(deviceid)
    if deviceobj is None:
        return ClientRedirect("/")
    messages = list(deviceobj.messages)
    if not messages:
        return HTMXTemplate(template_name="messages.html", context={"messages":["Device messages : Waiting.."]})
    messagelist = list(localtimestring(t) + "  " + m for t,m in messages)
    messagelist.reverse()
    # Show last three messages
    if len(messagelist) > 3:
        messagelist = messagelist[-3:]
    return HTMXTemplate(template_name="messages.html", context={"messages":messagelist})



@get("/changegroup/{deviceid:int}/{group:str}", exclude_from_auth=True, sync_to_thread=False)
def changegroup(deviceid:int, group:str, request: Request[str, str, State]) -> Template|ClientRedirect:
    "Set chosen group, populate group tabs and group vectors"
    # check valid group
    if not group:
        return ClientRedirect("/")
    deviceobj = get_deviceobj(deviceid)
    if deviceobj is None:
        return ClientRedirect("/")
    iclient = get_indiclient()
    blobfolder = True if iclient.BLOBfolder else False
    # Check if user is logged in
    loggedin = False
    cookie = request.cookies.get('token', '')
    if cookie:
        userauth = getuserauth(cookie)
        if userauth is not None:
            loggedin = True
    groups = list(set(vectorobj.group for vectorobj in deviceobj.values() if vectorobj.enable ))
    groups.sort()
    if group not in groups:
        group = groups[0]
    # get vectors in this group
    vectorsingroup = list(vectorobj for vectorobj in deviceobj.values() if vectorobj.group == group and vectorobj.enable)
    vectorsingroup.sort(key=lambda x: x.label)   # sort by label
    context = { "deviceid":deviceid,
                "device": deviceobj.devicename,
                "vectors":vectorsingroup,
                "groups":groups,
                "selectedgp":group,
                "loggedin":loggedin,
                "blobfolder":blobfolder}

    return HTMXTemplate(template_name="group.html", context=context)



device_router = Router(path="/device", route_handlers=[choosedevice,
                                                       devicechange,
                                                       vectorchange,
                                                       updatemessages,
                                                       changegroup
                                                       ])
