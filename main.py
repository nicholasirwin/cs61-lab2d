#!/usr/bin/env python

"""main.py: Description of what the program does."""

# Standard Library
import cmd
import getpass
import os
import shlex
import sys
from typing import List, Union, Literal, Tuple

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


def handle_register(args: List[str], conn: MySQLConnection) -> None:
    """
    Handle specific `register <author | editor | reviewer>` case input.
    Open and close MySQLConnection.cursor appropriately.
    """
    mycursor = conn.cursor(buffered=True)
    role_id = None
    if not args:
        print("Invalid number of arguments.\n **Usage:** register <author | editor | reviewer>\n")
        return
    role_type = args[0]
    if role_type == "author":
        if len(args) != 5:
            print(
                "Invalid number of arguments.\n **Usage:** register author <fname> <lname> <email> <affiliation>\n"
            )
        else:
            role_id = register_author(args[1:], mycursor)

    elif role_type == "editor":
        if len(args) != 3:
            print(
                "Invalid number of arguments.\n **Usage:** register editor <fname> <lname>\n"
            )
        else:
            role_id = register_editor(args[1:], mycursor)

    elif role_type == "reviewer":
        if len(args) < 4 or len(args) > 6:
            print(
                "Invalid number of arguments.\n **Usage:** register reviewer <fname> <lname> <ICode 1> <ICode 2> <ICode 3>\n"
            )
        else:
            role_id = register_reviewer(args[1:], mycursor)
            record_reviewer_expertise(role_id, [int(word) for word in args[3:]], mycursor)

    else:
        print("Invalid argument.\n **Usage:** register <author | editor | reviewer>\n")

    if role_id:
        login_id = register_unique_id(role_id, role_type, mycursor)
        if login_id:
            print(f"Successfully registered {role_type}.\n")
            print(f"## Your unique login id: `{login_id}` ##\n")

    conn.commit()
    mycursor.close()


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

    
def handle_login(args: List[str], conn: MySQLConnection) -> Tuple[int, str]:
    """
    Handle specific `login <id>` case input.
    Open and close MySQLConnection.cursor appropriately.
    """
    mycursor = conn.cursor(buffered=True)
    if len(args) != 1:
        print("Invalid number of arguments.\n **Usage:** login <id>\n")
        return
    
    login_id = int(args[0])
    (role_id, role_type) = get_role_from_login(login_id, mycursor) or (None, None)

    if not (role_id and role_type):
        print("Invalid login id\n")
        return

    login = getattr(sys.modules[__name__], f'login_{role_type}')
    login(role_id, mycursor)

    return login_id, role_type

    

def login_author(role_id: int, cursor: MySQLConnection.cursor) -> None:
    """
    A description.
    """
    message = "Welcome author:"
    # authors full name, address, output from status commmand
    try:
        query = "SELECT `f_name`, `l_name`, `email` FROM `PRIMARY_AUTHOR` WHERE `authorID` = {}".format(role_id)
        cursor.execute(query)
    except Error as err:
        print(f"{err.msg}\n")
    else:
        row = cursor.fetchone()
        if row:
            message = f"{message} {row[0]} {row[1]}, {row[2]}\n"
            print(message)

    
def login_editor(role_id: int, cursor: MySQLConnection.cursor) -> None:
    """
    A description.
    """
    message = "Welcome editor:"
    # full name and output from status commeand
    try:
        query = "SELECT `f_name`, `l_name` FROM `EDITOR` WHERE `editorID` = {}".format(role_id)
        cursor.execute(query)
    except Error as err:
        print(f"{err.msg}\n")
    else:
        row = cursor.fetchone()
        if row:
            message = f"{message} {row[0]} {row[1]}\n"
            print(message)
    

