"""This module defines users and passwords on a database,
   on first being imported if the file users.sqlite does not exist, an
   sqlite database will be created with the single user 'admin' and password 'password!'
   You should immediately log in as this user and change the password.
   """

import sqlite3, os, time, asyncio

from datetime import datetime, timezone

from hashlib import scrypt

from secrets import token_urlsafe

from pathlib import Path

from dataclasses import dataclass

from functools import lru_cache


_PARAMETERS = {
                "host":None,
                "port":None,
                "indihost":"localhost",
                "indiport":7624,
                "blobfolder":None,
                "indiclient":None,
                "dbfolder":None,
                "dbase":None,
                "runclient":None
              }

DEFINE_EVENT = asyncio.Event()

MESSAGE_EVENT = asyncio.Event()

DEVICE_EVENTS = {}


# This event is set whenever the table of users needs updating
TABLE_EVENT = asyncio.Event()

# Dictionary of cookie:userauth, built as cookies are created
# The cookie is a random string sent as the cookie token
USERCOOKIES = {}

# seconds after which an idle user will be logged out (set to 1 hour here)
IDLETIMEOUT = 3600


# UserInfo objects are generally populated from the database, or LRU cache, and used
# to pass a bundle of user information. Since a cache is used the objects are usually static,
# and if changed, the cache must be cleared.

@dataclass
class UserInfo():
    "Class used to hold user details"
    user:str
    auth:str
    fullname:str


# UserAuth objects are created as users are logged in and stored in the USERCOOKIES
# dictionary, with cookies as the dictionary keys.
# These store the user associated with the cookie


@dataclass
class UserAuth():
    "Class used to hold a logged in user details"
    user:str             # The username
    time:float           # time used for timing out the session


########## Functions to set and read _PARAMETERS and events


def get_indiclient():
    global _PARAMETERS
    return _PARAMETERS["indiclient"]


def get_deviceobj(deviceid):
    "Returns device object, or None if not found"
    global _PARAMETERS
    iclient = _PARAMETERS["indiclient"]
    if iclient.stop:
        return
    if not iclient.connected:
        return
    if not deviceid:
        return
    for deviceobj in iclient.values():
        if deviceobj.itemid == deviceid:
            if not deviceobj.enable:
                return
            return deviceobj

def get_vectorobj(vectorid, deviceid=None):
    "Returns vector object, or None if not found"
    global _PARAMETERS
    iclient = _PARAMETERS["indiclient"]
    if iclient.stop:
        return
    if not iclient.connected:
        return
    if not vectorid:
        return
    if deviceid:
        deviceobj = get_deviceobj(deviceid)
        if not deviceobj:
            return
        for vectorobj in deviceobj.values():
            if vectorobj.itemid == vectorid:
                if vectorobj.enable:
                    return vectorobj
                return
    else:
        for deviceobj in iclient.values():
            for vectorobj in deviceobj.values():
                if vectorobj.itemid == vectorid:
                    if vectorobj.enable:
                        return vectorobj
                    return



def getconfig(parameter):
    return _PARAMETERS.get(parameter)


def setconfig(parameter, value):
    global _PARAMETERS
    if parameter in _PARAMETERS:
        _PARAMETERS[parameter] = value


def indihostport():
    "Returns the string 'hostname:port' for the INDI server"
    return f"{_PARAMETERS['indihost']}:{_PARAMETERS['indiport']}"


def connectedtext():
    global _PARAMETERS
    iclient = _PARAMETERS["indiclient"]
    if iclient.connected:
        return f"Connected to INDI service at: {_PARAMETERS['indihost']}:{_PARAMETERS['indiport']}"
    else:
        return f"Connecting to INDI service at: {_PARAMETERS['indihost']}:{_PARAMETERS['indiport']}"


def localtimestring(t=None):
    "Return a string of the local time (not date)"
    if t is None:
        t = datetime.now(tz=timezone.utc)
    localtime = t.astimezone(tz=None)
    # convert microsecond to integer between 0 and 100
    ms = localtime.microsecond//10000
    return f"{localtime.strftime('%H:%M:%S')}.{ms:0>2d}"


def get_device_event(devicename):
    global DEVICE_EVENTS
    if devicename not in DEVICE_EVENTS:
        DEVICE_EVENTS[devicename] = asyncio.Event()
    return DEVICE_EVENTS[devicename]



def get_stored_item(item):
    "Gets stored item from the database"
    con = sqlite3.connect(_PARAMETERS["dbase"])
    cur = con.cursor()
    if item == "host":
        cur.execute("SELECT host FROM parameters")
    elif item == "port":
        cur.execute("SELECT port FROM parameters")
    elif item == "indihost":
        cur.execute("SELECT indihost FROM parameters")
    elif item == "indiport":
        cur.execute("SELECT indiport FROM parameters")
    elif item == "blobfolder":
        cur.execute("SELECT blobfolder FROM parameters")
    else:
        cur.close()
        con.close()
        return
    result = cur.fetchone()
    cur.close()
    con.close()
    if not result:
        return
    return result[0]

