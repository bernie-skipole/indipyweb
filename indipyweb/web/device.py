"""
Handles all routes beneath /device
"""


from litestar import Litestar, get, post, Request, Router
from litestar.plugins.htmx import HTMXTemplate, ClientRedirect
from litestar.response import Template, Redirect
from litestar.datastructures import State

from litestar.response import ServerSentEvent, ServerSentEventMessage
from litestar.types import SSEData

from ..register import indihostport, localtimestring, get_device_messages_event, get_indiclient

from .userdata import setuserdevice, getuserdevice


@get("/choosedevice/{device:str}")
async def choosedevice(device:str, request: Request[str, str, State]) -> Template|Redirect:
    """A device has been selected"""
    # have to check device exists #############################
    cookie = request.cookies.get('token', '')
    # associate this session with a device
    setuserdevice(cookie, device)
    # add items to a context dictionary
    context = {"device":device}
    return Template(template_name="device/devicepage.html", context=context)   # The top device page


class ShowMessages:
    """Iterate with messages whenever a message change happens."""

    def __init__(self, device):
        self.lasttimestamp = None
        self.device = device
        self.message_event = get_device_messages_event(device)
        self.iclient = get_indiclient()

    def __aiter__(self):
        return self

    async def __anext__(self):
        "Whenever there is a new message, return a ServerSentEventMessage message"
        while True:
            if self.iclient.stop:
                raise StopAsyncIteration
            if not self.iclient.connected:                     #### note, check device exists, event to go back to main page?
                raise StopAsyncIteration
            # get new message
            if self.iclient[device].messages:
                lasttimestamp = self.iclient[device].messages[0][0]
                if (self.lasttimestamp is None) or (lasttimestamp != self.lasttimestamp):
                    # a new message is received
                    self.lasttimestamp = lasttimestamp
                    return ServerSentEventMessage(event="devicemessages")
            elif self.lasttimestamp is not None:
                # There are no self.iclient[device].messages, but self.lasttimestamp
                # has a value, so there has been a change
                self.lasttimestamp = None
                return ServerSentEventMessage(event="devicemessages")
            # No change, wait, at most 5 seconds, for a device message event
            try:

                await asyncio.wait_for(self.message_event.wait(), timeout=5.0)
            except TimeoutError:
                pass
            # either a device message event has occurred, or 5 seconds since the last has passed
            # so continue the while loop to check for any new messages


# SSE Handler
@get(path="/messages", sync_to_thread=False)
def messages() -> ServerSentEvent:
    cookie = request.cookies.get('token', '')
    device = getuserdevice(cookie)
    return ServerSentEvent(ShowMessages(device))

@get("/updatemessages")
async def updatemessages() -> Template:
    "Updates the messages on the main public page"
    cookie = request.cookies.get('token', '')
    device = getuserdevice(cookie)
    iclient = get_indiclient()
    messages = list(iclient[device].messages)
    messagelist = list(localtimestring(t) + "  " + m for t,m in messages)
    messagelist.reverse()
    # Show last three messages
    if len(messagelist) > 3:
        messagelist = messagelist[-3:]
    return HTMXTemplate(template_name="messages.html", context={"messages":messagelist})




device_router = Router(path="/device", route_handlers=[choosedevice,
                                                       messages,
                                                       updatemessages
                                                       ])
