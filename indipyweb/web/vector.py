"""
Handles all routes beneath /vector
"""

import asyncio, os

from asyncio.exceptions import TimeoutError

from typing import Annotated

from litestar import Litestar, get, post, Request, Router, MediaType
from litestar.plugins.htmx import HTMXTemplate, ClientRedirect, ClientRefresh
from litestar.response import Template, Redirect
from litestar.datastructures import State, UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import ServerSentEvent, ServerSentEventMessage

from .userdata import localtimestring, get_indiclient, getuserauth, get_vectorobj




@get("/update/{vectorid:int}", exclude_from_auth=True, sync_to_thread=False)
def update(vectorid:int, request: Request[str, str, State]) -> Template|ClientRedirect|ClientRefresh:
    "Update vector"
    iclient = get_indiclient()
    # check valid vector
    vectorobj = get_vectorobj(vectorid)
    if vectorobj is None:
        return ClientRedirect("/")
    # Check if user is looged in
    loggedin = False
    cookie = request.cookies.get('token', '')
    if cookie:
        userauth = getuserauth(cookie)
        if userauth is not None:
            loggedin = True
    if vectorobj.user_string:
        # This is not a full update, just an update of the result and state fields
        return HTMXTemplate(template_name="vector/result.html",
                            re_target=f"#result_{vectorobj.itemid}",
                            context={"state":f"{vectorobj.state}",
                                     "stateid":f"state_{vectorobj.itemid}",
                                     "timestamp":localtimestring(vectorobj.timestamp),
                                     "result":vectorobj.user_string})
    # have to return a vector html template here
    return HTMXTemplate(template_name="vector/getvector.html", context={"vectorobj":vectorobj,
                                                                        "timestamp":localtimestring(vectorobj.timestamp),
                                                                        "loggedin":loggedin,
                                                                        "blobfolder":str(iclient.BLOBfolder),
                                                                        "message_timestamp":localtimestring(vectorobj.message_timestamp)})


@post("/submit/{vectorid:int}")
async def submit(vectorid:int, request: Request[str, str, State]) -> Template|ClientRedirect|ClientRefresh:
    # check valid vector
    iclient = get_indiclient()
    # check valid vector
    vectorobj = get_vectorobj(vectorid)
    if vectorobj is None:
        return ClientRedirect("/")


    if vectorobj.perm == "ro":
        return HTMXTemplate(None, template_str="<p>INVALID: This is a Read Only vector!</p>")

    form_data = await request.form()

    # deal with switch vectors
    if vectorobj.vectortype  == "SwitchVector":
        members = {}
        oncount = 0
        for mbr in vectorobj.members().values():
            fm = f"member_{mbr.itemid}"
            if fm in form_data:
                members[mbr.name] = "On"
                oncount += 1
            else:
                members[mbr.name] = "Off"
        if vectorobj.rule != 'AnyOfMany':
            # 'OneOfMany', and 'AtMostOne' rules have a max oncount of 1
            if vectorobj.rule == "OneOfMany" and oncount != 1:
                return HTMXTemplate(template_name="vector/result.html", context={"state":"Alert",
                                                                                 "stateid":f"state_{vectorobj.itemid}",
                                                                                 "timestamp":localtimestring(),
                                                                                 "result":"OneOfMany rule requires one switch only to be On"})
            if vectorobj.rule == "AtMostOne" and oncount > 1:
                return HTMXTemplate(template_name="vector/result.html", context={"state":"Alert",
                                                                                 "stateid":f"state_{vectorobj.itemid}",
                                                                                 "timestamp":localtimestring(),
                                                                                 "result":"AtMostOne rule requires no more than one On switch"})
    else:
        # text and number members
        members = {}
        for mbr in vectorobj.members().values():
            fm = f"member_{mbr.itemid}"
            if fm in form_data:
                members[mbr.name] = form_data[fm]
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
        return HTMXTemplate(template_name="vector/result.html", context={"state":"Alert",
                                                                         "stateid":f"state_{vectorobj.itemid}",
                                                                         "timestamp":localtimestring(),
                                                                         "result":"Unable to parse number value"})


    # and send the vector
    await iclient.send_newVector(vectorobj.devicename, vectorobj.name, members=members)
    return HTMXTemplate(template_name="vector/result.html", context={"state":"Busy",
                                                                     "stateid":f"state_{vectorobj.itemid}",
                                                                     "timestamp":localtimestring(),
                                                                     "result":"Vector changes sent"})



@post(path="/blobsend/{vectorid:int}/{memberid:int}", media_type=MediaType.TEXT)
async def blobsend(
    vectorid:int, memberid:int,
    request: Request[str, str, State],
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)]) -> Template|ClientRedirect|ClientRefresh:

    # check valid vector
    iclient = get_indiclient()
    # check valid vector
    vectorobj = get_vectorobj(vectorid)
    if vectorobj is None:
        return ClientRedirect("/")

    if vectorobj.perm == "ro":
        return HTMXTemplate(None, template_str="<p>INVALID: This is a Read Only vector!</p>")

    memberobj = None

    for mbr in vectorobj.members().values():
        if mbr.itemid == memberid:
            memberobj = mbr
            break
    if memberobj is None:
        return ClientRedirect("/")

    content = await data.read()
    filename = data.filename

    memberobj.user_string = f"File {filename} sent"

    name, extension = os.path.splitext(filename)

    # memberdict of {membername:(value, blobsize, blobformat)}
    await vectorobj.send_newBLOBVector(members={memberobj.name:(content, 0, extension)})

    return HTMXTemplate(template_name="vector/result.html", context={"state":"Busy",
                                                                     "stateid":f"state_{vectorobj.itemid}",
                                                                     "timestamp":localtimestring(),
                                                                     "result":f"File {filename} sent"})




vector_router = Router(path="/vector", route_handlers=[update, submit, blobsend])
