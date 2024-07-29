#from flask_socketio import SocketIO
from store.routes import app
from store import socketio


if __name__ == '__main__':
    #app.run(debug=True)
    #socketio = SocketIO(app)
    socketio.run(app, debug=True)
