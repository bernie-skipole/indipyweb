"""
Creates the main litestar app with the top level routes
and authentication functions, including setting and testing cookies

Note, edit routes are set under edit.edit_router

"""

import asyncio

from os import listdir, remove
from os.path import isfile, join

from pathlib import Path

from collections.abc import AsyncGenerator

from asyncio.exceptions import TimeoutError

from litestar import Litestar, get, post, Request
from litestar.plugins.htmx import HTMXPlugin, HTMXTemplate, ClientRedirect, ClientRefresh
from litestar.contrib.mako import MakoTemplateEngine
from litestar.template.config import TemplateConfig
from litestar.response import Template, Redirect, File
from litestar.static_files import create_static_files_router
from litestar.datastructures import Cookie, State

from litestar.middleware import AbstractAuthenticationMiddleware, AuthenticationResult, DefineMiddleware
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException, NotFoundException

from litestar.response import ServerSentEvent, ServerSentEventMessage

from . import userdata, edit, device, vector, setup

from ..iclient import do_startup, do_shutdown


# location of static files, for CSS and javascript
STATICFILES = Path(__file__).parent.resolve() / "static"

# location of template files
TEMPLATEFILES = Path(__file__).parent.resolve() / "templates"


class ShowInstruments:
    """Iterate with instruments table whenever an instrument change happens."""

    def __init__(self):
        self.instruments = set()
        self.connected = False
        self.iclient = userdata.get_indiclient()

    def __aiter__(self):
        return self

    async def __anext__(self):
        "Whenever there is a change in devices, return a ServerSentEventMessage message"
        while True:
            if self.iclient.stop:
                raise StopAsyncIteration
            if self.iclient.connected != self.connected:
                self.connected = self.iclient.connected
                return ServerSentEventMessage(event="newinstruments")
            # get a set of instrument names for enabled devices
            newinstruments = set(name for name,value in self.iclient.items() if value.enable)
            if newinstruments == self.instruments:
                # No change, wait, at most 5 seconds, for a DEFINE_EVENT
                try:
                    await asyncio.wait_for(userdata.DEFINE_EVENT.wait(), timeout=5.0)
                except TimeoutError:
                    pass
                # either a DEFINE_EVENT has occurred, or 5 seconds since the last has passed
                # so continue the while loop to check for any new devices
                continue
            # There has been a change, send a newinstruments to the users browser
            self.instruments = newinstruments
            return ServerSentEventMessage(event="newinstruments")


# SSE Handler
@get(path="/instruments", exclude_from_auth=True, sync_to_thread=False)
def instruments() -> ServerSentEvent:
    return ServerSentEvent(ShowInstruments())


class ShowMessages:
    """Iterate with messages whenever a message change happens."""

    def __init__(self):
        self.lasttimestamp = None
        self.connected = False
        self.iclient = userdata.get_indiclient()

    def __aiter__(self):
        return self

    async def __anext__(self):
        "Whenever there is a new message, return a ServerSentEventMessage message"
        while True:
            if self.iclient.stop:
                asyncio.sleep(2)
                return ServerSentEventMessage(event="newmessage")

            if self.iclient.connected != self.connected:
                self.connected = self.iclient.connected
                return ServerSentEventMessage(event="newmessage")
            # get new message
            if self.iclient.messages:
                lasttimestamp = self.iclient.messages[0][0]
                if (self.lasttimestamp is None) or (lasttimestamp != self.lasttimestamp):
                    # a new message is received
                    self.lasttimestamp = lasttimestamp
                    return ServerSentEventMessage(event="newmessages")
            elif self.lasttimestamp is not None:
                # There are no self.iclient.messages, but self.lasttimestamp
                # has a value, so there has been a change
                self.lasttimestamp = None
                return ServerSentEventMessage(event="newmessages")
            # No change, wait, at most 5 seconds, for a MESSAGE_EVENT
            try:
                await asyncio.wait_for(userdata.MESSAGE_EVENT.wait(), timeout=5.0)
            except TimeoutError:
                pass
            # either a MESSAGE_EVENT has occurred, or 5 seconds since the last has passed
            # so continue the while loop to check for any new messages


# SSE Handler
@get(path="/messages", exclude_from_auth=True, sync_to_thread=False)
def messages() -> ServerSentEvent:
    return ServerSentEvent(ShowMessages())


