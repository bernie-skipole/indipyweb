"""
Handles all routes beneath /edit
"""


from litestar import Litestar, get, post, Request, Router
from litestar.plugins.htmx import HTMXTemplate, ClientRedirect
from litestar.response import Template, Redirect
from litestar.datastructures import State

from litestar.response import ServerSentEvent, ServerSentEventMessage

from . import userdata


##################

class TableChange:
    """Iterate whenever a user table change happens."""

    def __aiter__(self):
        return self

    async def __anext__(self):
        "Whenever there is a new table event, return a ServerSentEventMessage"
        await userdata.TABLE_EVENT.wait()
        return ServerSentEventMessage(event="tablechange")


# SSE Handler
@get(path="/tablechange", exclude_from_auth=True, sync_to_thread=False)
def tablechange(request: Request[str, str, State]) -> ServerSentEvent:
    return ServerSentEvent(TableChange())


#################



@get("/")
async def edit(request: Request[str, str, State]) -> Template|ClientRedirect|Redirect:
    """This allows a user to edit his/her password, or delete themself from the system
       If the user is an admin user, further facilities to add/delete/reset other users
       are available"""
    user = request.user
    auth = request.auth
    uinfo = userdata.getuserinfo(user)
    if uinfo is None:
        # user not recognised, this should never happen, but in the event it does
        if request.htmx:
            return ClientRedirect("/login")
        return Redirect("/login")
    # admin and user auth levels get different templates
    if auth != "admin":
        return Template(template_name="edit/user/useredit.html", context={"user": user,
                                                                          "fullname":uinfo.fullname,
                                                                          "hostname":userdata.connectedtext() })
    # So the user is an administrator, show further buttons
    # plus a table of users
    thispage = 0
    context = userdata.userlist(thispage)
    if context is None:
        if request.htmx:
            return ClientRedirect("/login")
        return Redirect("/login")
    # add further items to this context dictionary
    context["user"] = user
    context["fullname"] = uinfo.fullname
    context["hostname"] = userdata.connectedtext()
    return Template(template_name="edit/admin/adminedit.html", context=context)


@post("/adminfullname")
async def adminfullname(request: Request[str, str, State]) -> Template:
    "An administrator is changing his own full name"
    if request.auth != "admin":
        return logout(request)
    user = request.user
    form_data = await request.form()
    newfullname = form_data.get("fullname")
    message = userdata.newfullname(user, newfullname)
    if message:
        return HTMXTemplate(None,
                        template_str=f"<p id=\"nameconfirm\" class=\"vanish\" style=\"color:red\">Invalid. {message}</p>")
    userdata.TABLE_EVENT.set()
    userdata.TABLE_EVENT.clear()
    return HTMXTemplate(None,
                        template_str="<p id=\"nameconfirm\" style=\"color:green\" class=\"vanish\">Success! The name has changed</p>")



@post("/userfullname")
async def userfullname(request: Request[str, str, State]) -> Template:
    "An administrator is changing someone else's name, hence get username from the form"
    if request.auth != "admin":
        return logout(request)
    form_data = await request.form()
    username = form_data.get("username")
    newfullname = form_data.get("fullname")
    message = userdata.newfullname(username, newfullname)
    if message:
        return HTMXTemplate(None,
                        template_str=f"<p id=\"nameconfirm\" class=\"vanish\" style=\"color:red\">Invalid. {message}</p>")
    userdata.TABLE_EVENT.set()
    userdata.TABLE_EVENT.clear()
    return HTMXTemplate(None,
                        template_str="<p id=\"nameconfirm\" style=\"color:green\" class=\"vanish\">Success! The name has changed</p>")



