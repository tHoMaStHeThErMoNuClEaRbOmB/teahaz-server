import os
import sys
import json
import uuid
import base64
import sqlite3


import security_th as security
from logging_th import logger as log



#--------------------------------------------- encoding ---------------------------------------------
# encode/decode shit to stop any sort of injection
def b(a):
    return base64.b64encode(str(a).encode('utf-8')).decode('utf-8')

def d(a):
    return base64.b64decode(str(a).encode('utf-8')).decode('utf-8')

# decode, but omit errors
# this is strictly for optional arguments and should not be used anywhere else
def de(a):
    try:
        a = base64.b64decode(str(a).encode('utf-8')).decode('utf-8')
    except:
        pass
    return a




################################################# user stuff ###############################################
#-------------------------------------------------  init ----------------------------------------------------
# creates a users database
def init_main_db():
    try:
        db_connection = sqlite3.connect(f'storage/main.db')
        db_cursor = db_connection.cursor()
        db_cursor.execute(f"CREATE TABLE chatrooms ('chatroomId', 'chatroom_name')")
        db_cursor.execute(f"CREATE TABLE users ('username', 'email', 'nickname', 'password', cookies, chatrooms)")
        db_connection.commit()
        db_connection.close()


    except Exception as e:
        return f"error occured during the creation of main.db: {e}", 500


    return "OK", 200


#------------------------------------------------  testing --------------------------------------------------
# tis only for testinerror
def get_all_users(p=True):
    if not os.path.isfile('storage/main.db'):
        return False
    try:
        db_connection = sqlite3.connect(f'storage/main.db')
        db_cursor = db_connection.cursor()
        db_cursor.execute(f"SELECT * FROM users")
        a = db_cursor.fetchall()
        db_connection.close()
        if p:
            for i in a:
                print(i)

        return True
    except:
        return False


#-------------------------------------------------- access control ------------------------------------------
def save_new_user(username=None, email=None, nickname=None, password=None):
    try:

        # encode email if compulsary
        if email != None:
            email = b(email)


        # encode username and nickname (no injection pls)
        username = b(username)
        nickname = b(nickname)


        # hash pw (no plain-text pls)
        password = b(security.hashpw(password))


        # NOTE: issue in todo.md
        # default cookie and default chatroom should be removed
        cookie = b(json.dumps(['cookie time']))
        chatrooms = b(json.dumps([]))


    # if some of the data was corrupt and couldnt be encoded/hahsed
    except Exception as e:
        log(level='error', msg=f"[server/dbhandler/save_new_user/0] malformed data, could not be encloded\nTraceback: {e}")
        return "Internal server error", 500


    # save all the encoded data in the database
    try:
        db_connection = sqlite3.connect(f'storage/main.db')
        db_cursor = db_connection.cursor()
        # cookies are being stored as a list that has been converted to string, this makes it easy to add new cookies
        db_cursor.execute(f"INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", (username, email, nickname, password, cookie, chatrooms))
        db_connection.commit()
        db_connection.close()


    # fail on sqlite errors. This usually happens when the server is run without properly set up databases
    except sqlite3.OperationalError as e:
        log(level='fail', msg=f'[server/dbhandler/checkuser/3] database operation failed:  {e}')
        return "Login failed. Internal database error", 500


    # everything okay
    return "OK", 200


def checkuser(username=None, email=None, password=None):
    if not os.path.isfile(f'storage/main.db'): #  check if there is a database
        # i dont think database should be autoinitialized bc on some error it could delete the old database
        log(level='fail', msg=f'could not find main.db')
        return "Login failed. Internal server error", 500


    # check if password exists
    # this should not happen as there are tests before, but it doesnt hurt to check again :)
    if password == None:
        return "Login failed. no password sent", 400


    # email takes priority over username, so if email is present then use that for login
    if email != None:
        key = b(email)
        using = 'email'


    # if no email then login with username
    else: 
        key = b(username)
        using = 'username'




    # get all passwords for the user from the db
    try:
        db_connection = sqlite3.connect(f'storage/main.db')
        db_cursor = db_connection.cursor()
        db_cursor.execute(f"SELECT password FROM users WHERE {using} = ?", (key,))
        storedPassword = db_cursor.fetchall()
        db_connection.close()


    # fail on sqlite errors. This usually happens when the server is run without properly set up databases
    except sqlite3.OperationalError as e:
        log(level='fail', msg=f'[server/dbhandler/checkuser/3] database operation failed:  {e}')
        return "Login failed. Internal database error", 500


    # check for passwords with for said user
    # if there are none then the user is not registered
    if len(storedPassword) > 0:
        storedPassword = d(storedPassword[0][0])
    else:
        return "Login failed. Unrecognized username. Are you registered?", 401


    # check if the password is correct
    if security.checkpw(password, storedPassword):
        return "OK", 200
    else:
        return "Login failed. Username/email or password is incorrect!", 401


