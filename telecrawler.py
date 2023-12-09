#!/usr/bin/python3
# -*- coding: utf-8 -*-
#pip install cryptg - recommended for better performance
import configparser
import sqlite3
import time
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sync import TelegramClient
from telethon import functions, types
config = configparser.ConfigParser()
config.read("config.ini")
api_id = config['Telegram']['api_id']
api_hash = config['Telegram']['api_hash']
phone_number = config['Telegram']['phone']
username = config['Telegram']['username']
db_file = 'crawler.db'
search_seed = 'flores'
iterations=2048
iteration_sleep=.1
iteration_sleep_message=.1
con = sqlite3.connect(db_file)
#max allowed by telegram messages_limit = 1000000
messages_limit=2048
download_files=False
download_images_only=False
media_path='media'

def create_database():
    print("Creating database.")
    cur = con.cursor()
    cur.execute("""CREATE TABLE words (word text, UNIQUE (word))""")
    cur.execute("""CREATE TABLE search_history (word text, UNIQUE (word))""")
    cur.execute("""CREATE TABLE user_chat (userid text, chatid text)""")
    cur.execute("""CREATE TABLE messages (userid text, chatid text, message text)""")
    cur.execute("""INSERT INTO words (word) VALUES (?)""",(search_seed,))
    cur.execute("""CREATE TABLE users (id text,first_name text,last_name text,username text,phone text,status text,usernames text,UNIQUE (id))""")
    cur.execute("""CREATE TABLE chats (id text,title text,username text,participants_count integer,UNIQUE (id))""")
    con.commit()

def get_random_word():
    exists=True
    while exists:
        cur = con.cursor()
        query = cur.execute("SELECT word FROM words WHERE rowid > ( ABS(RANDOM()) % (SELECT max(rowid) FROM words)) LIMIT 1").fetchall()
        exists=search_history_exists(query[0][0])
    return query[0][0]

def check_database():
    try:
        cur = con.cursor()
        ans = cur.execute("SELECT max(rowid) FROM words").fetchall()
    except sqlite3.OperationalError:
        create_database()
    return True

def search_history_exists(word):
    cur = con.cursor()
    query = cur.execute("""SELECT EXISTS(SELECT 1 FROM search_history WHERE word=? LIMIT 1)""",(word,)).fetchall()
    if str(query[0][0]) == "1":
        return True
    return False

def user_exists(user_id):
    cur = con.cursor()
    query = cur.execute("""SELECT EXISTS(SELECT 1 FROM users WHERE id=? LIMIT 1)""",(user_id,)).fetchall()
    if str(query[0][0]) == "1":
        return True
    return False

def chat_exists(chat_id):
    cur = con.cursor()
    query = cur.execute("""SELECT EXISTS(SELECT 1 FROM chats WHERE id=? LIMIT 1)""",(chat_id,)).fetchall()
    if str(query[0][0]) == "1":
        return True
    return False

def insert_user(user):
    cur = con.cursor()
    cur.execute("""INSERT INTO users (id,first_name,last_name,username,phone,status,usernames) VALUES (?,?,?,?,?,?,?)""",(user.id,user.first_name,user.last_name,user.username,user.phone,str(user.status),str(user.usernames)))
    con.commit()
    return True

def insert_user_chat(userid,chatid):
    cur = con.cursor()
    cur.execute("""INSERT INTO user_chat (userid,chatid) VALUES (?,?)""",(userid,chatid))
    con.commit()
    return True

def insert_message(message,chatid):
    print('Inserting message {}'.format(message.text))
    cur = con.cursor()
    cur.execute("""INSERT INTO messages (userid,chatid,message) VALUES (?,?,?)""",(message.sender_id,chatid,message.text))
    con.commit()
    return True

def insert_chat(chat,username):
    print('Inserting chat {}'.format(chat.id))
    cur = con.cursor()
    cur.execute("""INSERT INTO chats (id,title,username,participants_count) VALUES (?,?,?,?)""",(chat.id,chat.title,username,chat.participants_count))
    con.commit()
    return True

def insert_words(sentence):
    sentence=str(sentence).replace('\n',' ')
    for word in sentence.split():
        cur = con.cursor()
        cur.execute("""insert or ignore into words (word) values (?)""",(word,))
        con.commit()
    return True

def insert_search_history(word):
    cur = con.cursor()
    cur.execute("""insert or ignore into search_history (word) values (?)""",(word,))
    con.commit()
    return True

def evaluate_user(user):
    #print('Evaluating user {} {} {}'.format(user.first_name,user.last_name, user.username))
    sentences=[str(user.first_name),str(user.last_name),str(user.username)]
    for sentence in sentences:
        insert_words(sentence)
    if not user_exists(user.id):
        insert_user(user)
    else:
        print('User {} already exists.'.format(user.id))
    time.sleep(iteration_sleep)
    return True

def evaluate_message(message,chatid,client):
    insert_words(message.text)
    if message.text != "" and message.text != None:
        insert_message(message,chatid)
    if download_images_only:
        client.download_media(message,media_path,thumb=-1)
    elif download_files:
        client.download_media(message,media_path)
    time.sleep(iteration_sleep_message)
    return True

def evaluate_chat(chat,client):
    username=''
    is_broadcast=True
    try:
        username=chat.username
    except AttributeError:
        username=''

    try:
        is_broadcast=chat.broadcast
    except AttributeError:
        is_broadcast=True

    print('Evaluating chat {} {}'.format(chat.title,username))
    if not chat_exists(chat.id):
        insert_chat(chat,username)
    else:
        print('Chat {} already exists.'.format(chat.id))
        return False
    sentences=[str(chat.title),str(username)]
    for sentence in sentences:
        insert_words(sentence)
    if not is_broadcast:
        print('Inserting users')
        user_list = client.get_participants(entity=chat,aggressive=True)
        for user in user_list:
            insert_user_chat(user.id,chat.id)
            evaluate_user(user)
    for message in client.iter_messages(chat,limit=messages_limit):
        evaluate_message(message,chat.id,client)
        #print('Message ',message.sender_id, ':', message)
    time.sleep(iteration_sleep)
    return True

def crawl(iterations):
    client = TelegramClient(phone_number, api_id, api_hash)
    client.connect()
    if not client.is_user_authorized():
        client.send_code_request(phone_number)
        client.sign_in(phone_number, input('Enter the code: '))
    check_database()
    for iteration in range(iterations):
        search=get_random_word()
        print('Searching for {}'.format(search))
        result = client(functions.contacts.SearchRequest( q=search, limit=100))
        print("Evaluating chats.")
        for chat in result.chats:
            evaluate_chat(chat,client)
        print("Evaluating loose users.")
        for user in result.users:
            evaluate_user(user)
        insert_search_history(search)

def main():
    crawl(iterations)

if __name__ == "__main__":
    main()

#SELECT u.username, c.title FROM users AS u  LEFT JOIN user_chat AS uc  ON u.id=uc.userid  LEFT JOIN chats AS c  ON uc.chatid = c.id;