def login_reviewer(role_id: int, cursor: MySQLConnection.cursor) -> None:
    """
    A description.
    """
    # full name, list of all manuscripts assigned to reviewer, sorted by their status from 
    # under review through accepted/rejected
    message = "Welcome reviewer:"
    try:
        query = "SELECT `f_name`, `l_name` FROM `REVIEWER` WHERE `reviewerID` = {}".format(role_id)
        cursor.execute(query)
    except Error as err:
        print(f"{err.msg}\n")
    else:
        row = cursor.fetchone()
        if row:
            message = f"{message} {row[0]} {row[1]}\n"
            print(message)
            print("Your manuscripts: \n")
        else:
            return

    try:
        cursor.execute(f"SET @rev_id = {role_id};")
    except Error as err:
        print(f"{err.msg}\n")

    # show ReviewStatus view for this reviewer
    try:
        cursor.execute("SELECT * FROM `ReviewStatus`;")
    except Error as err:
        print(f"{err.msg}\n")
    else:
        rows = cursor.fetchall()
        for row in rows:
            print(row)


def get_role_from_login(login_id: int, cursor: MySQLConnection.cursor) -> Tuple[Union[int, None], str]:
    try:
        query = "SELECT `roleID`, `role_type` FROM `LOGIN_TO_ROLE` WHERE `loginID` = {};".format(login_id)
        cursor.execute(query)
    except Error as err:
        print(f"{err.msg}\n")
    else:
        row = cursor.fetchone()
        if row:
            return row[0], row[1]

    
def handle_resign(conn: MySQLConnection, curr_login_id: int, curr_role: str, arg: str) -> bool:
    mycursor = conn.cursor(buffered=True)

    if arg:
        print("Invalid number of arguments.\n **Usage:** resign \n")
    elif curr_role != 'reviewer' or not curr_login_id:
        print("Invalid command. Only able to `resign` if logged in as a reviewer\n")
    else:
        role_id = get_role_from_login(curr_login_id, mycursor)[0]
        try:
            query = f"DELETE FROM `REVIEWER_EXPERTISE` WHERE `REVIEWER_reviewerID` = {role_id};"
            mycursor.execute(query)
        except Error as err:
            print(f"{err.msg}\n")

        try:
            query = f"DELETE FROM `LOGIN_TO_ROLE` WHERE `roleID` = {role_id};"
            mycursor.execute(query)
        except Error as err:
            print(f"{err.msg}\n")

        try:
            query = f"DELETE FROM `REVIEWER` WHERE `reviewerID` = {role_id};"
            mycursor.execute(query)
        except Error as err:
            print(f"{err.msg}\n")
        else:
            print("You have been removed. Thank you for your service.\n")
            conn.commit()
            mycursor.close()
            return True
    
    return False

def handle_accept(conn: MySQLConnection, curr_login_id: int, curr_role: str, args: List[str]):
    mycursor = conn.cursor(buffered=True)
    # Any attempts to act on a manuscript not assigned to this reviewer or 
    # a manuscript not in “Reviewing” status should fail with an appropriate message.

    # verify user is logged in and is a reviewer
    if curr_role != 'reviewer' or not curr_login_id:
        print("Invalid command. Only able to use `accept` if logged in as a reviewer\n")
    elif len(args) != 5:
        print("Invalid number of arguments.\n **Usage:** accept <manuscriptID> <ascore> <cscore> <mscore> <escore>\n")
    else:
        manID = int(args[0])
        reviewer_id = get_role_from_login(curr_login_id, mycursor)[0]
        
        if check_man_for_reviewer(manID, reviewer_id, mycursor):
            ascore, cscore, mscore, escore = int(args[1]), int(args[2]), int(args[3]), int(args[4])
            # check that scores are between 1 and 10?
            give_feedback(manID, reviewer_id, mycursor, ascore, cscore, mscore, escore, 10)
        
    conn.commit()
    mycursor.close()