def user_save_chatroom(username, new_chatroom):
    if not username or not new_chatroom:
        log(level='fail', msg=f'[server/dbhandler/user_save_chatroom/0] user_save_chatroom did not get the required arguments')
        return "internal server error", 500

    try:
        username = b(username)
    except:
        return "usernme could not be encoded", 500


    # get stored cookies
    try:
        db_connection = sqlite3.connect("storage/main.db")
        db_cursor = db_connection.cursor()
        db_cursor.execute(f"SELECT chatrooms FROM users WHERE username = ?", (username,))
        chatrooms = db_cursor.fetchall()
        db_connection.close()


    # fail on sqlite errors. This usually happens when the server is run without properly set up databases
    except sqlite3.OperationalError as e:
        log(level='fail', msg=f'[server/dbhandler/user_save_chatroom/1] database operation getting chatrooms failed:  {e}')
        return "Internal database error", 500


    # al users should have at least '[]' stored their chatrooms, if they dont then the database is corrupted somehow
    print(chatrooms)
    if len(chatrooms) == 0:
        log(level='error', msg=f'[server/dbhandler/user_save_chatroom/2] user does not exists or did not get initialized properly')
        return "Internal database error", 500


    # add new chatroomId to chatrooms list
    ## cookies are being stored as a list that has been converted to string, this makes it easy to add new cookies
    try:
        #decode
        chatrooms = d(chatrooms[0][0])

        #append
        chatrooms = json.loads(chatrooms)
        chatrooms.append(new_chatroom)
        chatrooms = json.dumps(chatrooms)

        # encode
        chatrooms = b(chatrooms)


    # if the cookies cannot be decoded/encoded than the data is malformed, which is a server issue
    except:
        log(level='error', msg=f'[server/dbhandler/user_save_chatroom/3] malformed chatroom data in databse')
        return "Internal database error", 500


    # update server with new cookes list
    try:
        db_connection = sqlite3.connect("storage/main.db")
        db_cursor = db_connection.cursor()
        db_cursor.execute(f'UPDATE users SET chatrooms = ? WHERE username = ?', (chatrooms, username))
        db_connection.commit()
        db_connection.close()


    # fail on sqlite errors. This usually happens when the server is run without properly set up databases
    except sqlite3.OperationalError as e:
        log(level='fail', msg=f'[server/dbhandler/user_save_chatroom/4] database operation, saving chatroom: failed:  {e}')
        return "Internal database error", 500


    # everything worked out fine
    return "OK", 200


#NOTE this could probably be merged with get_cookes
def user_get_chatrooms(username):
    try:
        username = b(username)

    except Exception as e:
        log(level='error', msg=f"[server/dbhandler/user_get_chatroms/0] username could not be encoded: {e}")
        return "internal server error", 500


    # get all  stored cookies of the user
    try:
        db_connection = sqlite3.connect(f'storage/main.db')
        db_cursor = db_connection.cursor()
        db_cursor.execute(f"SELECT chatrooms FROM users WHERE username = ?", (username,))
        data = db_cursor.fetchall()
        db_connection.close()



    except sqlite3.OperationalError as e:
        log(level='fail', msg=f'[server/dbhandler/user_get_chatroms/1] database operation failed:  {e}')
        return "internal database error", 500


    # chatrooms are stored in a base64 encoded str(list)
    if len(data) == 0:
        log(level='error', msg=f'[server/dbhandler/user_get_chatroms/2] user not initialized properly')
        return "internal database error", 500


    # decode and load the data as json
    try:
        data = d(data)
        data = json.loads(data)
    except:
        log(level='error', msg=f'[server/dbhandler/user_get_chatroms/3] failed to process chatrooms data of user {username}\n Data is probably corrupted')


    return data, 200





def check_access(username, chatroom_id):
    #return "chatroom doesnt exist or user doesnt have access to view it", 404
    return "OK", 200



