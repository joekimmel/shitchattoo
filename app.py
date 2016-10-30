from collections import deque
import random

from flask import Flask, render_template, request, make_response
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Burton'
socketio = SocketIO(app, async_mode=None)

messages = deque()

names = [ "anonymous",
          "A. Nonny Moose",
          "coward",
          "kool koala",
          "you don't say",
          "they didn't say",
          "some rando",
          "I don't like typing my name",
          "Silent Sombrero",
          "Incognito Interrupter",
          "unknown uncle",
          "That Which Shall Not Be Named",
          "who?",
          "i dunno who said this",
          "Unnamed Undertaker"]


@app.route('/')
def index():    
    client_id = int(request.cookies.get('userID', "-1"))
    if(client_id == -1):
        app.client_counter += 1
        client_id = app.client_counter
        print ("client_counter is now: %d " % app.client_counter)

    resp = make_response(
        render_template('index.html', messages=messages, client_id = client_id, users = app.client_names))
    resp.set_cookie('userID', str(client_id))
    return resp

@socketio.on('trd_connect_event', namespace='/trd')
def connect_event(evt):
    print("we are running with " + socketio.async_mode)
    print("connect event"+evt['data'])

@socketio.on('trd_broadcast_event', namespace='/trd')
def broadcast_message(message):
    sender = message['sender'] if len(message['sender']) > 0 else random.choice(names)
    outbound = {
        'msg': message['msg'],
        'sender': sender}

    #keep a buffer of the last 20 messages for new clients who are joining...
    messages.append(outbound)
    while(len(messages) > 20 ):
        messages.popleft()

    emit('chat_message',
         outbound,
         broadcast=True)

@socketio.on('trd_name_change_event', namespace='/trd')
def name_change_message(message):
    app.client_names[message['id']] = {'name': message['name']}
    print('client ' + str(message['id']) + ' is now named: ' + message['name'])
    emit('names_message',
         app.client_names,
         broadcast=True)


if __name__ == '__main__':
    app.client_counter = 0
    app.client_names = {}
    socketio.run(app, debug=True, host='0.0.0.0')
