# GPT Multi-User Chat

**GPT Multi-User Chat** is a real-time web application that allows multiple participants (human or GPT) to interact with each other in a seamless, live-chat environment. This project enables users to engage in real-time conversations and integrates advanced technologies such as **Flask-Dance** for Google OAuth authentication, **Flask-SocketIO** for real-time messaging, and **MongoDB** for storing user data and chat sessions.

## Technologies Used

- **Backend**: Flask, Flask-Dance, Flask-SocketIO
- **Frontend**: HTML, CSS, JavaScript
- **Authentication**: Google OAuth via Flask-Dance
- **Database**: MongoDB
- **Real-Time Communication**: WebSockets (via Flask-SocketIO)
- **AI Integration**: OpenAI's GPT API (ChatGPT)

## Features

| Feature                | Description                                                      |
|------------------------|------------------------------------------------------------------|
| **Login System**        | Google OAuth via Flask-Dance                        |
| **Database**            | MongoDB for users, sessions, messages         |
| **WebSocket Chat**      | Real-time chat using Flask-SocketIO                   |
| **Human/GPT Roles**     | Dynamically assign each chat participant as GPT or user          |
| **GPT + Optional RAG**  | ChatGPT API integration          |
| **Chat History**        | Store full transcripts per user                          |

## Setup Instructions

### Prerequisites

Before getting started, ensure you have the following installed:

- **Python 3.7+** (for the backend)
- **pip** (Python package manager)

### Set up Environment Variables
1. Create a .env file in the root directory of the project.
2. Add the following environment variables to the .env file:

  FLASK_SECRET_KEY=your_flask_secret_key
  GOOGLE_CLIENT_ID=your_google_client_id
  GOOGLE_CLIENT_SECRET=your_google_client_secret
  MONGO_URI=your_mongodb_connection_string
  OPENAI_API_KEY=your_openai_api_key


### Clone the Repository

Clone the repository using Git:

```bash
git clone https://github.com/krishashah64/GPT-Multi-User-Chat.git