# NOTE get nickname and get chatname could probably be combined into one function
def get_nickname(username):
    try:
        username = b(username)
        db_connection = sqlite3.connect(f'storage/main.db')
        db_cursor = db_connection.cursor()
        db_cursor.execute(f"SELECT nickname FROM users WHERE username = ?", (username,))
        data = db_cursor.fetchall()
        db_connection.close()
    except sqlite3.OperationalError as e:
        log(level='fail', msg=f'[server/dbhandler/get_nickname/0] database operation failed:  {e}')
        return False

    # sqlite3 wraps the username in a tuple inside of a list
    #print(data)
    try:
        nickname = d(data[0][0])
    except:
        nickname = "could not get nickname"


    return nickname


def get_chatname(chatroomId):
    try:
        chatroomId = b(chatroomId)
        db_connection = sqlite3.connect(f'storage/main.db')
        db_cursor = db_connection.cursor()
        db_cursor.execute(f"SELECT chatroom_name FROM chatrooms WHERE chatroomId = ?", (chatroomId,))
        data = db_cursor.fetchall()
        db_connection.close()



    except sqlite3.OperationalError as e:
        log(level='fail', msg=f'[server/dbhandler/get_nickname/0] database operation failed:  {e}')
        return "internal database error: database operation failed", 500



    try:
        chatroom_name = d(data[0][0])


    except:
        log(level='fail', msg=f'[server/dbhandler/get_chatname/1] corrupted data in database:  {e}')
        return "internal database error: some values may be corrupted", 500


    return chatroom_name, 200


def store_cookie(username=None, email=None, new_cookie=None):
    if new_cookie == None: # check if the function was called without cookies, this should only happen if the sever code is brokent
        log(level="error", msg=f'[server/dbhandler/store_cookie/0] function was called without a cookie supplied to it')
        return "Internal server error", 500


    # email takes priority over username, so if email is present then use that as the key
    if email != None:
        key = b(email)
        using = 'email'


    # if no email then key is username
    else: 
        key = b(username)
        using = 'username'


    # get stored cookies
    try:
        db_connection = sqlite3.connect("storage/main.db")
        db_cursor = db_connection.cursor()
        db_cursor.execute(f"SELECT cookies FROM users WHERE {using} = ?", (key,))
        cookies = db_cursor.fetchall()
        db_connection.close()


    # fail on sqlite errors. This usually happens when the server is run without properly set up databases
    except sqlite3.OperationalError as e:
        log(level='fail', msg=f'[server/dbhandler/store_cookie/1] database operation getting cookies failed:  {e}')
        return "Internal database error", 500


    # al users should have at least '[]' stored as cookes, if they dont then the database is corrupted somehow
    if len(cookies) == 0:
        log(level='error', msg=f'[server/dbhandler/store_cookie/2] user does not exists or did not get initialized properly\n (database cookies entry doesnt exist)')
        return "Internal database error", 500


    # add new cookie to cookies list
    ## cookies are being stored as a list that has been converted to string, this makes it easy to add new cookies
    try:
        #decode
        cookies = d(cookies[0][0])

        #append
        cookies = json.loads(cookies)
        cookies.append(new_cookie)
        cookies = json.dumps(cookies)

        # encode
        cookies = b(cookies)


    # if the cookies cannot be decoded/encoded than the data is malformed, which is a server issue
    except:
        log(level='error', msg=f'[server/dbhandler/store_cookie/3] malformed cookie data in databse')
        return "Internal database error", 500


    # update server with new cookes list
    try:
        db_connection = sqlite3.connect("storage/main.db")
        db_cursor = db_connection.cursor()
        db_cursor.execute(f'UPDATE users SET cookies = ? WHERE {using} = ?', (cookies, key))
        db_connection.commit()
        db_connection.close()


    # fail on sqlite errors. This usually happens when the server is run without properly set up databases
    except sqlite3.OperationalError as e:
        log(level='fail', msg=f'[server/dbhandler/store_cookie/3] database operation, saving cookie: failed:  {e}')
        return "Internal database error", 5000


    # everything worked out fine
    return "OK", 200



def get_cookies(username):
    username = b(username)

    # get all  stored cookies of the user
    try:
        db_connection = sqlite3.connect(f'storage/main.db')
        db_cursor = db_connection.cursor()
        db_cursor.execute(f"SELECT cookies FROM users WHERE username = ?", (username,))
        data = db_cursor.fetchall()
        db_connection.close()
    except sqlite3.OperationalError as e:
        log(level='fail', msg=f'[server/dbhandler/get_cookies/2] database operation failed:  {e}')
        return False

    # cookies are stored in a base64 encoded str(list)
    if len(data) == 0:
        return False

    # decode and load the data as json
    try:
        data = d(data)
        data = json.loads(data)
    except:
        log(level='error', msg=f'[server/dbhandler/get_cookies/0] failed to process cookie data of user {username}\n Data is probably corrupted')

    return data



