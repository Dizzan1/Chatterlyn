# Chatterlyn

Chatterlyn is a real-time chat web application built with Python, FastAPI, Jinja2, SQLAlchemy, SQLite, Bootstrap, and WebSockets. It provides user authentication, public and private chat rooms, message history, unread message counters, member lists, and invitation links for private rooms.

https://github.com/user-attachments/assets/a5ad3a33-66c8-43c5-9e27-19470ab41182

## Features

- Real-time messaging with WebSockets
- User registration, login, logout, and secure cookie-based sessions
- Password hashing with Argon2 through `pwdlib`
- Public chat rooms that users can discover and join
- Private chat rooms with owner-generated invitation links
- Persistent message history stored in SQLite by default
- Unread message counters in the chat sidebar
- Chat member list and live member count updates
- Server-side validation for usernames, passwords, and chat names
- Jinja2 templates with Bootstrap-based styling

## Tech Stack

- **Backend:** FastAPI
- **Frontend:** Jinja2 templates, Bootstrap, JavaScript
- **Real-time communication:** WebSockets
- **Database:** SQLite by default, configurable through `DATABASE_URL`
- **ORM:** SQLAlchemy async
- **Authentication:** JWT stored in HTTP-only cookies
- **Password hashing:** Argon2 via `pwdlib`

## Project Structure

```text
Chatterlyn-main/
+-- main.py                  # FastAPI application entry point
+-- config.py                # Environment-based configuration
+-- requirements.txt         # Python dependencies
+-- db/                      # SQLite database location
+-- modules/
|   +-- connection_manager.py
|   +-- database.py
|   +-- dependencies.py
|   +-- models.py
|   +-- schemas.py
|   +-- utils.py
+-- routers/
|   +-- auth.py              # Home, register, login, logout
|   +-- chat.py              # Chat pages, rooms, members, invites
|   +-- websocket.py         # WebSocket endpoint
+-- static/                  # CSS, JavaScript, fonts, and images
+-- templates/               # Jinja2 HTML templates
```

## Requirements

- Python 3.11 or newer recommended
- `pip`
- A virtual environment is recommended

## Installation

1. Clone or download the project.

2. Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

3. Install the dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=change-this-secret-key
SESSION_SECRET_KEY=change-this-session-secret-key
DATABASE_URL=sqlite+aiosqlite:///db/chatterlyn.db
COOKIE_SECURE=False
```
Generate the secret keys:

```bash
openssl rand -hex 32
```

### Variables

- `SECRET_KEY`: Required. Used to sign JWT tokens.
- `SESSION_SECRET_KEY`: Optional. Used by the session middleware. If not set, `SECRET_KEY` is used.
- `DATABASE_URL`: Optional. Defaults to `sqlite+aiosqlite:///db/chatterlyn.db`.
- `COOKIE_SECURE`: Optional. Set to `True` when running behind HTTPS in production.

## Running the Application

Start the development server:

```bash
python main.py
```

Or run it directly with Uvicorn:

```bash
uvicorn main:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

When the application starts, it creates the database tables automatically if they do not exist and creates a default public room named `General`.

## Basic Usage

1. Register a new account.
2. Log in to access the chat area.
3. Join the default `General` room or browse available public rooms.
4. Create a public or private chat room.
5. For private rooms, the room owner can generate an invitation link.
6. Send messages in real time and switch between chats from the sidebar.

## Notes

- The default database is stored at `db/chatterlyn.db`.
- WebSocket authentication uses the same HTTP-only cookie created during login.
- Private chat invitation links are JWT-based and expire after 10 minutes.
- The JWT that identifies the user expires after one day.
- The `General` chat room is mandatory and cannot be left.

## License

This project is licensed under the GNU Affero General Public License v3.0. See the `LICENSE` file for details.

If you need to use this project under different terms (for example, a more permissive license), please contact me to discuss alternative licensing options.
