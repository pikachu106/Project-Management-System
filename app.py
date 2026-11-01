from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_session_management'
app.config['TEMPLATES_AUTO_RELOAD'] = True

# In-memory storage for Users and Projects
users = {
    "manager1": {"username": "manager1", "password": "123", "role": "manager", "name": "Project Manager 1"},
    "alex": {"username": "alex", "password": "123", "role": "developer", "name": "Alex (Dev)"},
    "rahim": {"username": "rahim", "password": "123", "role": "developer", "name": "Rahim (Dev)"},
    "client1": {"username": "client1", "password": "123", "role": "client", "name": "Client 1"}
}

projects = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    name = data.get('name')

    if not username or not password or not role or not name:
        return jsonify({"error": "All fields are required"}), 400

    if username in users:
        return jsonify({"error": "Username already exists"}), 400

    users[username] = {
        "username": username,
        "password": password,
        "role": role,
        "name": name
    }
    return jsonify({"message": "Registration successful"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = users.get(username)
    if not user or user['password'] != password:
        return jsonify({"error": "Invalid username or password"}), 401

    session['user'] = {
        "username": user['username'],
        "role": user['role'],
        "name": user['name']
    }
    return jsonify({"message": "Login successful", "user": session['user']}), 200

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({"message": "Logged out"}), 200

@app.route('/api/current_user', methods=['GET'])
def get_current_user():
    if 'user' in session:
        return jsonify({"loggedIn": True, "user": session['user']})
    return jsonify({"loggedIn": False})

@app.route('/api/developers', methods=['GET'])
def get_developers():
    devs = [{"username": u['username'], "name": u['name']} for u in users.values() if u['role'] == 'developer']
    return jsonify(devs)

@app.route('/api/projects', methods=['GET'])
def get_projects():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    current_user = session['user']
    # Developer shudhu sei project-gulo dekhbe jate tar username assigned ache
    if current_user['role'] == 'developer':
        filtered = [p for p in projects if current_user['username'] in p.get('developer_usernames', [])]
        return jsonify(filtered)
    
    return jsonify(projects)

@app.route('/api/projects', methods=['POST'])
def create_project():
    if 'user' not in session or session['user']['role'] != 'manager':
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    # Multiple developers support (developer_usernames list)
    dev_usernames = data.get('developer_usernames', [])
    
    dev_display_names = [users.get(u)['name'] for u in dev_usernames if u in users]

    new_project = {
        "id": str(uuid.uuid4())[:8],
        "name": data.get('name'),
        "developer_usernames": dev_usernames,
        "developers": dev_display_names,
        "deadline": data.get('deadline'),
        "status": "In Progress",
        "subtasks": [],
        "comments": []
    }
    projects.append(new_project)
    return jsonify(new_project), 201

# 1. ONLY PROJECT MANAGER CAN COMPLETE PROJECT
@app.route('/api/projects/<project_id>/complete', methods=['PATCH'])
def complete_project(project_id):
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    current_user = session['user']
    if current_user['role'] != 'manager':
        return jsonify({"error": "Only Project Manager can mark the project as completed!"}), 403

    project = next((p for p in projects if p['id'] == project_id), None)
    if project:
        project['status'] = "Completed"
        return jsonify(project), 200
    return jsonify({"error": "Project not found"}), 404

# 2. MANAGER ADDS SUBTASK AND ASSIGNS TO A SPECIFIC DEVELOPER
@app.route('/api/projects/<project_id>/subtasks', methods=['POST'])
def add_subtask(project_id):
    if 'user' not in session or session['user']['role'] != 'manager':
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    project = next((p for p in projects if p['id'] == project_id), None)
    if project:
        subtask_item = {
            "id": str(uuid.uuid4())[:8],
            "name": data.get('subtaskName'),
            "assigned_to": data.get('assigned_to'),  # Developer username
            "completed": False
        }
        project['subtasks'].append(subtask_item)
        return jsonify(project), 200
    return jsonify({"error": "Project not found"}), 404

# 3. ONLY THE ASSIGNED DEVELOPER CAN COMPLETE THEIR SUBTASK
@app.route('/api/projects/<project_id>/subtasks/<subtask_id>/complete', methods=['PATCH'])
def complete_subtask(project_id, subtask_id):
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    current_user = session['user']
    if current_user['role'] != 'developer':
        return jsonify({"error": "Only developers can complete subtasks!"}), 403

    project = next((p for p in projects if p['id'] == project_id), None)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    subtask = next((s for s in project['subtasks'] if s['id'] == subtask_id), None)
    if not subtask:
        return jsonify({"error": "Subtask not found"}), 404

    # Check if the logged-in developer is the one assigned to this subtask
    if subtask['assigned_to'] != current_user['username']:
        return jsonify({"error": "You are not assigned to this subtask!"}), 403

    subtask['completed'] = True
    return jsonify(project), 200

@app.route('/api/projects/<project_id>/comments', methods=['POST'])
def add_comment(project_id):
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    project = next((p for p in projects if p['id'] == project_id), None)
    if project:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        project['comments'].append({
            "author": session['user']['name'],
            "role": session['user']['role'],
            "text": data.get('text'),
            "time": now
        })
        return jsonify(project), 200
    return jsonify({"error": "Project not found"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)