class LoggedInAuth(AbstractAuthenticationMiddleware):
    """Checks if a logged-in cookie is present, and verifies it
       If ok, returns an AuthenticationResult with the user, and the users
       authorisation level. If not ok raises a NotAuthorizedException"""
    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        # retrieve the cookie
        auth_cookie = connection.cookies
        if not auth_cookie:
            raise NotAuthorizedException()
        token =  auth_cookie.get('token')
        if not token:
            raise NotAuthorizedException()
        # the userdata.verify function looks up a dictionary of logged in users
        userinfo = userdata.verify(token)
        # If not verified, userinfo will be None
        # If verified userinfo will be a userdata.UserInfo object
        if userinfo is None:
            raise NotAuthorizedException()
        # Return an AuthenticationResult which will be
        # made available to route handlers as request: Request[str, str, State]
        return AuthenticationResult(user=userinfo.user, auth=userinfo.auth)


def gotologin_error_handler(request: Request, exc: Exception) -> ClientRedirect|Redirect:
    """If a NotAuthorizedException is raised, this handles it, and redirects
       the caller to the login page"""
    if request.htmx:
        return ClientRedirect("/login")
    return Redirect("/login")


def gotonotfound_error_handler(request: Request, exc: Exception) -> ClientRedirect|Redirect:
    """If a NotFoundException is raised, this handles it, and redirects
       the caller to the not found page"""
    if request.htmx:
        return ClientRedirect("/notfound")
    return Redirect("/notfound")


@get("/notfound", exclude_from_auth=True, sync_to_thread=False )
def notfound(request: Request) -> Template:
    "This is the public root page of your site"
    iclient = userdata.get_indiclient()
    # Check if user is looged in
    loggedin = False
    cookie = request.cookies.get('token', '')
    if cookie:
        userauth = userdata.getuserauth(cookie)
        if userauth is not None:
            loggedin = True
    return Template("notfound.html", context={"hostname":userdata.connectedtext(),
                                             "loggedin":loggedin})


# Note, all routes with 'exclude_from_auth=True' do not have cookie checked
# and are not authenticated

@get("/", exclude_from_auth=True, sync_to_thread=False )
def publicroot(request: Request) -> Template:
    "This is the public root page of your site"
    iclient = userdata.get_indiclient()
    # Check if user is looged in
    loggedin = False
    cookie = request.cookies.get('token', '')
    if cookie:
        userauth = userdata.getuserauth(cookie)
        if userauth is not None:
            loggedin = True
    blobfolder = True if iclient.BLOBfolder else False
    return Template("landing.html", context={"hostname":userdata.connectedtext(),
                                             "loggedin":loggedin,
                                             "blobfolder":blobfolder})


@get("/updateinstruments", exclude_from_auth=True, sync_to_thread=False )
def updateinstruments(request: Request) -> Template:
    "Updates the instruments on the main public page"
    iclient = userdata.get_indiclient()
    instruments = list(deviceobj for deviceobj in iclient.values() if deviceobj.enable)
    instruments.sort(key=lambda x: x.devicename)
    return HTMXTemplate(template_name="instruments.html", context={"instruments":instruments})


@get("/updatemessages", exclude_from_auth=True, sync_to_thread=False )
def updatemessages() -> Template:
    "Updates the messages on the main public page"
    iclient = userdata.get_indiclient()
    if iclient.stop:
        return HTMXTemplate(template_name="messages.html", context={"messages":["Error: client application has stopped"]})
    messages = list(iclient.messages)
    messagelist = list(userdata.localtimestring(t) + "  " + m for t,m in messages)
    messagelist.reverse()
    return HTMXTemplate(template_name="messages.html", context={"messages":messagelist})


@get("/login", exclude_from_auth=True, sync_to_thread=False )
def login_page(request: Request[str, str, State]) -> Template:
    "Render the login page"
    cookie = request.cookies.get('token')
    # log the user out
    if cookie:
        userdata.logout(request.cookies['token'])
    return Template("edit/login.html", context={"hostname":userdata.connectedtext()})


@post("/login", exclude_from_auth=True)
async def login(request: Request) -> Template|ClientRedirect:
    """This is a handler for the login post, in which the caller is setting their
       username and password into a form.
       Checks the user has logged in correctly, and if so creates a logged-in cookie
       for the caller and redirects the caller to / the root application page"""
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")
    # check these on the database of users, this checkuserpassword returns a userdata.UserInfo object
    # if the user exists, and the password is correct, otherwise it returns None
    userinfo = userdata.checkuserpassword(username, password)
    if userinfo is None:
        # sleep to force a time delay to annoy anyone trying to guess a password
        await asyncio.sleep(1.0)
        # unable to find a matching username/password
        # returns an 'Invalid' template which the htmx javascript
        # puts in the right place on the login page
        return HTMXTemplate(None,
                            template_str="<p id=\"result\" class=\"vanish\" style=\"color:red\">Invalid</p>")
    # The user checks out ok, create a cookie for this user and set redirect to the /,
    loggedincookie = userdata.createcookie(userinfo.user)
    # redirect with the loggedincookie
    response =  ClientRedirect("/")
    response.set_cookie(key = 'token', value=loggedincookie)
    return response


