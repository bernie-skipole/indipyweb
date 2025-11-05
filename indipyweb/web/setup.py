"""
Handles all routes beneath /setup
"""

import pathlib

from litestar import Litestar, get, post, Request, Router
from litestar.plugins.htmx import HTMXTemplate, ClientRedirect
from litestar.response import Template, Redirect
from litestar.datastructures import State

from litestar.response import ServerSentEvent, ServerSentEventMessage

from . import userdata


def logout(request: Request[str, str, State]) -> ClientRedirect|Redirect:
    "Logs the session out and redirects to the login page"
    if 'token' in request.cookies:
        # log the user out
        userdata.logout(request.cookies['token'])
    if request.htmx:
        return ClientRedirect("/login")
    return Redirect("/login")


@get("/", sync_to_thread=False)
def setup(request: Request[str, str, State]) -> Template:
    "Get the setup page"
    if request.auth != "admin":
        return logout(request)

    currentblobfolder = userdata.getconfig("blobfolder")
    if currentblobfolder is None:
        currentblobfolder = ""
    storedblobfolder = userdata.get_stored_item('blobfolder')
    if storedblobfolder is None:
        storedblobfolder = ""

    # get parameters from database and set up in context
    context = {"currentwebhost":userdata.getconfig("host"),
               "storedwebhost":userdata.get_stored_item('host'),
               "currentwebport":userdata.getconfig("port"),
               "storedwebport":userdata.get_stored_item('port'),
               "currentindihost":userdata.getconfig("indihost"),
               "storedindihost":userdata.get_stored_item('indihost'),
               "currentindiport":userdata.getconfig("indiport"),
               "storedindiport":userdata.get_stored_item('indiport'),
               "currentblobfolder":currentblobfolder,
               "storedblobfolder":storedblobfolder
              }
    return Template(template_name="setup/setuppage.html", context=context)


@get("/backupdb", sync_to_thread=False)
def backupdb(request: Request[str, str, State]) -> Template|Redirect:
    """This creates a backup file of the user database"""
    if request.auth != "admin":
        return logout(request)
    # userdata.dbbackup() actuall does the work
    filename = userdata.dbbackup()
    if filename:
        return HTMXTemplate(None,
                        template_str="<p id=\"backupfile\" style=\"color:green\" class=\"w3-animate-right\">Backup file created: ${filename|h}</p>", context={"filename":filename})
    return HTMXTemplate(None,
                        template_str="<p id=\"backupfile\"  style=\"color:red\" class=\"w3-animate-right\">Backup failed!</p>")


@post("/webhost")
async def webhost(request: Request[str, str, State]) -> Template:
    "An admin is setting the webhost"
    if request.auth != "admin":
        return logout(request)
    form_data = await request.form()
    webhost = form_data.get("webhostinput")
    if not webhost:   # further checks required here
        return HTMXTemplate(None,
                        template_str="<p id=\"webhostconfirm\" class=\"vanish\" style=\"color:red\">Invalid host name/IP</p>")
    userdata.set_stored_item('host', webhost)
    return HTMXTemplate(template_name="setup/webhost.html", context={"storedwebhost":webhost})



@post("/webport")
async def webport(request: Request[str, str, State]) -> Template:
    "An admin is setting the webport"
    if request.auth != "admin":
        return logout(request)
    form_data = await request.form()
    webport = form_data.get("webportinput")
    try:
        webport = int(webport)
    except Exception:
        return HTMXTemplate(None,
                        template_str="<p id=\"webportconfirm\" class=\"vanish\" style=\"color:red\">Invalid port</p>")
    userdata.set_stored_item('port', webport)
    return HTMXTemplate(template_name="setup/webport.html", context={"storedwebport":str(webport)})


@post("/indihost")
async def indihost(request: Request[str, str, State]) -> Template:
    "An admin is setting the INDI server hostname"
    if request.auth != "admin":
        return logout(request)
    form_data = await request.form()
    indihost = form_data.get("indihostinput")
    if not indihost:   # further checks required here
        return HTMXTemplate(None,
                        template_str="<p id=\"indihostconfirm\" class=\"vanish\" style=\"color:red\">Invalid host name/IP</p>")
    userdata.set_stored_item('indihost', indihost)
    return HTMXTemplate(template_name="setup/indihost.html", context={"storedindihost":indihost})


@post("/indiport")
async def indiport(request: Request[str, str, State]) -> Template:
    "An admin is setting the INDI server port"
    if request.auth != "admin":
        return logout(request)
    form_data = await request.form()
    indiport = form_data.get("indiportinput")
    try:
        indiport = int(indiport)
    except Exception:
        return HTMXTemplate(None,
                        template_str="<p id=\"indiportconfirm\" class=\"vanish\" style=\"color:red\">Invalid port</p>")
    userdata.set_stored_item('indiport', indiport)
    return HTMXTemplate(template_name="setup/indiport.html", context={"storedindiport":str(indiport)})


@post("/blobfolder")
async def blobfolder(request: Request[str, str, State]) -> Template:
    "An admin is setting the BLOB folder"
    if request.auth != "admin":
        return logout(request)
    form_data = await request.form()
    blobfolder = form_data.get("blobfolderinput")
    if blobfolder:
        try:
            blobpath = pathlib.Path(blobfolder).expanduser().resolve()
        except Exception:
            return HTMXTemplate(None,
                    template_str="<p id=\"blobfolderconfirm\" class=\"vanish\" style=\"color:red\">Invalid folder</p>")
        else:
            if not blobpath.is_dir():
                return HTMXTemplate(None,
                    template_str="<p id=\"blobfolderconfirm\" class=\"vanish\" style=\"color:red\">Folder does not exist</p>")
        blobfolder = str(blobpath)
    if not blobfolder:
        userdata.set_stored_item('blobfolder', None)
        blobfolder = ""
    else:
        userdata.set_stored_item('blobfolder', blobfolder)
    return HTMXTemplate(template_name="setup/blobfolder.html", context={"storedblobfolder":blobfolder})



setup_router = Router(path="/setup", route_handlers=[setup,
                                                     backupdb,
                                                     webhost,
                                                     webport,
                                                     indihost,
                                                     indiport,
                                                     blobfolder
                                                    ])
