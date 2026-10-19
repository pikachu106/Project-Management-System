from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_session_management'

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
    if current_user['role'] == 'developer':
        filtered = [p for p in projects if p['developer_username'] == current_user['username']]
        return jsonify(filtered)
    
    return jsonify(projects)

@app.route('/api/projects', methods=['POST'])
def create_project():
    if 'user' not in session or session['user']['role'] != 'manager':
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    dev_username = data.get('developer_username')
    dev_user = users.get(dev_username)
    dev_display_name = dev_user['name'] if dev_user else dev_username

    new_project = {
        "id": str(uuid.uuid4())[:8],
        "name": data.get('name'),
        "developer_username": dev_username,
        "developer": dev_display_name,
        "deadline": data.get('deadline'),
        "status": "In Progress",
        "subtasks": [],
        "comments": []
    }
    projects.append(new_project)
    return jsonify(new_project), 201

@app.route('/api/projects/<project_id>/subtasks', methods=['POST'])
def add_subtask(project_id):
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    project = next((p for p in projects if p['id'] == project_id), None)
    if project:
        project['subtasks'].append({"name": data.get('subtaskName'), "completed": False})
        return jsonify(project), 200
    return jsonify({"error": "Project not found"}), 404

@app.route('/api/projects/<project_id>/complete', methods=['PATCH'])
def complete_project(project_id):
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    project = next((p for p in projects if p['id'] == project_id), None)
    if project:
        project['status'] = "Completed"
        return jsonify(project), 200
    return jsonify({"error": "Project not found"}), 404

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
            "text": data.get('text'),
            "time": now
        })
        return jsonify(project), 200
    return jsonify({"error": "Project not found"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)