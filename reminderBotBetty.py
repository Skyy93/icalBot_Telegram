#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Bot to read in .ics files and sending reminders
#
# Copyright (c) 2018
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""
This Bot uses the Updater class from the python-telegram-bot API and the icalender Parser

Please use your own Telegram-Token in the main-Class. After you started the bot it will run till you press Ctrl-C on the command line

Usage:
The Bot is started on the command line and reads in the icalender-file.
Send /start to initiate the reminder-service. Once a day the bot checks if there are any reminders for today and sends the messages to the subscribers.
If you don't want to get reminders send /stop for getting deleted from the database.
"""

from telegram.ext import Updater, CommandHandler
from icalendar import Calendar, Event
from datetime import datetime
import requests
import logging
import time
import sqlite3
import os

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Create DB and connect if it does not exists
if not os.path.isfile('data.db'):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE users
            (users text)''')
    conn.commit()
    conn.close()

# Imports ics-file
def importCalender():
    g = open('termine.ics','rb')
    gcal = Calendar.from_ical(g.read())
    g.close()
    return gcal

# Sends Reminders for today when first /start sent
def sendReminders(bot, job):
    events = todayReminder()
    for message in events:
        bot.send_message(job.context, message)

# Builds text for today 
def todayReminder():
    gcal = importCalender()
    today = datetime.today().date()
    botText = []
    for component in gcal.walk():
        if component.name == "VEVENT":
            if component.get('dtstart') is not None:
                if component.get('dtstart').dt.date() == today:
                    botText.append("Termin: " +str(component.get('summary')) + "\nDatum: " + str(component.get('DTSTART').dt.strftime("%d-%m-%Y %H:%M")) + "\nLocation: " + str(component.get('LOCATION')) + "\nBeschreibung: " + str(component.get('DESCRIPTION')))
                if component.subcomponents:
                    for a in component.to_ical().split():
                        if "TRIGGER" in str(a):
                            days = int("".join(filter(str.isdigit, str(a))))
                            if (component.get('dtstart').dt - timedelta(days=days)).date() == today:
                                botText.append("ERINNERUNG AN: \nTermin: " +str(component.get('summary')) + "\nDatum: " + str(component.get('DTSTART').dt.strftime("%d-%m-%Y %H:%M")) + "\nLocation: " + str(component.get('LOCATION')) + "\nBeschreibung: " + str(component.get('DESCRIPTION')))    
    return botText


# Define a few command handlers. These usually take the two arguments bot and
def start(bot, update, args, job_queue, chat_data):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    update.message.reply_text('Hi im Betty-Bot and will inform you about your events :)')
    chat_id = update.message.chat_id
    job = job_queue.run_once(sendReminders, 1, context=chat_id)
    chat_data['job'] = job

    rowsWithId = c.execute("SELECT * FROM users WHERE users='"+str(chat_id)+"'")
    if rowsWithId.fetchone() is None: 
        c.execute("INSERT INTO users VALUES ('"+str(chat_id)+"')")
    conn.commit()
    conn.close()

# Removes the users from the database
def stop(bot, update, args, job_queue, chat_data):
    update.message.reply_text('Okay, i delete you from the database and you will not get any further reminders.')
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    chat_id = update.message.chat_id
    c.execute("DELETE FROM users WHERE users='"+str(chat_id)+"'")
    conn.commit()
    conn.close()

# DailyJob for the reminders
def dailyJob(bot):
    while(1):
        time.sleep(86400)
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users")
        users = c.fetchall()
        events = todayReminder()
        for id in users:
            for message in events:
                bot.sendMessage(id[0],message)
            bot.sendMessage(id[0],"If you dont want to get this reminders send: /stop.")
        conn.commit()
        conn.close()   
        


# Error handling
def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    """Run bot."""
    updater = Updater("TOKEN")

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))
    dp.add_handler(CommandHandler("stop", stop,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))
    

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    #DailyUpdate
    dailyJob(updater.bot)



if __name__ == '__main__':
    main()
