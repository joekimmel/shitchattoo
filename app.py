from collections import deque

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Burton'
socketio = SocketIO(app, async_mode=None)

messages = deque()


@app.route('/')
def index():
    return render_template('index.html', messages=messages)

@socketio.on('trd_connect_event', namespace='/trd')
def connect_event(evt):
    print("connect event"+evt['data'])

@socketio.on('trd_broadcast_event', namespace='/trd')
def broadcast_message(message):
    outbound = {
        'msg': message['msg'],
        'sender': message['sender']}

    #keep a buffer of the last 20 messages for new clients who are joining...
    messages.append(outbound)
    while(len(messages) > 20 ):
        messages.popleft()

    emit('chat_message',
         outbound,
         broadcast=True)


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0')
