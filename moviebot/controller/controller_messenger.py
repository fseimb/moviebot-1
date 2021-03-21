
import json
import sqlite3
from moviebot.agent.agent import Agent
from moviebot.controller.controller import Controller
from moviebot.utterance.utterance import UserUtterance
from flask import Flask, request
import requests
from os import environ
#from imdb import IMDb
#import tokens
#import app
from moviebot.database.database import DataBase
from moviebot.nlu.annotation.slots import Slots
from moviebot.dialogue_manager.dialogue_state import DialogueState
import time
ACCESS_TOKEN = 'EAAF5ZA8L6hnUBAH9CjUB2YExM9WMvi3CitPQOzivVwnC3NEKZB7pxhxHeUrXmEDFMqTBEfJZCkV5MUGV3hyT2vppi3w80YBHzO5oMow7iOAfQxEpunp2w2EVSDn1Sq1e32ItNDdQMZAkzdjxMQSdzzKhcy6nsrj3dBIDUfalJt1XYcc7dppy'

class ControllerMessenger(Controller):

    def __init__(self):
        self.agent = {}
        self.user_options = {}
        self.payload = ""
        self.user_options = {}
        self.agent_response = {}
        self.movie_id = ""
        self.configuration = {}
        self.info = {}
        self.action_list = [
        {"payload": "start", "action": self.instructions},
        {"payload": "help", "action": self.help}
        ]
        #images.upload_images()
        self.start = {"get_started": {"payload": "start"}}
        #self.greeting()
        self.get_started()
        
    def get_started(self):
        return requests.post('https://graph.facebook.com/v2.6/me/messenger_profile?access_token='+ACCESS_TOKEN, json=self.start).json()

    def greeting(self):
        greeting = {
            "locale": "default",
            "text": "Hello!"
            }
        return requests.post('https://graph.facebook.com/v10.0/me/messenger_profile?access_token='+ACCESS_TOKEN, json=greeting).json()

    def send_reply(self):
        text = messages.text
        text['recipient']['id'] = user_id
        text['message']['text'] = "test"
        return requests.post('https://graph.facebook.com/v9.0/me/messages?access_token='+ACCESS_TOKEN, json=text).json()

    def persistent_menu(self):
        menu = messages.menu
        menu['psid'] = user_id
        return requests.post('https://graph.facebook.com/v2.6/me/messenger_profile?access_token='+ACCESS_TOKEN, json=menu).json()

    def get_info(self, movie_id):
        for row in self.lookup().execute(f'SELECT * FROM movies_v2 WHERE ID="{movie_id}"'):
            self.info['title'] = row[1]
            self.info['rating'] = row[4]
            self.info['duration'] = row[6]
            self.info['summary'] = row[10]
            self.info["image_url"] = row[9]
            self.info['imdb_link'] = row[12]

    def lookup(self):
        conn = sqlite3.connect(self.get_db())
        c = conn.cursor()
        return c

    def strip_tuple(self, element):
        for e in element:
            return e

    def get_db(self):
        db_path = self.configuration['DATA']['db_path']
        print("path: ", db_path)
        return db_path

    def execute_agent(self, configuration):
        self.configuration = configuration
        self.configuration['new_user'] = {}
        #self.agent = Agent(configuration)
        #self.agent.initialize()
        self.get_db()
        #self.agent_response, self.user_options = self.agent.start_dialogue()

    def start_agent(self, user_id):
        if user_id not in self.agent:
            self.agent[user_id] = Agent(self.configuration)
            self.user_options[user_id] = {}
            self.agent[user_id].initialize(user_id)
            self.agent_response[user_id], self.user_options[user_id] = self.agent[user_id].start_dialogue()

    def typing_on(self, user_id):
        typing = {
            "recipient":{"id": user_id},
            "sender_action": "typing_on"
        }
        return requests.post('https://graph.facebook.com/v2.6/me/messages?access_token='+ACCESS_TOKEN, json=typing).json()

    def mark_seen(self, user_id):
        mark_seen = {
            "recipient": {"id": user_id},
            "sender_action": "mark_seen"
            }
        return requests.post('https://graph.facebook.com/v2.6/me/messages?access_token='+ACCESS_TOKEN, json=mark_seen).json()

    def send_template(self, user_id, buttons):
        template = self.movie_template(user_id, buttons[0:3],
            self.info['image_url'], self.info['imdb_link'], self.info['summary'], self.info['title'],
            self.info['rating'], self.info['duration'])
        return requests.post('https://graph.facebook.com/v9.0/me/messages?access_token='+ACCESS_TOKEN, json=template).json()

    def create_buttons(self, user_id, options):
        buttons = []
        for option in options:
            if type(option) == type("string"):
                print("string option: ", option)
                buttons.append(self.create_button(option))
            else:
                for item in option:
                    print("item: ", item)
                    buttons.append(self.create_button(item))
        self.template = self.buttons_template(buttons, user_id)
        return buttons
        
    def create_button(self, payload):
        button = {"type": "postback", "title": payload, "payload": payload}
        return button

    def get_movie_id(self, response):
        if "/tt" in response:
            start = response.find("/tt")
            movie_id = response[start+3:start+10]
            return movie_id

    def continue_dialogue(self, user_id):
        user_utterance = UserUtterance({'text': self.payload})
        self.agent_response[user_id], self.user_options[user_id] =  \
            self.agent[user_id].continue_dialogue(
            user_utterance, self.user_options[user_id]
        )
        self.movie_id = self.get_movie_id(self.agent_response[user_id])
        self.get_info(self.movie_id)
        print("agent_response: ", self.agent_response[user_id])

    def send_message(self, user_id):
        self.continue_dialogue(user_id)
        if self.user_options[user_id]:
            buttons = self.create_buttons(user_id, self.user_options[user_id].values())
            if "**" in self.agent_response[user_id]:
                self.send_template(user_id, buttons)
            else: 
                template = self.buttons_template(buttons, user_id)
                self.send_buttons(template)
        else: 
            text = self.text(user_id, self.agent_response[user_id])
            return requests.post('https://graph.facebook.com/v9.0/me/messages?access_token='+ACCESS_TOKEN, json=text).json()

    def text(self, user_id, message):
        text = {
            'recipient': {'id': user_id},
            'message': {'text': message}
        }
        return text

    def send_buttons(self, template):
        return requests.post('https://graph.facebook.com/v2.6/me/messages?access_token='+ACCESS_TOKEN, json=template).json()
    
    def buttons_template(self, buttons, user_id):
        template = {
            "recipient":{ "id": user_id},
            "message":{
            "attachment":{
                "type":"template",
                "payload":{
                "template_type":"button",
                "text":self.agent_response[user_id],
                "buttons":buttons
                }
            }
            }
        }
        return template

    def get_started(self):
        return requests.post('https://graph.facebook.com/v2.6/me/messenger_profile?access_token='+ACCESS_TOKEN, json=self.start).json()

    def action(self, payload, recipient_id):
      
        self.start_agent(recipient_id)
        self.typing_on(recipient_id)
        self.mark_seen(recipient_id)
        self.payload = payload
        #time.sleep(2)
        for item in self.action_list:
            if payload.lower() == item['payload']:
                func = item.get('action')
                return func()
        return self.send_message(recipient_id)

    def quick_reply(psid):
      quickreply= {
      'messaging_type':'RESPONSE',
        'recipient':{'id':psid},
        'message':{
          'text': "More information",
          'quick_replies':[]
        }
        
      }
      return quickreply

    def movie_template(self, user_id, buttons, poster, url, plot, title, rating, duration):
        template = {
            "recipient":{ "id": user_id},
            "message":{
            "attachment":{
                "type":"template",
                "payload":{
                "template_type":"generic",
                "elements":[
                    {
                    "title":title + " " + str(rating) + " " + str(duration) + " min",
                    "image_url":poster,
                    "subtitle":plot,
                    "default_action": {
                        "type": "web_url",
                        "url": url,
                        "webview_height_ratio": "tall",
                    },
                    "buttons": buttons
                    }
                ]
                }
            }
            }
        }
        return template

    def help(self):
        self.instructions(True)
        # help = "To start the conversation, issue \"/start\", say Hi/Hello, or simply " \
        #         "enter you preferences (\"I want a horror movie from the 90s\").\n\n" \
        #         "To restart the recommendation process, issue \"/restart\".\n\n" \
        #         "To end the conversation, issue \"/exit\" or say Bye/Goodbye.\n\n" \
        #         "To see these instructions again, issue: \"/help\"." 
        # return requests.post('https://graph.facebook.com/v9.0/me/messages?access_token='+ACCESS_TOKEN, json=self.text(help)).json()

    def instructions(self, help=False):
        response =  "To start the conversation, issue \"/start\", say Hi/Hello, or simply " \
                "enter you preferences (\"I want a horror movie from the 90s\").\n\n" \
                "To restart the recommendation process, issue \"/restart\".\n\n" \
                "To end the conversation, issue \"/exit\" or say Bye/Goodbye.\n\n" \
                "To see these instructions again, issue: \"/help\"." 

        instructions = 'Hi there. I am IAI MovieBot, your movie recommending buddy. ' \
                       'I can recommend you movies based on your preferences.\n' \
                       'I will ask you a few questions and based on your answers, ' \
                       'I will try to find a movie for you.\n\n' 
        if help is False:
            response = instructions + response
        return requests.post('https://graph.facebook.com/v9.0/me/messages?access_token='+ACCESS_TOKEN, json=self.text(response)).json()
         

    # def send_quickreply(self):

#     quickreply = messages.qreply(user_id)
#     quick_replies = []
#     for option in self.user_options.values():
#         if type(option) == type("string"):
#             quick_replies.append(messages.create_reply(option, option))
#         else:
#             for item in option:
#                 quick_replies.append(messages.create_reply(item, item))
#     quickreply['message']['quick_replies'] = quick_replies
#     return requests.post(messages.quickreply, json=quickreply).json()

# menu = {
#     "psid": "",

#     "persistent_menu": [
#         {
#             "locale": "default",
#             "composer_input_disabled": False,
#             "call_to_actions": [
#                 {
#                     "type": "postback",
#                     "title": "Talk to an agent",
#                     "payload": "CARE_HELP"
#                 },
#                 {
#                     "type": "postback",
#                     "title": "Outfit suggestions",
#                     "payload": "CURATION"
#                 },
#                 {
#                     "type": "web_url",
#                     "title": "Shop now",
#                     "url": "https://wikipedia.com/",
#                     "webview_height_ratio": "full"
#                 }
#             ]
#         }
#     ]
# }