def handle_reject(conn: MySQLConnection, curr_login_id: int, curr_role: str, args: List[str]):
    mycursor = conn.cursor(buffered=True)
    # Any attempts to act on a manuscript not assigned to this reviewer or 
    # a manuscript not in “Reviewing” status should fail with an appropriate message.

    # verify user is logged in and is a reviewer
    if curr_role != 'reviewer' or not curr_login_id:
        print("Invalid command. Only able to use `reject` if logged in as a reviewer\n")
    elif len(args) != 5:
        print("Invalid number of arguments.\n **Usage:** reject <manuscriptID> <ascore> <cscore> <mscore> <escore>\n")
    else:
        manID = int(args[0])
        reviewer_id = get_role_from_login(curr_login_id, mycursor)[0]
        
        if check_man_for_reviewer(manID, reviewer_id, mycursor):
            ascore, cscore, mscore, escore = int(args[1]), int(args[2]), int(args[3]), int(args[4])
            # check that scores are between 1 and 10?
            give_feedback(manID, reviewer_id, mycursor, ascore, cscore, mscore, escore, 0)
        
    conn.commit()
    mycursor.close()
    

def give_feedback(manuscriptID: int, reviewerID: int, cursor: MySQLConnection.cursor, ascore: int, cscore: int, mscore:int, escore:int, rec_score:int):
    try:
        query = f"UPDATE `REVIEW` SET `score_a`={ascore}, `score_c`={cscore}, `score_m`={mscore}, `score_e`={escore}, `rec_score`={rec_score}, `date_feedback_received` = now() WHERE `MANUSCRIPT_manuscriptID`={manuscriptID} AND `REVIEWER_reviewerID`={reviewerID};"
        cursor.execute(query)
    except Error as err:
        print(f"{err.msg}\n")
    else:
        print("Scores successfully submitted")


def check_man_for_reviewer(manuscriptID: int, reviewerID: int, cursor: MySQLConnection.cursor) -> bool:
    # verify that manuscript is assigned to reviewer
    # AND that manuscript status is under review
    
    # check that manuscript status is UnderReview
    try:
        query = f"SELECT `status` FROM `MANUSCRIPT` WHERE `manuscriptID`={manuscriptID};"
        cursor.execute(query)
    except Error as err:
        print(f"{err.msg}\n")
    else:
        row = cursor.fetchone()
        # if no row found with that manID, invalid ID
        if not row:
            print("Invalid manuscriptID")
            return False
        if row[0] != "UnderReview":
            print("Error: this manuscript is not `UnderReview`")
            return False

    # check that given manuscript is assigned to this reviewer
    try:
        query = f"SELECT * FROM `REVIEW` WHERE `MANUSCRIPT_manuscriptID`={manuscriptID} AND `REVIEWER_reviewerID`={reviewerID};"
        cursor.execute(query)
    except Error as err:
        print(f"{err.msg}\n")
    else:
        row = cursor.fetchone()
        # if no row found with both manID and reviewerID, not assigned to this reviewer
        if not row:
            print("Error: this manuscript is not assigned to you")
        else:
            return True

    return False


    

def handle_submit(conn: MySQLConnection, curr_login_id: int, curr_role: str, args: List[str]):
    mycursor = conn.cursor(buffered=True)

    if curr_role != 'author' or not curr_login_id:
        print("Invalid command. Only able to `submit` if logged in as an author\n")
    elif len(args) < 4 or len(args) > 7:
        print(
            "Invalid number of arguments.\n **Usage:** submit <title> <Affiliation> <ICode> <author2> <author3> <author4> <filename>\n"
        )
    else:
        role_id = get_role_from_login(curr_login_id, mycursor)[0]
        title, affiliation, icode, filename = args[0], args[1], args[2], args[-1]
        if not file_exists_and_readable(filename):
            return
        with open(filename, 'r') as file:
            document = file.read()
        try:
            query = "INSERT INTO `MANUSCRIPT` (`title`, `document`, `status`, `PRIMARY_AUTHOR_authorID`, `ICODE_code`) VALUES ('{}','{}','{}','{}','{}');".format(title, document, 'submitted', role_id, int(icode))
            mycursor.execute(query)
        except Error as err:
            print(f"{err.msg}\n")
        else:
            # Success
            manuscript_id = mycursor.lastrowid
            print(f"Manuscript submission confirmed.\nSystem-wide unique manuscript id: {manuscript_id}")

            num_secondary_authors = len(args) - 4
            for i in range(num_secondary_authors):
                try:
                    query = "INSERT INTO `SECONDARY_AUTHOR` (`priority`, `MANUSCRIPT_manuscriptID`, `full_name`) VALUES ('{}','{}','{}');".format(i+1, manuscript_id, args[len(args)-1-(num_secondary_authors-i)])
                    mycursor.execute(query)
                except Error as err:
                    print(f"{err.msg}\n")
    
    conn.commit()
    mycursor.close()


