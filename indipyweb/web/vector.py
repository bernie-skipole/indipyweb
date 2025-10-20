"""
Handles all routes beneath /vector
"""

import asyncio

from asyncio.exceptions import TimeoutError

from litestar import Litestar, get, post, Request, Router
from litestar.plugins.htmx import HTMXTemplate, ClientRedirect, ClientRefresh
from litestar.response import Template, Redirect
from litestar.datastructures import State

from litestar.response import ServerSentEvent, ServerSentEventMessage
from litestar.types import SSEData

from ..register import localtimestring, get_vector_event, get_indiclient


class VectorEvent:
    """Iterate with whenever a vector change happens."""

    def __init__(self, device, vector):
        self.lasttimestamp = None
        self.device = device
        self.vector = vector
        self.vector_event = get_vector_event(device, vector)
        self.iclient = get_indiclient()

    def __aiter__(self):
        return self

    async def __anext__(self):
        "Whenever there is a new vector event, return a ServerSentEventMessage message"
        while True:
            if self.iclient.stop or (not self.iclient.connected):
                await asyncio.sleep(2)
                return ServerSentEventMessage(event=self.vector) # forces the client to send update
                                                                 # which requests new vector
            if self.device not in self.iclient:
                await asyncio.sleep(2)
                return ServerSentEventMessage(event=self.vector)
            deviceobject = self.iclient.get(self.device)
            if (deviceobject is None) or not deviceobject.enable:
                await asyncio.sleep(2)
                return ServerSentEventMessage(event=self.vector)
            vectorobject = deviceobject.get(self.vector)
            if (vectorobject is None) or not vectorobject.enable:
                await asyncio.sleep(2)
                return ServerSentEventMessage(event=self.vector)
            # So nothing wrong with the vector, check timestamp
            lasttimestamp = vectorobject.timestamp
            if (self.lasttimestamp is None) or (lasttimestamp != self.lasttimestamp):
                # the vector has been updated
                self.lasttimestamp = lasttimestamp
                return ServerSentEventMessage(event=self.vector)
            # No change, wait, at most 5 seconds, for a vector event
            try:
                await asyncio.wait_for(self.vector_event.wait(), timeout=5.0)
            except TimeoutError:
                pass
            # either a vector event has occurred, or 5 seconds since the last has passed
            # so continue the while loop to check for any new events


# SSE Handler
@get(path="/vectorsse/{device:str}/{vector:str}", sync_to_thread=False)
def vectorsse(device:str, vector:str, request: Request[str, str, State]) -> ServerSentEvent:
    return ServerSentEvent(VectorEvent(device, vector))



@get("/update/{device:str}/{vector:str}")
async def update(device:str, vector:str, request: Request[str, str, State]) -> Template|ClientRedirect|ClientRefresh:
    "Update vector"
    # check valid vector
    if not vector:
        return ClientRedirect("/")
    if not device:
        return ClientRedirect("/")
    iclient = get_indiclient()
    if iclient.stop:
        return ClientRedirect("/")
    if not iclient.connected:
        return ClientRedirect("/")
    if device not in iclient:
        return ClientRedirect("/")
    deviceobj = iclient[device]
    if not deviceobj.enable:
        return ClientRedirect("/")
    if vector not in deviceobj:
        return ClientRefresh()
    vectorobj = deviceobj[vector]
    if not vectorobj.enable:
        return ClientRefresh()

    if vectorobj.user_string:
        # This is not a full update, just an update of the result and state fields
        return HTMXTemplate(template_name="vector/result.html",
                            re_target=f"#result_{vectorobj.name}",
                            context={"state":f"{vectorobj.state}",
                                     "stateid":f"state_{vectorobj.name}",
                                     "timestamp":localtimestring(vectorobj.timestamp),
                                     "result":vectorobj.user_string})

    # have to return a vector html template here
    return HTMXTemplate(template_name="vector/getvector.html", context={"vectorobj":vectorobj,
                                                                        "timestamp":localtimestring(vectorobj.timestamp),
                                                                        "message_timestamp":localtimestring(vectorobj.message_timestamp)})


@post("/submit/{device:str}/{vector:str}")
async def submit(device:str, vector:str, request: Request[str, str, State]) -> Template|ClientRedirect|ClientRefresh:
    # check valid vector
    if not vector:
        return ClientRedirect("/")
    if not device:
        return ClientRedirect("/")
    iclient = get_indiclient()
    if iclient.stop:
        return ClientRedirect("/")
    if not iclient.connected:
        return ClientRedirect("/")
    if device not in iclient:
        return ClientRedirect("/")
    deviceobj = iclient[device]
    if not deviceobj.enable:
        return ClientRedirect("/")
    if vector not in deviceobj:
        return ClientRefresh()
    vectorobj = deviceobj[vector]
    if not vectorobj.enable:
        return ClientRefresh()

    form_data = await request.form()
    members = {name:value for name,value in form_data.items() if value and (name in vectorobj)}
    if not members:
        return HTMXTemplate(None, template_str="<p>Nothing to send!</p>")

    # deal with number vectors
    try:
        if vectorobj.vectortype  == "NumberVector":
            # Have to apply minimum and maximum rules
            for name, value in members.items():
                memberobj = vectorobj.member(name)
                minfloat = memberobj.getfloat(memberobj.min)
                floatval = memberobj.getfloat(value)
                # check step, and round floatval to nearest step value
                stepvalue = memberobj.getfloat(memberobj.step)
                if stepvalue:
                    floatval = round(floatval / stepvalue) * stepvalue
                if memberobj.max != memberobj.min:
                    maxfloat = memberobj.getfloat(memberobj.max)
                    if floatval > maxfloat:
                        floatval = maxfloat
                    elif floatval < minfloat:
                        floatval = minfloat
                members[name] = floatval

    except Exception as e:
        print(e)
        return HTMXTemplate(template_name="vector/result.html", context={"state":"Alert",
                                                                         "stateid":f"state_{vectorobj.name}",
                                                                         "timestamp":localtimestring(),
                                                                         "result":"Unable to parse number value"})

    # this is ok for light and text vectors
    await iclient.send_newVector(device, vector, members=members)
    return HTMXTemplate(template_name="vector/result.html", context={"state":"Busy",
                                                                     "stateid":f"state_{vectorobj.name}",
                                                                     "timestamp":localtimestring(),
                                                                     "result":"Vector changes sent"})




vector_router = Router(path="/vector", route_handlers=[update, vectorsse, submit])