def set_stored_item(item, value):
    "Sets parameter item value into the database"
    con = sqlite3.connect(_PARAMETERS["dbase"])
    with con:
        cur = con.cursor()
        if item == "host":
            cur.execute("UPDATE parameters SET host = ?", (value,))
        elif item == "port":
            cur.execute("UPDATE parameters SET port = ?", (value,))
        elif item == "indihost":
            cur.execute("UPDATE parameters SET indihost = ?", (value,))
        elif item == "indiport":
            cur.execute("UPDATE parameters SET indiport = ?", (value,))
        elif item == "blobfolder":
            cur.execute("UPDATE parameters SET blobfolder = ?", (value,))
    cur.close()
    con.close()



def setupdbase(host, port, dbfolder):
    "This is called on startup to setup the database and read initial parameters"

    global _PARAMETERS
    _PARAMETERS["host"] = host
    _PARAMETERS["port"] = port
    _PARAMETERS["dbfolder"] = dbfolder

    dbase = dbfolder / "indipyweb.db"

    _PARAMETERS["dbase"] = dbase


    # set defaults
    defaults = {'host':'localhost',
                'port':8000,
                'indihost':'localhost',
                'indiport':7624,
                'blobfolder':None}


    if not dbase.is_file():
        # create a database file, initially with user 'admin', password 'password!', and auth 'admin'
        # where auth is either 'admin' or 'user'. passwords are stored as scrypt hashes

        # generate and store a random number as salt
        salt = os.urandom(16)

        # encode the userpassword
        encoded_password = scrypt( password = 'password!'.encode(),
                                   salt = salt,
                                   n = 2048,
                                   r = 8,
                                   p = 1,
                                   maxmem=0,
                                   dklen=64)

        con = sqlite3.connect(dbase)

        with con:
            con.execute("CREATE TABLE users(username PRIMARY KEY, password NOT NULL, auth NOT NULL, salt NOT NULL, fullname) WITHOUT ROWID")
            con.execute("INSERT INTO users VALUES(:username, :password, :auth, :salt, :fullname)",
                  {'username':'admin', 'password':encoded_password, 'auth':'admin', 'salt':salt, 'fullname':'Default Administrator'})

            con.execute("CREATE TABLE parameters(host, port, indihost, indiport, blobfolder)")
            con.execute("INSERT INTO parameters VALUES(:host, :port, :indihost, :indiport, :blobfolder)", defaults)
        con.close()

        if not _PARAMETERS["host"]:        # command line argument has priority if it exists
            _PARAMETERS["host"] = defaults['host']
        if not _PARAMETERS["port"]:        # command line argument has priority if it exists
            _PARAMETERS["port"] = defaults['port']
        _PARAMETERS["indihost"] = defaults['indihost']
        _PARAMETERS["indiport"] = defaults['indiport']
        _PARAMETERS["blobfolder"] = defaults['blobfolder']

    else:
        # dbase exists, so read host, port, indihost, indiport, blobfolder

        con = sqlite3.connect(dbase)
        cur = con.cursor()
        cur.execute("SELECT host, port, indihost, indiport, blobfolder FROM parameters")
        result = cur.fetchone()
        cur.close()
        con.close()
        webhost, webport, indihost, indiport, blobfolder = result

        if not _PARAMETERS["host"]:        # command line argument has priority if it exists
            _PARAMETERS["host"] = result[0]
        if not _PARAMETERS["port"]:        # command line argument has priority if it exists
            _PARAMETERS["port"] = result[1]
        _PARAMETERS["indihost"] = result[2]
        _PARAMETERS["indiport"] = result[3]
        _PARAMETERS["blobfolder"] = result[4]


########### Functions to set and read user information from the database

def checkuserpassword(user:str, password:str) -> UserInfo|None:
    """Given a user,password pair from a login form,
       If this matches the database entry for the user, return a UserInfo object
       If this user does not exist, or the password does not match, return None"""
    # everytime a user logs in, expired cookies are deleted
    cleanusercookies()
    if (not user) or (not password):
        return
    if len(user)<5:
        return
    if len(password)<8:
        return
    con = sqlite3.connect(_PARAMETERS["dbase"])
    cur = con.cursor()
    cur.execute("SELECT password,auth,salt,fullname FROM users WHERE username = ?", (user,))
    result = cur.fetchone()
    cur.close()
    con.close()
    if not result:
        return
    # encode the received password, and compare it with the value in the database
    storedpassword, auth, salt, fullname = result
    # hash the received password to compare it with the encoded password
    receivedpassword = scrypt( password = password.encode(),
                               salt = salt,
                               n = 2048,
                               r = 8,
                               p = 1,
                               maxmem=0,
                               dklen=64)
    if receivedpassword == storedpassword:
        # user and password are ok, return a UserInfo object
        return UserInfo(user, auth, fullname)
    # invalid password, return None


