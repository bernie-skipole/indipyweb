"""
Handles all routes beneath /edit
"""


from litestar import Litestar, get, post, Request, Router
from litestar.plugins.htmx import HTMXTemplate, ClientRedirect
from litestar.response import Template, Redirect
from litestar.datastructures import State

from . import userdata

from ..register import indihostport


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
        return Template(template_name="edit/youedit.html", context={"user": user,
                                                                    "fullname":uinfo.fullname,
                                                                    "hostname":indihostport()})
    context = userdata.userlist(request.cookies.get('token', ''))
    if context is None:
        if request.htmx:
            return ClientRedirect("/login")
        return Redirect("/login")
    # add further items to this context dictionary
    context["user"] = user
    context["fullname"] = uinfo.fullname
    context["hostname"] = indihostport()
    return Template(template_name="edit/adminedit.html", context=context)


@post("/fullname")
async def fullname(request: Request[str, str, State]) -> Template|ClientRedirect|Redirect:
    "A user is changing his own full name"
    user = request.user
    form_data = await request.form()
    newfullname = form_data.get("fullname")
    message = userdata.newfullname(user, newfullname)
    if message:
        return HTMXTemplate(None,
                        template_str=f"<p id=\"nameconfirm\" class=\"w3-animate-right\" style=\"color:red\">Invalid. {message}</p>")
    # name changed
    if request.auth != "admin":
        return HTMXTemplate(None,
                        template_str="<p id=\"nameconfirm\" class=\"w3-animate-right\" style=\"color:green\">Success! Your full name has changed</p>")
    # Update the user list
    context = userdata.userlist(request.cookies.get('token', ''))
    if context is None:
        if request.htmx:
            return ClientRedirect("/login")
        return Redirect("/login")
    return HTMXTemplate(template_name="edit/namechanged.html", context=context)



@post("/userfullname")
async def userfullname(request: Request[str, str, State]) -> Template|ClientRedirect|Redirect:
    "An administrator is changing someone else's name, hence get username from the form"
    if request.auth != "admin":
        return logout(request)
    form_data = await request.form()
    username = form_data.get("username")
    newfullname = form_data.get("fullname")
    message = userdata.newfullname(username, newfullname)
    if message:
        return HTMXTemplate(None,
                        template_str=f"<p id=\"nameconfirm\" class=\"w3-animate-right\" style=\"color:red\">Invalid. {message}</p>")
    # Update the user list
    context = userdata.userlist(request.cookies.get('token', ''))
    if context is None:
        if request.htmx:
            return ClientRedirect("/login")
        return Redirect("/login")
    return HTMXTemplate(template_name="edit/namechanged.html", context=context)



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
                        template_str="<p id=\"pwdconfirm\" class=\"w3-animate-right\" style=\"color:red\">Invalid. Incorrect old password!</p>")
    if password1 != password2:
        return HTMXTemplate(None,
                        template_str="<p id=\"pwdconfirm\" class=\"w3-animate-right\" style=\"color:red\">Invalid. Passwords do not match!</p>")
    message = userdata.changepassword(user, password1)
    if message:
        return HTMXTemplate(None,
                        template_str=f"<p id=\"pwdconfirm\" class=\"w3-animate-right\" style=\"color:red\">Invalid. {message}</p>")
    else:
        return HTMXTemplate(None,
                        template_str="<p id=\"pwdconfirm\" style=\"color:green\" class=\"w3-animate-right\">Success! Your password has changed</p>")


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
                        template_str="<p id=\"pwdconfirm\" class=\"w3-animate-right\" style=\"color:red\">Invalid. Passwords do not match!</p>")
    message = userdata.changepassword(username, password1)
    if message:
        return HTMXTemplate(None,
                        template_str=f"<p id=\"pwdconfirm\" class=\"w3-animate-right\" style=\"color:red\">Invalid. {message}</p>")
    else:
        return HTMXTemplate(None,
                        template_str="<p id=\"pwdconfirm\" style=\"color:green\" class=\"w3-animate-right\">Success! The password has changed</p>")


@post("/delete")
async def delete(request: Request[str, str, State]) -> Template|ClientRedirect:
    "A user is deleting himself"
    user = request.user
    message = userdata.deluser(user)
    if message:
        return HTMXTemplate(None,
                        template_str=f"Failed. {message}")
    return ClientRedirect(f"/edit/deleted/{user}")


