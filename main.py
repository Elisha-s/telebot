#!/usr/bin/env python3

try:
    import mysql.connector
    from mysql.connector import Error
    import yaml
    import re
    import telebot
except ModuleNotFoundError:
    print("Couldn't Import Libraries")
    print("Kindly run:")
    print("")
    print("\tpip install -r requirements.txt")
    exit(1)


___version___ = "1.15"
___name___ = "Upvote Bot"

# Global Variable(s)
BOT_TOKEN = ""
DB_HOST = ""
DB_USER = ""
DB_PASS = ""
DB_NAME = ""


# Parse SECRETS from "config.yaml" file
def parse_secrets():
    try:
        with open("config.yaml", "r") as config:
            return yaml.load(config, Loader=yaml.FullLoader)
    except FileNotFoundError:
        print("ERROR: 'config.yaml' file not found")
        print("")
        print("Rename 'sample_config.yaml' to 'config.yaml'")
        exit(1)


def set_secrets():
    global BOT_TOKEN, DB_HOST, DB_USER, DB_PASS, DB_NAME
    SECRETS = parse_secrets()
    BOT_TOKEN = SECRETS["BOT_TOKEN"]
    DB_HOST = SECRETS["DB_HOST"]
    DB_USER = SECRETS["DB_USER"]
    DB_PASS = SECRETS["DB_PASS"]
    DB_NAME = SECRETS["DB_NAME"]
    if not (BOT_TOKEN and DB_HOST and DB_USER and DB_PASS and DB_NAME):
        print("Empty Secrets!")
        exit(1)


def create_connection(db_host, db_user, db_pass, db_name):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=db_host,
            user=db_user,
            passwd=db_pass
        )
        cursor = connection.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS {0};".format(db_name))
        cursor.close()
        print("Connection to MySQL DB successful")
    except Error as e:
        print(f"The error '{e}' occurred")
        print("ERROR: Connection to MySQL DB failed")
        exit(1)
    connection = mysql.connector.connect(
            host=db_host,
            user=db_user,
            passwd=db_pass,
            database=db_name
        )
    return connection


set_secrets()
connection = create_connection(DB_HOST, DB_USER, DB_PASS, DB_NAME)
db_cursor = connection.cursor()
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="MARKDOWNV2")


# Function to check whether or not a given Table Exists in Database
# Function Arguments: DB Connection, Table Name
# Returns True or False depending upon the result
def check_table_exists(dbcon, tablename):
    dbcur = dbcon.cursor()
    dbcur.execute("""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = '{0}'
        """.format(tablename.replace('\'', '\'\'')))
    if dbcur.fetchone()[0] == 1:
        dbcur.close()
        return True
    dbcur.close()
    return False


# Function to create a Table in Database
def table_provider(table_name):
    SQL = f"""CREATE TABLE {table_name} (
        message_id INT NOT NULL,
        COUNTER INT,
        user_id LONGTEXT,
        PRIMARY KEY (message_id));"""
    db_cursor.execute(SQL)
    print(f"Table ({table_name}) created into DB successfully.")


def checker(id, list):
    for element in list:
        if int(element) == id:
            return False
    return True


def send_message(message, text_to_send):
    try:
        bot.send_message(message.chat.id, text_to_send, reply_to_message_id=message.reply_to_message.message_id)
    except Exception:
        print("Sending Message to Telegram Failed")
        print(text_to_send)


# Trigger(s) for the upvote command
@bot.message_handler(commands=["upvote"])
@bot.message_handler(regexp="^\\+1(\\s|$)")
def plus_one(message):
    if message.chat.type == "group" or message.chat.type == "supergroup":
        if message.reply_to_message is not None:
            if message.reply_to_message.from_user.id == message.from_user.id:
                bot.reply_to(message, "You can't upvote your own message\\!")
                return
            CHAT_ID = str(message.chat.id).replace("-", "_")
            if check_table_exists(connection, CHAT_ID) is False:
                table_provider(CHAT_ID)
            SQL = f"SELECT message_id FROM {CHAT_ID};"
            db_cursor.execute(SQL)
            myresults = db_cursor.fetchall()
            flag = 0
            for x in myresults:
                if x[0] == message.reply_to_message.id:
                    flag = 1
            if flag == 1:
                SQL1 = f"SELECT user_id FROM {CHAT_ID} WHERE message_id = {message.reply_to_message.id};"
                db_cursor.execute(SQL1)
                myresult = db_cursor.fetchall()
                if checker(message.from_user.id, re.split(" ", myresult[0][0])):
                    new_user_id = f"{myresult[0][0]} {message.from_user.id}"
                    QUERY = f"UPDATE {CHAT_ID} SET COUNTER = COUNTER + 1 WHERE message_id = {message.reply_to_message.id}"
                    db_cursor.execute(QUERY)
                    QUERY2 = f"UPDATE {CHAT_ID} SET user_id = '{new_user_id}' WHERE message_id = {message.reply_to_message.id}"
                    db_cursor.execute(QUERY2)
                    text_to_send = f"`{message.from_user.first_name}` gave \\+1 "
                    text_to_send += f"to `{message.reply_to_message.from_user.first_name}`'s message"
                    connection.commit()
                    print(f"Successfuly updated an entry for MessageID {message.reply_to_message.id}")
                    send_message(message, text_to_send)
                else:
                    print("User already upvoted the message")
                    text_to_send = f"[{message.from_user.first_name}](tg://user?id={message.from_user.id}) have already upvoted "
                    text_to_send += f"to `{message.reply_to_message.from_user.first_name}`'s message\\!"
                    send_message(message, text_to_send)
            elif flag == 0:
                QUERY = "INSERT INTO {0} VALUES({1}, 1, {2})".format(CHAT_ID, message.reply_to_message.id, message.from_user.id)
                db_cursor.execute(QUERY)
                connection.commit()
                print(f"Successfuly created an entry for Message ID {message.reply_to_message.id}")
                text_to_send = f"`{message.from_user.first_name}` gave \\+1 "
                text_to_send += f"to `{message.reply_to_message.from_user.first_name}`'s message"
                send_message(message, text_to_send)
        else:
            bot.reply_to(message, "You need to reply to a message\\!")
    elif message.chat.type == "private":
        bot.reply_to(message, f"Private Chats Not Are Supported by {___name___}")


def main():
    print(f"{___name___} Started, version {___version___}")
    try:
        print(f"Bot username: @{bot.get_me().username}")
        print(f"    Bot Name: {bot.get_me().first_name}")
        print("")
        print("    === Logs ===")
        print("")
    except Exception:
        print("ERROR: Initializing Bot Failed! Check your Bot Token")
        exit(1)
    bot.polling()


if __name__ == "__main__":
    main()