def createcookie(user:str) -> str:
    """Given a user, create and return a cookie string value
       Also create and set a UserAuth object into USERCOOKIES"""
    randomstring = token_urlsafe(16)
    USERCOOKIES[randomstring] = UserAuth(user, time.time())
    # The cookie returned will be the random string
    return randomstring


@lru_cache
def getuserinfo(user:str) -> UserInfo:
    "Return UserInfo object for the given user, if not found, return None"

    # Note this is cached, so repeated calls for the same user
    # do not need sqlite lookups.

    con = sqlite3.connect(_PARAMETERS["dbase"])
    cur = con.cursor()
    cur.execute("SELECT auth, fullname FROM users WHERE username = ?", (user,))
    result = cur.fetchone()
    cur.close()
    con.close()
    if not result:
        return
    auth, fullname = result
    return UserInfo(user, auth, fullname)


def cleanusercookies() -> None:
    "Every time someone logs in, remove any expired cookies from USERCOOKIES"
    now = time.time()
    for cookie in list(USERCOOKIES.keys()):
        userauth = USERCOOKIES[cookie]
        if now-userauth.time > IDLETIMEOUT:
            # log the user out, after IDLETIMEOUT inactivity
            del USERCOOKIES[cookie]


def getuserauth(cookie:str) -> UserAuth|None:
    "Return UserAuth object, or None on failure"
    userauth = USERCOOKIES.get(cookie)
    if userauth is None:
        return
    now = time.time()
    if now-userauth.time > IDLETIMEOUT:
        # log the user out, as IDLETIMEOUT inactivity has passed
        del USERCOOKIES[cookie]
        return
    # success, update the time
    userauth.time = now
    return userauth


def verify(cookie:str) -> UserInfo|None:
    "Return UserInfo object, or None on failure"
    userauth = getuserauth(cookie)
    if userauth is None:
        return
    # return a UserInfo object
    return getuserinfo(userauth.user)


def logoutuser(user:str) -> None:
    "Logs the user out, even if user has multiple sessions open"
    for cookie in list(USERCOOKIES.keys()):
        userauth = USERCOOKIES[cookie]
        if user == userauth.user:
            del USERCOOKIES[cookie]


def logout(cookie:str) -> None:
    "Logout function by removing cookie from dictionary of logged in cookies"
    if cookie not in USERCOOKIES:
        return
    del USERCOOKIES[cookie]


def newfullname(user:str, newfullname:str) -> str|None:
    "Sets a new fullname for the user, on success returns None, on failure returns an error message"
    if not newfullname:
        return "An empty full name is insufficient"
    if len(newfullname) > 30:
        return "A full name should be at most 30 characters"
    con = sqlite3.connect(_PARAMETERS["dbase"])
    with con:
        cur = con.cursor()
        cur.execute("SELECT count(*) FROM users WHERE username = ?", (user,))
        result = cur.fetchone()[0]
        if result:
            cur.execute("UPDATE users SET fullname = ? WHERE username = ?", (newfullname, user))
    cur.close()
    con.close()
    if not result:
        # invalid user
        logoutuser(user)
        return "User not found"
    # clear cache
    getuserinfo.cache_clear()


def changepassword(user:str, newpassword:str) -> str|None:
    "Sets a new password for the user, on success returns None, on failure returns an error message"

    if len(newpassword) < 8:
        return "New password needs at least 8 characters"

    if newpassword.isalnum():
        return "New password needs at least one special character"

    # generate and store a random number as salt
    salt = os.urandom(16)

    # encode the userpassword
    encoded_password = scrypt( password = newpassword.encode(),
                               salt = salt,
                               n = 2048,
                               r = 8,
                               p = 1,
                               maxmem=0,
                               dklen=64)

    con = sqlite3.connect(_PARAMETERS["dbase"])
    with con:
        cur = con.cursor()
        cur.execute("SELECT count(*) FROM users WHERE username = ?", (user,))
        result = cur.fetchone()[0]
        if result:
            cur.execute("UPDATE users SET password = ?, salt = ? WHERE username = ?", (encoded_password, salt, user))
    cur.close()
    con.close()
    if not result:
        # invalid user
        logoutuser(user)
        return "User not found"


