from flask import Flask, render_template, session, redirect, url_for, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from oauthlib.oauth2 import TokenExpiredError
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import os
import uuid 
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")
socketio = SocketIO(app)

# MongoDB Setup
mongo_client = MongoClient(os.getenv("MONGO_URI"))
db = mongo_client['gpt_chat_app']
messages_collection = db['messages']
users_collection = db['users']
sessions_collection = db['sessions']

# Google OAuth Setup
google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"), 
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ],
    redirect_url="/",
    offline=True, 
    reprompt_consent=True 
)

app.register_blueprint(google_bp, url_prefix="/login")

# OpenAI API
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ROOM_ID = "global-room"
SESSION_ID = "shared-session-id"


def save_message_to_db(room, session_id, user, message):
    try:
        messages_collection.insert_one({
            "session_id": SESSION_ID,
            "room_id": ROOM_ID,
            "user": user,
            "message": message,
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        print(f"Error saving message to database: {e}")


@app.route("/")
def index():
    if not google.authorized:
        return redirect(url_for("google.login"))

    try:
        resp = google.get("/oauth2/v2/userinfo")
        resp.raise_for_status()
    except TokenExpiredError:
        session.clear() 
        return redirect(url_for("google.login"))
    except Exception as e:
        session.clear()
        return f"Login error: {e}", 401

    user_info = resp.json()

    session['user'] = {
        'email': user_info["email"],
        'name': user_info.get("name"),
        'profile_pic': user_info.get("picture")
    }


    # Update user information in MongoDB
    users_collection.update_one(
        {"email": user_info["email"]},
        {
            "$set": {
                "name": user_info.get("name"),
                "profile_pic": user_info.get("picture")
            },
            "$setOnInsert": {"created_at": datetime.utcnow()}
        },
        upsert=True
    )

    session['session_id'] = SESSION_ID

    existing_sessions = sessions_collection.find_one({"session_id": SESSION_ID})

    if existing_sessions:
        participant_emails = [p["email"] for p in existing_sessions.get("participants", [])]
        if user_info["email"] not in participant_emails:
            sessions_collection.update_one(
                {"session_id": SESSION_ID},
                {
                    "$push": {"participants": {"email": user_info["email"]}},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
    else:
        sessions_collection.insert_one({
            "room_id": ROOM_ID,
            "session_id": SESSION_ID,
            "participants": [{"email": user_info["email"]}],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

    history = list(messages_collection.find({"session_id": SESSION_ID}).sort("timestamp", 1))

    return render_template("chat.html", user=session['user'], room=ROOM_ID, history=history)


@app.route("/login")
def login():
    return redirect(url_for("google.login"))

@app.route("/logout")
def logout():
    session.pop('user', None)
    session.pop('room', None)
    session.pop('google_oauth_token', None)
    return redirect(url_for('login')) 


@socketio.on("join")
def handle_join(data):
    room = data['room'] 
    user = session.get('user')

    join_room(room)
    print(f"User joined room: {room}")  

    existing_room = sessions_collection.find_one({"room_id": room})

    if existing_room:
        # Use the existing session ID from the database
        session_id = existing_room['session_id']

        # Add the user to the participants list in the database
        sessions_collection.update_one(
            {"session_id": session_id},
            {
                "$addToSet": {"participants": {"email": user["email"], "role": "human"}},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        # Assign the session ID to the user's session
        session['session_id'] = session_id
    else:
        # If no session exists, create new one
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id

        sessions_collection.insert_one({
            "session_id": SESSION_ID,
            "room_id": ROOM_ID,
            "participants": [{"email": user["email"], "role": "human"}],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

    emit("receive_message", {"user": user, "message": f"{user["email"]} has joined the room.", 'room': room}, room=room)



@socketio.on('send_message')
def handle_send_message(data):
    room = data.get('room')
    if not room:
        print("Error: No room provided for the message.")
        return

    print(f"Received message for room: {room}")
    message = data['message']
    user = session.get('user')
    session_id = session.get('session_id')

    save_message_to_db(ROOM_ID, SESSION_ID, user, message)

    emit('receive_message', {'user': user, 'message': message,'room': room}, room=room)

    if "GPT" in data.get('target', ''):
        gpt_reply = ask_gpt(message)

        messages_collection.insert_one({
            "session_id": SESSION_ID,
            "room": ROOM_ID,
            "user": "GPT",
            "role": "gpt",
            "message": gpt_reply,
            "timestamp": datetime.utcnow()
        })

        emit("receive_message", {"user": "GPT", "message": gpt_reply, "room": room}, room=room)

def ask_gpt(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error from GPT: {str(e)}"

@app.route("/new_chat", methods=["POST"])
def new_chat():

    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    session_id = str(uuid.uuid4())
    sessions_collection.insert_one({
        "session_id": session_id,
        "user_id": user, 
        "participants": [{"email": user['email'], "role": "human"}],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })

    return jsonify({"session_id": session_id})


@app.route("/chat_sessions")
def chat_sessions():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    chats = sessions_collection.find({"participants.email": user['email']}).sort("updated_at", -1)

    return jsonify([
        {"chat_id": str(chat["_id"]), "created_at": chat.get("created_at", "Unknown")}
        for chat in chats
    ])

@app.route("/chat/<chat_id>")
def chat_history(chat_id):
    try:
        chat = sessions_collection.find_one({"_id": ObjectId(chat_id)})
        if not chat:
            return "Chat not found", 404

        session_id = chat.get("session_id")
        if not session_id:
            return "Session ID missing", 400

        history = list(messages_collection.find({"session_id": chat["session_id"]}).sort("timestamp", 1))
        return jsonify([
            {"user": msg["user"], "message": msg["message"], "timestamp": msg["timestamp"].isoformat()}
            for msg in history
        ])
    except Exception as e:
        return str(e), 400

if __name__ == "__main__":
    socketio.run(app, debug=True)