@get("/logout", sync_to_thread=False )
def logout(request: Request[str, str, State]) -> Template:
    "Logs the user out, and render the logout page"
    cookie = request.cookies.get('token')
    # log the user out
    if cookie:
        userdata.logout(request.cookies['token'])
    return Template("edit/loggedout.html", context={"hostname":userdata.connectedtext()})


@get("/blobs", sync_to_thread=False )
def blobs(request: Request[str, str, State]) -> Template:
    "Shows a page of blob files"
    iclient = userdata.get_indiclient()
    blobfolder = iclient.BLOBfolder
    if blobfolder:
        blobfiles = [f for f in listdir(blobfolder) if isfile(join(blobfolder, f))]
        blobfiles.sort()
    else:
        blobfiles = []
    admin = True if request.auth == "admin" else False
    context = {'blobfiles':blobfiles,
               'admin':admin}
    return Template("blobs.html", context=context)


@get("/getblob/{blobfile:str}", media_type="application/octet", sync_to_thread=False )
def getblob(blobfile:str, request: Request[str, str, State]) -> File:
    "Download a BLOB to the browser client"
    iclient = userdata.get_indiclient()
    blobfolder = iclient.BLOBfolder
    if not blobfolder:
        raise NotFoundException()
    blobpath = iclient.BLOBfolder / blobfile
    if not blobpath.is_file():
        raise NotFoundException()
    return File(
        path=blobpath,
        filename=blobfile
        )

@get("/delblob/{blobfile:str}", sync_to_thread=False )
def delblob(blobfile:str, request: Request[str, str, State]) -> ClientRefresh:
    "Deletes a blob"
    auth = request.auth
    if auth != "admin":
        raise NotAuthorizedException()
    iclient = userdata.get_indiclient()
    blobfolder = iclient.BLOBfolder
    if not blobfolder:
        raise NotFoundException()
    blobpath = iclient.BLOBfolder / blobfile
    if not blobpath.is_file():
        raise NotFoundException()
    remove(blobpath)
    return ClientRefresh()



@get(["/api", "/api/{device:str}", "/api/{device:str}/{vector:str}"], exclude_from_auth=True, sync_to_thread=False)
def api(device:str="", vector:str="") -> dict:
    iclient = userdata.get_indiclient()
    if not device:
        # return whole client dict
        shot = iclient.snapshot()
        return shot.dictdump()
    deviceobj = iclient.get(device)
    if deviceobj is None:
        return {}
    if vector:
        vectorobj = deviceobj.data.get(vector)
        if vectorobj is None:
            return {}
        shot = vectorobj.snapshot()
        return shot.dictdump()
    shot = deviceobj.snapshot()
    return shot.dictdump()


# This defines LoggedInAuth as middleware and also
# excludes certain paths from authentication.
# In this case it excludes all routes mounted at or under `/static*`
# This allows CSS and javascript libraries to be placed there, which
# therefore do not need authentication to be accessed
auth_mw = DefineMiddleware(LoggedInAuth, exclude="static")


def ipywebapp():
    # Initialize the Litestar app with a Mako template engine and register the routes
    iclient = userdata.get_indiclient()
    app = Litestar(
        route_handlers=[publicroot,
                        updateinstruments,
                        updatemessages,
                        notfound,
                        login_page,
                        login,
                        logout,
                        instruments,
                        messages,
                        blobs,
                        getblob,
                        delblob,
                        api,
                        edit.edit_router,     # This router in edit.py deals with routes below /edit
                        device.device_router, # This router in device.py deals with routes below /device
                        vector.vector_router, # This router in vector.py deals with routes below /vector
                        setup.setup_router,   # This router in setup.py deals with routes below /setup
                        create_static_files_router(path="/static", directories=[STATICFILES]),
                       ],
        exception_handlers={ NotAuthorizedException: gotologin_error_handler, NotFoundException: gotonotfound_error_handler},
        plugins=[HTMXPlugin()],
        middleware=[auth_mw],
        template_config=TemplateConfig(directory=TEMPLATEFILES,
                                       engine=MakoTemplateEngine,
                                      ),
        on_startup=[do_startup],
        on_shutdown=[do_shutdown],
        openapi_config=None
        )
    return app