def deluser(user:str) -> str|None:
    "Deletes the user, on success returns None, on failure returns an error message"
    if not user:
        return "No user given"
    con = sqlite3.connect(_PARAMETERS["dbase"])
    cur = con.cursor()
    cur.execute("SELECT auth FROM users WHERE username = ?", (user,))
    result = cur.fetchone()
    if not result:
        cur.close()
        con.close()
        return "User not recognised"
    if result[0] == "admin":
        # Further check: confirm this is not the only admin
        cur.execute("SELECT count(*) FROM users WHERE auth = 'admin'")
        number = cur.fetchone()[0]
        if number == 1:
            cur.close()
            con.close()
            return "Cannot delete the only administrator"
    cur.execute("DELETE FROM users WHERE username = ?", (user,))
    con.commit()
    cur.close()
    con.close()
    # The user is deleted
    logoutuser(user)
    # clear cache
    getuserinfo.cache_clear()


def adduser(user:str, password:str, auth:str, fullname:str) -> str|None:
    "Checks the user does not already exist, returns None on success, on failure returns an error message"
    if not user:
        return "No username given"
    elif len(user)<5:
        return "New username needs at least 5 characters"
    elif not user.isalnum():
        return "Username must be alphanumeric only"
    elif len(user)>16:
        return "New username should be at most 16 characters"
    elif len(password) < 8:
        return "New password needs at least 8 characters"
    elif password.isalnum():
        return "The password needs at least one special character"
    elif auth != "user" and auth != "admin":
        return "Auth level not recognised"
    elif not fullname:
        return "A full name is required"
    elif len(fullname)>30:
        return "Your full name should be at most 30 characters"

    con = sqlite3.connect(_PARAMETERS["dbase"])
    cur = con.cursor()
    cur.execute("SELECT count(*) FROM users WHERE username = ?", (user,))
    number = cur.fetchone()[0]
    if number:
        cur.close()
        con.close()
        return "Cannot add, this username already exists"

    # generate and store a random number as salt
    salt = os.urandom(16)

    # encode the users password
    encoded_password = scrypt( password = password.encode(),
                               salt = salt,
                               n = 2048,
                               r = 8,
                               p = 1,
                               maxmem=0,
                               dklen=64)

    # store the new user
    con.execute("INSERT INTO users VALUES(:username, :password, :auth, :salt, :fullname)",
              {'username':user, 'password':encoded_password, 'auth':auth, 'salt':salt, 'fullname':fullname})
    con.commit()
    cur.close()
    con.close()
    # The user is added



def userlist(thispage:int, requestedpage:str = "", numinpage:int = 10) -> dict|None:
    """requestedpage = '' for current page
                       '-' for previous page
                       '+' for next page
       numinpage is the number of results in the returned page
       Returns a dict of {users:list of [(username, fullname) ... ] for a page, ...plus pagination information}"""
    if not numinpage:
        return
    con = sqlite3.connect(_PARAMETERS["dbase"])
    cur = con.cursor()
    cur.execute("SELECT count(username) FROM users")
    number = cur.fetchone()[0]
    # number is total number of users
    lastpage = (number - 1) // numinpage
    # lastpage is the last page to show
    if requestedpage == "+" and thispage < lastpage:
        newpage = thispage + 1
    elif requestedpage == "-" and thispage:
        newpage = thispage - 1
    else:
        newpage = thispage
    if newpage > lastpage:
        # this could happen if users have been deleted
        newpage = lastpage
    # newpage is the page number required, starting at page 0
    # with numinpage results per page, calculate the number of lines to skip
    skip = numinpage*newpage
    cur.execute("SELECT username, fullname, auth FROM users ORDER BY fullname COLLATE NOCASE, username COLLATE NOCASE LIMIT ?, ?", (skip, numinpage))
    users = cur.fetchall()
    cur.close()
    con.close()
    # get previous page and next page
    if newpage<lastpage:
        # There are further users to come
        nextpage = newpage+1
    else:
        # No further users
        nextpage = newpage
    if newpage:
        # Not the first page, so previous pages must exist
        prevpage = newpage-1
    else:
        # This is page 0, no previous page
        prevpage = 0

    return {"users":users, "nextpage":nextpage, "prevpage":prevpage, "thispage":newpage, "lastpage":lastpage}


def dbbackup() -> str|None:
    "Create database backup file, return the file name, or None on failure"
    global _PARAMETERS

    backupfilename = datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S') + ".db"
    backupfilepath = _PARAMETERS["dbfolder"] / backupfilename

    try:
        con = sqlite3.connect(_PARAMETERS["dbase"])
        with con:
            con.execute("VACUUM INTO ?", (str(backupfilepath),))
        con.close()
    except Exception:
        return
    return backupfilename