@get("/deleted/{user:str}", exclude_from_auth=True)
async def deleted(user:str) -> Template:
    "Render the deleted page, showing the users name"
    return Template(template_name="edit/deleted.html", context={"user": user, "hostname":indihostport()})


@post("/userdelete")
async def userdelete(request: Request[str, str, State]) -> Template|ClientRedirect:
    "An administrator is deleting someone else, hence get username from the form"
    if request.auth != "admin":
        return logout(request)
    form_data = await request.form()
    username = form_data.get("username").strip()
    message = userdata.deluser(username)
    if message:
        return HTMXTemplate(None,
                        template_str=f"Failed. {message}")
    if username == request.user:
        return ClientRedirect(f"/edit/deleted/{username}")
    return ClientRedirect(f"/edit/userdeleted/{username}")


@get("/userdeleted/{user:str}")
async def userdeleted(user:str, request: Request[str, str, State]) -> Template|ClientRedirect:
    "Having deleted a user, give the reply and update the table of users"
    if request.auth != "admin":
        return logout(request)
    username = user.strip()
    context = userdata.userlist(request.cookies.get('token', ''))
    if context is None:
        if request.htmx:
            return ClientRedirect("/login")
        return Redirect("/login")
    context['user'] = username
    context["hostname"] = indihostport()
    return Template(template_name="edit/userdeleted.html", context=context)


def logout(request: Request[str, str, State]) -> ClientRedirect|Redirect:
    "Logs the session, from cookie, out and redirects to the login page"
    if 'token' in request.cookies:
        # log the user out
        userdata.logout(request.cookies['token'])
    if request.htmx:
        return ClientRedirect("/login")
    return Redirect("/login")


@post("/newuser")
async def newuser(request: Request[str, str, State]) -> Template|ClientRedirect|Redirect:
    "Create a new user, and on success update the table of users"
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
                        template_str=f"<p id=\"newuserconfirm\" class=\"w3-animate-right\" style=\"color:red\">Invalid. {message}</p>")
    # New user added, so update the user list
    context = userdata.userlist(request.cookies.get('token', ''))
    if context is None:
        if request.htmx:
            return ClientRedirect("/login")
        return Redirect("/login")
    return HTMXTemplate(template_name="edit/newuser.html", context=context)


@get("/prevpage")
async def prevpage(request: Request[str, str, State]) -> Template|ClientRedirect|Redirect:
    "Handle the admin user requesting a previouse page of the user table"
    if request.auth != "admin":
        return logout(request)
    context = userdata.userlist(request.cookies.get('token', ''), "-")
    if context is None:
        if request.htmx:
            return ClientRedirect("/login")
        return Redirect("/login")
    return Template(template_name="edit/listusers.html", context=context)


@get("/nextpage")
async def nextpage(request: Request[str, str, State]) -> Template|ClientRedirect|Redirect:
    "Handle the admin user requesting the next page of the user table"
    if request.auth != "admin":
        return logout(request)
    context = userdata.userlist(request.cookies.get('token', ''), "+")
    if context is None:
        if request.htmx:
            return ClientRedirect("/login")
        return Redirect("/login")
    return Template(template_name="edit/listusers.html", context=context)


@get("/edituser/{user:str}")
async def edituser(user:str, request: Request[str, str, State]) -> Template|Redirect:
    """A user to edit has been selected from the table"""
    if request.auth != "admin":
        return logout(request)
    uinfo = userdata.getuserinfo(user)
    if uinfo is None:
        return Redirect("/")   ### no such user
    context = userdata.userlist(request.cookies.get('token', ''))
    if context is None:
        return Redirect("/")
    # add further items to this context dictionary
    context["user"] = user
    context["fullname"] = uinfo.fullname
    context["hostname"] = indihostport()
    if user == request.user:
        # chosen yourself from the table
        return Template(template_name="edit/adminedit.html", context=context)
    return Template(template_name="edit/edituser.html", context=context)


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


edit_router = Router(path="/edit", route_handlers=[edit,
                                                   fullname,
                                                   userfullname,
                                                   changepwd,
                                                   changeuserpwd,
                                                   delete,
                                                   deleted,
                                                   userdelete,
                                                   userdeleted,
                                                   newuser,
                                                   prevpage,
                                                   nextpage,
                                                   edituser,
                                                   backupdb
                                                  ])
