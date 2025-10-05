"""This module defines users and passwords on a database"""

import sqlite3, os, time

from datetime import datetime, timezone

from hashlib import scrypt

from secrets import token_urlsafe

from pathlib import Path

from dataclasses import dataclass

from functools import lru_cache

from ..register import userdbase_location, userdbase_file


# These global values will be set by a call to setupdbase()
USERDBASE_LOCATION = None
USERDBASE = None


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
# These store the user associated with the cookie, and can also be used to store any
# temporary data associated with a particular logged in session.

@dataclass
class UserAuth():
    "Class used to hold a logged in user details"
    user:str             # The username
    time:float           # time used for timing out the session
    page:int             # admins can see 'pages' of user data, this stores the current page number
    device:str           # the device being displayed


def setupdbase():

    global USERDBASE_LOCATION, USERDBASE

    USERDBASE_LOCATION = userdbase_location()
    USERDBASE = userdbase_file()


    if not USERDBASE.is_file():
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

        con = sqlite3.connect(USERDBASE)

        with con:
            con.execute("CREATE TABLE users(username TEXT PRIMARY KEY, password TEXT NOT NULL, auth TEXT NOT NULL, salt TEXT NOT NULL, fullname TEXT) WITHOUT ROWID")
            con.execute("INSERT INTO users VALUES(:username, :password, :auth, :salt, :fullname)",
                  {'username':'admin', 'password':encoded_password, 'auth':'admin', 'salt':salt, 'fullname':'Default Administrator'})
        con.close()



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
    con = sqlite3.connect(USERDBASE)
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
    USERCOOKIES[randomstring] = UserAuth(user, time.time(), 0, '')    # initially page is set to zero, no device
    # The cookie returned will be the random string
    return randomstring


@lru_cache
def getuserinfo(user:str) -> UserInfo:
    "Return UserInfo object for the given user, if not found, return None"

    # Note this is cached, so repeated calls for the same user
    # do not need sqlite lookups.

    con = sqlite3.connect(USERDBASE)
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
    con = sqlite3.connect(USERDBASE)
    with con:
        cur = con.cursor()
        cur.execute("UPDATE users SET fullname = ? WHERE username = ?", (newfullname, user))
    cur.close()
    con.close()
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

    con = sqlite3.connect(USERDBASE)
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
    con = sqlite3.connect(USERDBASE)
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

    con = sqlite3.connect(USERDBASE)
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



def userlist(cookie:str, requestedpage:str="", numinpage:int = 10) -> dict|None:
    """requestedpage = '' for current page
                       '-' for previous page
                       '+' for next page
       numinpage is the number of results in the returned page
       Returns a dict of {users:list of [(username, fullname) ... ] for a page, ...plus page information}
       If cookie not found, returns None"""
    if not cookie:
        return
    userauth = getuserauth(cookie)
    if userauth is None:
        return
    if not numinpage:
        return
    con = sqlite3.connect(USERDBASE)
    cur = con.cursor()
    cur.execute("SELECT count(username) FROM users")
    number = cur.fetchone()[0]
    # number is total number of users
    lastpage = (number - 1) // numinpage
    # lastpage is the last page to show
    currentpage = userauth.page
    if requestedpage == "+" and currentpage < lastpage:
        page = currentpage + 1
    elif requestedpage == "-" and currentpage:
        page = currentpage - 1
    else:
        page = currentpage
    if page > lastpage:
        # this could happen if users have been deleted
        page = lastpage
    # page is the page number required, starting at page 0
    # with numinpage results per page, calculate the number of lines to skip
    skip = numinpage*page
    cur.execute("SELECT username, fullname, auth FROM users ORDER BY fullname COLLATE NOCASE, username COLLATE NOCASE LIMIT ?, ?", (skip, numinpage))
    users = cur.fetchall()
    cur.close()
    con.close()
    # get previous page and next page
    if page<lastpage:
        # There are further users to come
        nextpage = page+1
    else:
        # No further users
        nextpage = page
    if page:
        # Not the first page, so previous pages must exist
        prevpage = page-1
    else:
        # This is page 0, no previous page
        prevpage = 0
    # Update the recorded page in userauth
    userauth.page = page
    return {"users":users, "nextpage":nextpage, "prevpage":prevpage, "thispage":page, "lastpage":lastpage}


def dbbackup() -> str|None:
    "Create database backup file, return the file name, or None on failure"

    backupfilename = datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S') + ".sqlite"
    backupfilepath = USERDBASE_LOCATION / backupfilename

    try:
        con = sqlite3.connect(USERDBASE)
        with con:
            con.execute("VACUUM INTO ?", (str(backupfilepath),))
        con.close()
    except Exception:
        return
    return backupfilename


def setuserdevice(cookie:str, device:str) -> None:
    "Sets the device this user is monitoring, return None on failure, userauth on success"
    if not cookie:
        return
    userauth = getuserauth(cookie)
    if userauth is None:
        return
    if not device:
        return
    userauth.device = device
    return userauth

def getuserdevice(cookie:str) -> str|None:
    "Gets the device this user is monitoring, return None on failure"
    if not cookie:
        return
    userauth = getuserauth(cookie)
    if userauth is None:
        return
    return userauth.device