def check_user_exists(username=None, email=None):
    try: # try format data
        if username: username = b(username)
        if email: email = b(email)
    except:
        return "[server/dbhanler/check_user_exitst/0] username or email corrupt", 400

    try:
        # connec to the db
        db_connection = sqlite3.connect(f'storage/main.db')
        db_cursor = db_connection.cursor()

        # run slightly different checks depending on the data supplied
        if username and email:
            db_cursor.execute(f"SELECT * FROM users WHERE username = ? OR email = ?", (username,email,))
        elif username and not email:
            db_cursor.execute(f"SELECT * FROM users WHERE username = ? ", (username,))
        elif not username and email:
            db_cursor.execute(f"SELECT * FROM users WHERE email = ? ", (email,))


        # finalize everything
        data = db_cursor.fetchall()
        db_connection.close()


    except Exception as e:
        log(level='fail', msg=f'[server/dbhandler/get_nickname/0] database operation failed:  {e}')
        return '[server/dbhandler/check_user_exitst/1] internal database error', 500


    if len(data) > 0:
        return True, 200
    else:
        return False, 200



################################################# chat stuff ###############################################
#------------------------------------------------  testing ---------------------------------------------------
# tis only for testing
def get_all_messages(chatroom_id, p=True):
    if not os.path.exists("storage/conv1"):
        return False

    try:
        db_connection = sqlite3.connect(f'storage/{chatroom_id}/chatroom.db')
        db_cursor = db_connection.cursor()
        db_cursor.execute(f"SELECT * FROM messages")
    except sqlite3.OperationalError as e:
        log(level='fail', msg=f'[server/dbhandler/get_all_messages/0] database operation failed:  {e}')
        return False

    a = db_cursor.fetchall()

    if p:
        for b in a:
            print(b)

    db_connection.close()

    return True


#-------------------------------------------------  creating chatrooms ------------------------------------------------------
def init_chat(chatroom_id):
    try:
        db_connection = sqlite3.connect(f'storage/{chatroom_id}/chatroom.db')
        db_cursor = db_connection.cursor()
        db_cursor.execute(f"CREATE TABLE users ('username', 'admin', 'colour')")
        db_cursor.execute(f"CREATE TABLE messages ('time', 'messageId', 'username', 'chatroom_id', 'type', 'message', 'filename', 'extension')")
        db_connection.commit()
        db_connection.close()


    except Exception as e:
        return f"could not connect to database: {e}", 500

    return "OK", 200


def save_chatroom(chatroomId, chatroom_name):
    try:
        chatroomId = b(chatroomId)
        chatroom_name = b(chatroom_name)


    except Exception as e:
        return f"could not encode data: {e}"


    try:
        db_connection = sqlite3.connect(f'storage/main.db')
        db_cursor = db_connection.cursor()
        db_cursor.execute(f"INSERT INTO chatrooms VALUES (?, ?)", (chatroomId, chatroom_name))
        db_connection.commit()
        db_connection.close()


    except Exception as e:
        return f"could not connect to main database: {e}", 500


    return "OK", 200


