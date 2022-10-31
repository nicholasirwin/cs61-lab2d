#!/usr/bin/env python

"""main.py: Description of what the program does."""

# Standard Library
import cmd
import getpass
import os
import shlex
import sys
from typing import List, Union, Literal

# Third Party
from mysql.connector import MySQLConnection, Error, errorcode, FieldType

# Local Modules
from dbconfig import read_db_config

__authors__ = "Giorgie McCombe and Nick Irwin"
__credits__ = "MySQLTutorial, Charles Palmer"
__date__ = "29 Oct 2022"


def connect_to_db() -> MySQLConnection:
    """
    Helper function to connect to MySQL database using Team**Lab2.ini config file.
    Gracefully handle all errors in setting up connection.
    """
    dbconfig = read_db_config()
    if dbconfig["password"] == "":
        dbconfig["password"] = getpass.getpass("database password ? :")

    for key, value in dbconfig.items():
        value = value if key != 'password' else ''
        print(f"{key}: {value}")
    print()
    # print(dbconfig)

    # Connect to the database
    try:
        print("Connecting to MySQL database...")
        conn = MySQLConnection(**dbconfig)

        if conn.is_connected():
            print("connection established.")
        else:
            print("connection failed.")

        return conn

    except Error as err:
        print("connection failed somehow")
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password\nTry Again\n")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print("Unexpected error")
            print(err)
            sys.exit(1)


def handle_register(words: List[str], conn: MySQLConnection) -> None:
    """
    Handle specific `register <author | editor | reviewer>` case input.
    Open and close MySQLConnection.cursor appropriately.
    """
    mycursor = conn.cursor(buffered=True)
    role_id = None
    if not words:
        print("Invalid number of arguments.\n **Usage:** register <author | editor | reviewer>\n")
        return
    role_type = words[0]
    if role_type == "author":
        if len(words) != 5:
            print(
                "Invalid number of arguments.\n **Usage:** register author <fname> <lname> <email> <affiliation>\n"
            )
        else:
            role_id = register_author(words[1:], mycursor)

    elif role_type == "editor":
        if len(words) != 3:
            print(
                "Invalid number of arguments.\n **Usage:** register editor <fname> <lname>\n"
            )
        else:
            role_id = register_editor(words[1:], mycursor)

    elif role_type == "reviewer":
        if len(words) < 4 or len(words) > 6:
            print(
                "Invalid number of arguments.\n **Usage:** register reviewer <fname> <lname> <ICode 1> <ICode 2> <ICode 3>\n"
            )
        else:
            role_id = register_reviewer(words[1:], mycursor)
            record_reviewer_expertise(role_id, [int(word) for word in words[3:]], mycursor)

    else:
        print("Invalid argument.\n **Usage:** register <author | editor | reviewer>\n")

    if role_id:
        login_id = register_unique_id(role_id, role_type, mycursor)
        if login_id:
            print(f"Successfully registered {role_type}.\n")
            print(f"## Your unique login id: `{login_id}` ##\n")

    conn.commit()
    mycursor.close()


def handle_login(words: List[str], conn: MySQLConnection) -> None:
    """
    Handle specific `login <id>` case input.
    Open and close MySQLConnection.cursor appropriately.
    """
    mycursor = conn.cursor(buffered=True)
    print(words)


def register_unique_id(role_id: int, role_type: str, cursor: MySQLConnection.cursor) -> Union[int, None]:
    try:
        query = "INSERT INTO `LOGIN_TO_ROLE` (`roleID`, `role_type`) VALUES ('{}','{}');".format(role_id, role_type)
        # print("-->",query,"<--", end='')
        cursor.execute(query)
    except Error as err:
        print(f"{err.msg}\n")
    else:
        return cursor.lastrowid


def register_author(auth: List[str], cursor: MySQLConnection.cursor) -> Union[int, None]:
    try:
        query = "INSERT INTO `PRIMARY_AUTHOR` (`f_name`, `l_name`, `email`, `affiliation`) VALUES ('{}','{}','{}','{}');".format(auth[0], auth[1], auth[2], auth[3])
        # print("-->",query,"<--", end='')
        cursor.execute(query)
    except Error as err:
        print(f"{err.msg}\n")
    else:
        return cursor.lastrowid


def register_editor(ed: List[str], cursor: MySQLConnection.cursor) -> Union[int, None]:
    try:
        query = "INSERT INTO `EDITOR` (`f_name`, `l_name`) VALUES ('{}','{}');".format(ed[0], ed[1])
        # print("-->",query,"<--", end='')
        cursor.execute(query)
    except Error as err:
        print(f"{err.msg}\n")
    else:
        return cursor.lastrowid


def register_reviewer(rev: List[str], cursor: MySQLConnection.cursor) -> Union[int, None]:
    try:
        query = "INSERT INTO `REVIEWER` (`f_name`, `l_name`) VALUES ('{}','{}');".format(rev[0], rev[1])
        # print("-->",query,"<--", end='')
        cursor.execute(query)
    except Error as err:
        print(f"{err.msg}\n")
    else:
        return cursor.lastrowid

def record_reviewer_expertise(id: int, i_codes: List[int], cursor) -> None:
    for i_code in i_codes:
        try:
            query = "INSERT INTO `REVIEWER_EXPERTISE` (`REVIEWER_reviewerID`, `ICODE_code`) VALUES ('{}','{}');".format(id, i_code)
            # print("-->",query,"<--", end='')
            cursor.execute(query)
        except Error as err:
            print(f"{err.msg}\n")
        # else:
        #     print(f"Successfully added reviewer expertise for ICode={i_code}.\n")


class JournalApp(cmd.Cmd):
    intro = '\nWelcome to the Journal DB Manager.  Type help or ? to list commands.\n'
    prompt = '>>> '
    # file = None

    print("Attempting to connect to db...\n")
    conn = connect_to_db()
    while not conn:
        conn = connect_to_db()

    # current logged-in info
    curr_id: int = None
    curr_role: Literal['author', 'editor', 'reviewer'] = None
    
    # --- basic commands ---
    def do_register(self, arg: str) -> None:
        words = shlex.split(arg)
        handle_register(words, self.conn)

    def do_login(self, arg: str) -> None:
        words = shlex.split(arg)
        handle_login(words, self.conn)

    def do_exit(self, arg: str) -> bool:
        print("Shutting down...")
        self.conn.cmd_reset_connection()
        self.conn.close()
        return True



if __name__ == '__main__':
    JournalApp().cmdloop()
