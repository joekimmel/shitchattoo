from collections import deque, defaultdict
import random

from flask import Flask, render_template, request, make_response
from flask_socketio import SocketIO, emit, join_room #, leave_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Burton'
socketio = SocketIO(app, async_mode=None)

messages = {"main": deque()}

chat_rooms = ["main"]

names = [ "anonymous",
          "anon angler",
          "A. Nonny Moose",
          "kool koala",
          "you don't say",
          "some rando",
          "I like default names",
          "Silent Sombrero",
          "Incognito Interrupter",
          "unknown uncle",
          "That Which Shall Not Be Named",
          "who?",
          "i dunno who said this",
          "Unnamed Undertaker"]

client_counter = 0
clients = {}
name_to_client_id_map = {}
rooms_to_clients_map = defaultdict(list)

#unclear why we have to do this so often -- clients doesn't persist cleanly ...
def make_new_client(client_id, room_id = ''):
    global clients
    global name_to_client_id_map
    global rooms_to_clients_map

    new_name = random.choice(names)
    while(new_name in name_to_client_id_map):
        new_name = random.choice(names)

    clients[client_id] = {
        'name': new_name,
        'id': client_id,
        'connected': True,
        'room_id': room_id
        }

    name_to_client_id_map[new_name] = client_id
    rooms_to_clients_map['main'].append(client_id)
    ensure_client_counter(client_id)


def ensure_client_counter(client_id):
    global client_counter
    if(client_id > client_counter): # happens on server restart
        client_counter = client_id + 1

def get_active_users():
    global clients
    global rooms_to_clients_map

    #connected_clients = [clients[x] for x in clients if clients[x]['connected']]

    ret_clients = {}
    for room in rooms_to_clients_map:
        cli_dict = {}
        for client_id in rooms_to_clients_map[room]:
            if clients[client_id]['connected']:
                cli_dict[client_id] = {'id': client_id, 'name': clients[client_id]['name']}
        ret_clients[room] = cli_dict

    #for cli in connected_clients:
    #    ret_clients[cli['id']] = {'id': cli['id'], 'name': cli['name']}

    return ret_clients

@app.route('/')
def index():
    global client_counter
    global clients
    global chat_rooms

    client_id = int(request.cookies.get('userIDv2', "-1"))
    if(client_id == -1):
        client_counter += 1
        client_id = client_counter
        print ("client_counter is now: %d " % client_counter)

    if (client_id not in clients):
        make_new_client(client_id, '')


    #if they're reloading the page they may be marked as disconnected at this point
    clients[client_id]['connected'] = True

    resp = make_response(
        render_template('index.html',
                        messages = messages,
                        client_id = client_id,
                        users = get_active_users(),
                        chat_rooms = chat_rooms
                        )
        )
    resp.set_cookie('userIDv2', str(client_id))

    # seems like getting all browsers to refresh the page on e.g. "back" takes a few settings.
    resp.headers['Cache-Control'] = "no-cache, no-store, must-revalidate"
    resp.headers['Pragma'] = "no-cache"
    resp.headers['Expires'] = 0

    return resp

@socketio.on('trd_connect_event', namespace='/trd')
def connect_event(evt):
    global clients

    if(evt['client_id'] not in clients):
        print("for some reason we didn't already have the client_id?")
        make_new_client(evt['client_id'], request.sid)
    else:
        clients[evt['client_id']]['room_id'] = request.sid

    clients[evt['client_id']]['connected'] = True
    print("we are running with " + socketio.async_mode)
    print("connect event for client id: "+str(evt['client_id']))
    join_room('main')
    emit('names_message',
         get_active_users(),
         broadcast=True)

# disconnect events do not work; TODO: implement heartbeat/timestamp scheme to detect when clients leave.
#@socketio.on('trd_disconnect_event', namespace='/trd')
def disconnect_event(evt):
    global clients
    if(evt['client_id'] not in clients):
        print("for some reason we didn't already have the client_id?")
        make_new_client(evt['client_id'], request.sid)
    clients[evt['client_id']]['connected'] = False
    print("DISconnect event for client id: "+str(evt['client_id']))
    emit('names_message',
         get_active_users(),
         broadcast=True)


def send_private_message(message):
    username = ''
    pieces_in_name = 1
    pieces = message['msg'][1:].split()
    while(username not in name_to_client_id_map and pieces_in_name < len(pieces)):
        username = ' '.join(pieces[:pieces_in_name])
        pieces_in_name += 1
    if username in name_to_client_id_map:
        sender = message['sender'] if len(message['sender']) > 0 else random.choice(names)
        target_client = clients[name_to_client_id_map[username]]
        outbound = {
            'msg': "(PRIVATE) " + message['msg'],
            'timestamp': message['timestamp'],
            'sender': sender}
        emit('chat_message',
                outbound,
                room = target_client['room_id'])
    else:
        print("tried to send private message to {0} but they're not in the names map!".format(username))

def send_message_all(message):
    sender = message['sender'] if len(message['sender']) > 0 else random.choice(names)
    ensure_client_counter(message['client_id'])

    room = message['room']
    outbound = {
        'msg': message['msg'],
        'timestamp': message['timestamp'],
        'room': room,
        'sender': sender}

    #keep a buffer of the last 20 messages for new clients who are joining...
    messages[room].append(outbound)
    while(len(messages[room]) > 20 ):
        messages[room].popleft()

    print("broadcasting message for room: "+room)
    emit('chat_message',
         outbound,
         room = room)

@socketio.on('trd_broadcast_event', namespace='/trd')
def broadcast_message(message):
    global messages
    global name_to_client_id_map
    global clients

    if(message['msg'] == ""):
        return

    if(message['msg'][0] == '@'):
        pass#send_private_message(message)
    else:
        send_message_all(message)

@socketio.on('trd_join_room_event', namespace='/trd')
def client_join_room_event(message):
    _join_room(message)

def _join_room(message):
    global rooms_to_clients_map

    rooms_to_clients_map[message['room']].append(message['client_id'])
    join_room(message['room'])
    emit('names_message',
         get_active_users(),
         room=message['room'])


@socketio.on('trd_new_chat_room', namespace='/trd')
def new_chatroom(message):
    global chat_rooms
    global messages

    room = message['room_name']
    chat_rooms.append(room)
    messages[room] = deque()
    join_room(room)
    emit('new_chat_room', message, broadcast=True)


@socketio.on('trd_name_change_event', namespace='/trd')
def name_change_message(message):
    global clients
    global name_to_client_id_map

    ensure_client_counter(message['client_id'])

    del name_to_client_id_map[clients[message['client_id']]['name']]
    clients[message['client_id']]['name'] = message['name']
    name_to_client_id_map[message['name']] = message['client_id']

    print('client ' + str(message['client_id']) + ' is now named: ' + message['name'])
    emit('names_message',
         get_active_users(),
         broadcast=True)


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0')
