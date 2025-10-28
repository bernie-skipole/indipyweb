"""
Handles all routes beneath /setup
"""


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


@get("/")
async def setup(request: Request[str, str, State]) -> Template:
    "Get the setup page"
    if request.auth != "admin":
        return logout(request)
    # get parameters from database and set up in context
    context = {"webhost":userdata.getconfig("host")}
    return Template(template_name="setup/setuppage.html", context=context)


@get("/backupdb")
async def backupdb(request: Request[str, str, State]) -> Template|Redirect:
    """This creates a backup file of the user database"""
    if request.auth != "admin":
        return logout(request)
    # userdata.dbbackup() actuall does the work
    filename = userdata.dbbackup()
    if filename:
        return HTMXTemplate(None,
                        template_str=f"<p id=\"backupfile\" style=\"color:green\" class=\"w3-animate-right\">Backup file created: {filename}</p>")
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
                        template_str=f"<p id=\"webhostconfirm\" class=\"vanish\" style=\"color:red\">Invalid host name/IP</p>")
    userdata.setconfig("host", webhost)
    return HTMXTemplate(None,
                 template_str=f"<p id=\"webhostconfirm\" class=\"vanish\" style=\"color:green\">Host changed to {webhost}</p>")



setup_router = Router(path="/setup", route_handlers=[setup,
                                                     backupdb,
                                                     webhost
                                                    ])