@post("/changeuserpwd")
async def changeuserpwd(request: Request[str, str, State]) -> Template:
    "An administrator is changing someone else's password, hence get username from the form"
    if request.auth != "admin":
        return logout(request)
    form_data = await request.form()
    username = form_data.get("username")
    password1 = form_data.get("password1")
    password2 = form_data.get("password2")
    if password1 != password2:
        return HTMXTemplate(None,
                        template_str="<p id=\"pwdconfirm\" class=\"vanish\" style=\"color:red\">Invalid. Passwords do not match!</p>")
    message = userdata.changepassword(username, password1)
    if message:
        return HTMXTemplate(None,
                        template_str=f"<p id=\"pwdconfirm\" class=\"vanish\" style=\"color:red\">Invalid. {message}</p>")
    else:
        return HTMXTemplate(None,
                        template_str="<p id=\"pwdconfirm\" style=\"color:green\" class=\"vanish\">Success! The password has changed</p>")



######### Called by a user to edit himself

@post("/changepwd")
async def changepwd(request: Request[str, str, State]) -> Template:
    "A user is changing his own password"
    user = request.user
    form_data = await request.form()
    oldpassword = form_data.get("oldpassword")
    password1 = form_data.get("password1")
    password2 = form_data.get("password2")
    # check old password
    userinfo = userdata.checkuserpassword(user, oldpassword)
    if userinfo is None:
        # invalid old password
        return HTMXTemplate(None,
                        template_str="<p id=\"pwdconfirm\" class=\"vanish\" style=\"color:red\">Invalid. Incorrect old password!</p>")
    if password1 != password2:
        return HTMXTemplate(None,
                        template_str="<p id=\"pwdconfirm\" class=\"vanish\" style=\"color:red\">Invalid. Passwords do not match!</p>")
    message = userdata.changepassword(user, password1)
    if message:
        return HTMXTemplate(None,
                        template_str=f"<p id=\"pwdconfirm\" class=\"vanish\" style=\"color:red\">Invalid. {message}</p>")
    else:
        return HTMXTemplate(None,
                        template_str="<p id=\"pwdconfirm\" style=\"color:green\" class=\"vanish\">Success! Your password has changed</p>")


@post("/fullname")
async def fullname(request: Request[str, str, State]) -> Template:
    "A user is changing his own full name"
    user = request.user
    form_data = await request.form()
    newfullname = form_data.get("fullname")
    message = userdata.newfullname(user, newfullname)
    if message:
        return HTMXTemplate(None,
                        template_str=f"<p id=\"nameconfirm\" class=\"vanish\" style=\"color:red\">Invalid. {message}</p>")
    # name changed
    userdata.TABLE_EVENT.set()
    userdata.TABLE_EVENT.clear()
    return HTMXTemplate(None,
                 template_str="<p id=\"nameconfirm\" class=\"vanish\" style=\"color:green\">Success! Your full name has changed</p>")

@get("/delete", sync_to_thread=False)
def delete(request: Request[str, str, State]) -> Template|ClientRedirect:
    "A user is deleting himself"
    user = request.user
    message = userdata.deluser(user)
    if message:
        return HTMXTemplate(None,
                        template_str=f"Failed. {message}")
    userdata.TABLE_EVENT.set()
    userdata.TABLE_EVENT.clear()
    return ClientRedirect(f"/edit/deleted/{user}")


@get("/deleted/{user:str}", exclude_from_auth=True, sync_to_thread=False)
def deleted(user:str) -> Template:
    "Render the deleted page, showing the users name, with account deleted message"
    return Template(template_name="edit/user/userdeleted.html", context={"user": user,
                                                                         "hostname":userdata.connectedtext()})

##################################################


@post("/userdelete")
async def userdelete(request: Request[str, str, State]) -> Template|ClientRedirect:
    "An administrator is deleting someone from the table"
    if request.auth != "admin":
        return logout(request)
    form_data = await request.form()
    username = form_data.get("username").strip()
    message = userdata.deluser(username)
    if message:
        return HTMXTemplate(None,
                        template_str=f"Failed. {message}")
    userdata.TABLE_EVENT.set()
    userdata.TABLE_EVENT.clear()
    if username == request.user:
        return ClientRedirect(f"/edit/deleted/{username}")
    return HTMXTemplate(template_name="edit/admin/optionsdelete.html", re_target="#editoptions", context={'user': username})