#---------------------------------------------------- messages ------------------------------------------------
# va=None means that the fild is not used
# var=0 means that the field is not set AND IS NEEDED FOR THE FUNCTION
# this destiction is for readability, the None values are not required but the 0 ones are
def save_in_db(time=0, messageId=0, username=0, chatroom_id=0, message_type=0, message=None, filename=None, extension=None ):
    if time == 0 or messageId == 0 or username == 0 or chatroom_id == 0 or message_type == 0: #values marked with 0 are needed while ones marked with None are optional
        # making sure that all values that are needed exist
        log(level='error', msg='[server/dbhandler/save_in_db/0] one or more of the required fields passed to function "save_in_db" are not present [time, username, chatroom_id, message_type]')
        return "internal server error", 500


    # connect to the database
    try:
        db_connection = sqlite3.connect(f'storage/{chatroom_id}/chatroom.db') # chatroom_id is the folder name that data to do with chatroom resides in
        db_cursor = db_connection.cursor()


    # error: the database does not exists
    except:
        log(level='error', msg=f'[server/dbhandler/save_in_db/1] server could not connect to database')
        return "internal database error", 500


    # encode cumpolsary values
    try:
        username = b(username)
        messageId = b(messageId)
        chatroom_id = b(chatroom_id)
        message_type = b(message_type)


    # if this fails its bc the user sent bad data
    except:
        return "corrupted data sent to server", 400


    # encode non compulsary values
    if message: message = b(message)
    if filename: filename = b(filename)
    if extension: extension = b(extension)


    # save the new message
    try:
        db_cursor.execute(f"INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (time, messageId, username, chatroom_id, message_type, message, filename, extension))
        db_connection.commit()
        db_connection.close()


    # fail on sqlite errors. This usually happens when the server is run without properly set up databases
    except sqlite3.OperationalError as e:
        log(level='fail', msg=f'[server/dbhandler/save_in_db/2] database operation failed:  {e}')
        return "internal database error", 500


    # all is well
    return "OK", 200


def get_messages_db(last_time=0, chatroom_id=''):
    try: # try connect to the db
        db_connection = sqlite3.connect(f'storage/{chatroom_id}/chatroom.db') # chatroom_id is the folder name that data to do with chatroom resides in
        db_cursor = db_connection.cursor()


    # db doesnt exist
    except:
        log(level='error', msg=f'[server/dbhandler/get_messages/0] server could not connect to database')
        return "internal server error", 500



    # time and chatroom_id should not be encoded:
        # time shouldnt because its needed in sql queries with >=
        # chatroom_id is just an id, and its not controllable by the client



    # get all messages that had been sent since 'last_time'
    try:
        db_cursor.execute("SELECT * FROM messages WHERE time >= ?", (last_time,))

        data = db_cursor.fetchall()
        db_connection.close()
    except sqlite3.OperationalError as e:
        log(level='fail', msg=f'[server/dbhandler/get_messages/1] database operation failed:  {e}')
        return "internal database error", 500


    # sqlite returns a list of lists, we should convert this back to json
    json_data = []

    # format messages for returning
    try:
        for element in data:
            nickname = get_nickname(d(element[2]))

            # get compulsary data, all but time need to be decoded
            send_time = element[0]
            messageId = d(element[1])
            username = d(element[2])
            chatroom = d(element[3])
            msg_type = d(element[4])

            # get optional data, they may or may not be present
            message = element[5]
            if message: message = d(message)
            filename = element[6]
            if filename: filename = d(filename)
            extension = element[7]
            if extension: extension = d(extension)

            # make return dict
            a = {
                'time': send_time,
                'messageId': messageId,
                'username': username,
                'nickname': nickname,
                'chatroom': chatroom,
                'type': msg_type,
                'message': message,
                'filename': filename,
                'extension': extension
                    }

            # add to list
            json_data.append(a)


    # message format error
    except Exception as e:
    #else:
        log(level='error', msg=f"[server/dbhandler/get_messages/2] some data in the database is corrupted and cannot be decoded\n Traceback: {e}")
        return "internal databse error", 500


    # all is well
    return json_data, 200



def check_databses():
    log(level='log', msg='running system checks')


    # check if storage folder exists
    log(level='log', msg='checking storage folder')

    # check if folder exists, and try to create it if not
    if not os.path.isdir("storage/"):
        try:
            log(level='warning', msg='[health check] creating storage folder')
            os.mkdir("storage")

        except Exception as e:
            return f"could not create storage folder: {e}\n Please make sure you have to correct permissions", 500




    # check main.db
    log(level='log', msg='checking main db')

    # does the main db exist?
    if not os.path.isfile('storage/main.db'):
        log(level='warning', msg=f'[health check] creating main.db')

        response, status_code = init_main_db()
        if status_code != 200:
            return f"failed to create main.db\n Traceback: {response}\n\n Suggest that you delete the 'storage' folder"


    # make sure the database is good by testing all tables
    try:
        db_connection = sqlite3.connect(f'storage/main.db')
        db_cursor = db_connection.cursor()
        db_cursor.execute(f"SELECT * FROM users")
        db_cursor.execute(f"SELECT * FROM chatrooms")
        a = db_cursor.fetchall()
        db_connection.close()


    # something is wrong with the database
    except Exception as e:
        return f"main database is missing tables or otherwise corrupted\n Traceback: {e}", 500


    log(level='success', msg='[health check] System is healthy :)')
    return "OK", 200

