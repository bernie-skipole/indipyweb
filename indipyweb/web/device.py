"""
Handles all routes beneath /device
"""

import asyncio

from asyncio.exceptions import TimeoutError

from litestar import Litestar, get, post, Request, Router
from litestar.plugins.htmx import HTMXTemplate, ClientRedirect, ClientRefresh
from litestar.response import Template, Redirect
from litestar.datastructures import State

from litestar.response import ServerSentEvent, ServerSentEventMessage
from litestar.types import SSEData

from ..register import indihostport, localtimestring, get_device_event, get_indiclient

from .userdata import setuserdevice, getuserdevice, setselectedgp, getselectedgp


@get("/choosedevice/{device:str}")
async def choosedevice(device:str, request: Request[str, str, State]) -> Template|Redirect:
    """A device has been selected"""
    # have to check device exists
    iclient = get_indiclient()
    if device not in iclient:
        return Redirect("/")
    if not iclient[device].enable:
        return Redirect("/")
    # associate this session with a device
    cookie = request.cookies.get('token', '')
    userauth = setuserdevice(cookie, device)
    if userauth is None:
        return Redirect("/")
    # add items to a context dictionary,
    deviceobj = iclient[device]
    vectornames = list(deviceobj.keys())
    vectorobjects = list(deviceobj.values())
    vectorlabels = list(set(vectorobj.label for vectorobj in vectorobjects))
    groups = list(set(vectorobj.group for vectorobj in vectorobjects))
    groups.sort()
    selectedgp = getselectedgp(cookie)
    if (not selectedgp) or (selectedgp not in groups):
        selectedgp = groups[0]
        setselectedgp(cookie, selectedgp)
    vectornames.sort()        ####### change from vectors to vector labels
    vectorlabels.sort()
    context = {"device":device,
               "vectors":vectorlabels,
               "groups":groups,
               "selectedgp":selectedgp,
               "messages":["Device messages : Waiting.."]}
    return Template(template_name="devicepage.html", context=context)   # The top device page


class ShowMessages:
    """Iterate with messages whenever a device change happens."""

    def __init__(self, device):
        self.lasttimestamp = None
        self.device = device
        self.device_event = get_device_event(device)
        self.iclient = get_indiclient()

    def __aiter__(self):
        return self

    async def __anext__(self):
        "Whenever there is a new message, return a ServerSentEventMessage message"
        while True:
            if self.iclient.stop or (not self.iclient.connected):
                await asyncio.sleep(2)
                return ServerSentEventMessage(event="devicemessages") # forces the client to send updatemessages
                                                                      # which checks status of the device
            if self.device not in self.iclient:
                await asyncio.sleep(2)
                return ServerSentEventMessage(event="devicemessages")
            deviceobject = self.iclient[self.device]
            if not deviceobject.enable:
                await asyncio.sleep(2)
                return ServerSentEventMessage(event="devicemessages")
            # So nothing wrong with the device, check for new message
            if deviceobject.messages:
                lasttimestamp = deviceobject.messages[0][0]
                if (self.lasttimestamp is None) or (lasttimestamp != self.lasttimestamp):
                    # a new message is received
                    self.lasttimestamp = lasttimestamp
                    return ServerSentEventMessage(event="devicemessages")
            elif self.lasttimestamp is not None:
                # There are no deviceobject.messages, but self.lasttimestamp
                # has a value, so there has been a change
                self.lasttimestamp = None
                return ServerSentEventMessage(event="devicemessages")
            # No change, wait, at most 5 seconds, for a device event
            try:
                await asyncio.wait_for(self.device_event.wait(), timeout=5.0)
            except TimeoutError:
                pass
            # either a device event has occurred, or 5 seconds since the last has passed
            # so continue the while loop to check for any new messages


# SSE Handler
@get(path="/messages", sync_to_thread=False)
def messages(request: Request[str, str, State]) -> ServerSentEvent:
    cookie = request.cookies.get('token', '')
    device = getuserdevice(cookie)
    return ServerSentEvent(ShowMessages(device))


@get("/updatemessages")
async def updatemessages(request: Request[str, str, State]) -> Template|ClientRedirect:
    "Updates the messages on the device page, and redirects to / if device deleted"
    cookie = request.cookies.get('token', '')
    device = getuserdevice(cookie)
    if device is None:
        return ClientRedirect("/")
    iclient = get_indiclient()
    if iclient.stop:
        return ClientRedirect("/")
    if not iclient.connected:
        return ClientRedirect("/")
    if device not in iclient:
        return ClientRedirect("/")
    if not iclient[device].enable:
        return ClientRedirect("/")
    messages = list(iclient[device].messages)
    if not messages:
        return HTMXTemplate(template_name="messages.html", context={"messages":["Device messages : Waiting.."]})
    messagelist = list(localtimestring(t) + "  " + m for t,m in messages)
    messagelist.reverse()
    # Show last three messages
    if len(messagelist) > 3:
        messagelist = messagelist[-3:]
    return HTMXTemplate(template_name="messages.html", context={"messages":messagelist})



@get("/changegroup/{group:str}")
async def changegroup(group:str, request: Request[str, str, State]) -> Template|ClientRedirect|ClientRefresh:
    "Set chosen group, force a client refresh"
    # check valid group
    cookie = request.cookies.get('token', '')
    setselectedgp(cookie, group)
    return ClientRefresh()






device_router = Router(path="/device", route_handlers=[choosedevice,
                                                       messages,
                                                       updatemessages,
                                                       changegroup
                                                       ])