def logout(request: Request[str, str, State]) -> ClientRedirect|Redirect:
    "Logs the session out and redirects to the login page"
    if 'token' in request.cookies:
        # log the user out
        userdata.logout(request.cookies['token'])
    if request.htmx:
        return ClientRedirect("/login")
    return Redirect("/login")


@post("/newuser")
async def newuser(request: Request[str, str, State]) -> Template|ClientRedirect|Redirect:
    "Create a new user"
    if request.auth != "admin":
        return logout(request)
    form_data = await request.form()
    username = form_data.get("username").strip()
    password = form_data.get("password").strip()
    authlevel = form_data.get("authlevel").strip().lower()
    fullname = form_data.get("fullname").strip()
    message = userdata.adduser(username, password, authlevel, fullname)
    if message:
        return HTMXTemplate(None,
                        template_str=f"<p id=\"newuserconfirm\" class=\"vanish\" style=\"color:red\">Invalid. {message}</p>")
    userdata.TABLE_EVENT.set()
    userdata.TABLE_EVENT.clear()
    return HTMXTemplate(None,
                   template_str="<p id=\"newuserconfirm\" class=\"vanish\" style=\"color:green\">Success! New user added</p>")




@get("/edituser/{user:str}", sync_to_thread=False)
def edituser(user:str, request: Request[str, str, State]) -> Template|Redirect:
    """A user to edit has been selected from the table"""
    if request.auth != "admin":
        return logout(request)
    uinfo = userdata.getuserinfo(user)
    if uinfo is None:
        return Redirect("/")   ### no such user
    # add further items to this context dictionary
    context = {"user": user, "fullname": uinfo.fullname, "hostname":userdata.connectedtext()}
    if user == request.user:
        # chosen yourself from the table, options to edit yourself are displayed
        return HTMXTemplate(template_name="edit/admin/editoptions.html", context=context)
    # Options to edit a user are chosen
    return HTMXTemplate(template_name="edit/admin/edituser.html", context=context)


@get("/tableupdate", sync_to_thread=False)
def tableupdate(thispage:int, request: Request[str, str, State]) -> Template|ClientRedirect|Redirect:
    "Update the table of users"
    if request.auth != "admin":
        return logout(request)
    context = userdata.userlist(thispage)
    if context is None:
        if request.htmx:
            return ClientRedirect("/login")
        return Redirect("/login")
    return Template(template_name="edit/admin/listusers.html", context=context)

@get("/prevpage", sync_to_thread=False)
def prevpage(thispage:int, request: Request[str, str, State]) -> Template|ClientRedirect|Redirect:
    "Handle the admin user requesting a previouse page of the user table"
    if request.auth != "admin":
        return logout(request)
    context = userdata.userlist(thispage, "-")
    if context is None:
        if request.htmx:
            return ClientRedirect("/login")
        return Redirect("/login")
    return Template(template_name="edit/admin/listusers.html", context=context)


@get("/nextpage", sync_to_thread=False)
def nextpage(thispage:int, request: Request[str, str, State]) -> Template|ClientRedirect|Redirect:
    "Handle the admin user requesting the next page of the user table"
    if request.auth != "admin":
        return logout(request)
    context = userdata.userlist(thispage, "+")
    if context is None:
        if request.htmx:
            return ClientRedirect("/login")
        return Redirect("/login")
    return Template(template_name="edit/admin/listusers.html", context=context)





edit_router = Router(path="/edit", route_handlers=[edit,
                                                   fullname,
                                                   adminfullname,
                                                   userfullname,
                                                   changepwd,
                                                   changeuserpwd,
                                                   delete,
                                                   deleted,
                                                   userdelete,
                                                   newuser,
                                                   prevpage,
                                                   nextpage,
                                                   edituser,
                                                   tablechange,
                                                   tableupdate
                                                  ])