def file_exists_and_readable(filename: str) -> bool:
    if os.path.isfile(filename) and os.access(filename, os.R_OK):
        return True
    print("Manuscript filename either doesn't exist or is not readable.\n")
    return False


def handle_status(conn: MySQLConnection, curr_login_id: int, curr_role: str, arg: str) -> bool:
    mycursor = conn.cursor(buffered=True)
    
    if not (curr_login_id and curr_role):
        print("Invalid command. Must be logged in as an author or editor to view `status`\n")
    elif arg:
        print("Invalid number of arguments.\n **Usage:** status \n")
    elif curr_role == 'author':
        author_id = get_role_from_login(curr_login_id, mycursor)[0]
        get_author_status(mycursor, author_id)
    elif curr_role == 'editor':
        editor_id = get_role_from_login(curr_login_id, mycursor)[0]
        get_editor_status(mycursor, editor_id)
    else:
        print("Invalid command. Only able to see `status` if logged in as an author or editor\n")
    
    mycursor.close()


def get_author_status(cursor: MySQLConnection.cursor, author_id: int) -> None:
    try:
        query = f"SELECT `manuscriptID`, `title`, `date_received`, `status`, `status_updated_at` FROM `MANUSCRIPT` WHERE `PRIMARY_AUTHOR_authorID`={author_id};"
        cursor.execute(query)
    except Error as err:
        print(f"{err.msg}\n")
    else:
        rows = cursor.fetchall()
        for i, row in enumerate(rows):
            print(f"Manuscript{row[0]} -- Title: '{row[1]}';  Date received: '{row[2]}';  Current status: '{row[3]}';  Status last updated at: '{row[4]}'\n")


def get_editor_status(cursor: MySQLConnection.cursor, editor_id: int) -> None:
    pass


class JournalApp(cmd.Cmd):
    intro = '\nWelcome to the Journal DB Manager.  Type help or ? to list commands.\n'
    prompt = '>>> '
    # file = None

    print("Attempting to connect to db...\n")
    conn = connect_to_db()
    while not conn:
        conn = connect_to_db()

    # current logged-in info
    curr_login_id: int = None
    curr_role: Literal['author', 'editor', 'reviewer'] = None
    
    # --- basic commands ---
    def do_register(self, arg: str) -> None:
        args = shlex.split(arg)
        handle_register(args, self.conn)

    def do_login(self, arg: str) -> None:
        args = shlex.split(arg)
        (self.curr_login_id, self.curr_role) = handle_login(args, self.conn) or (None, None)        
    
    def do_resign(self, arg: str) -> None:
        resigned = handle_resign(self.conn, self.curr_login_id, self.curr_role, arg)
        if resigned:
            self.curr_login_id, self.curr_role = None, None
    
    def do_reject(self, arg: str) -> None:
        args = shlex.split(arg)
        handle_reject(self.conn, self.curr_login_id, self.curr_role, args)
    
    def do_submit(self, arg: str) -> None:
        args = shlex.split(arg)
        handle_submit(self.conn, self.curr_login_id, self.curr_role, args)
    
    def do_status(self, arg: str) -> None:
        handle_status(self.conn, self.curr_login_id, self.curr_role, arg)
        
    def do_exit(self, arg: str) -> bool:
        print("Shutting down...")
        self.conn.cmd_reset_connection()
        self.conn.close()
        return True



if __name__ == '__main__':
    JournalApp().cmdloop()
