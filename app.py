from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms, disconnect, close_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Burton'
socketio = SocketIO(app, async_mode=None)



@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('trd_connect_event', namespace='/trd')
def connect_event(evt):
    print("connect event"+evt['data'])

@socketio.on('trd_broadcast_event', namespace='/trd')
def broadcast_message(message):
    print("broadcast recieved from: " + message['sender'] + "message: "+message['msg'])
    emit('chat_message',
         {'msg': message['msg'],
           'sender': message['sender']},
         broadcast=True)


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0')
