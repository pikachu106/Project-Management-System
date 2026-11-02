from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_session_management'
app.config['TEMPLATES_AUTO_RELOAD'] = True

users = {
    "manager1": {"username": "manager1", "password": "123", "role": "manager", "name": "Project Manager 1"},
    "alex": {"username": "sunshine", "password": "123", "role": "developer", "name": "sunshine (Dev)"},
    "rahim": {"username": "sundaz", "password": "123", "role": "developer", "name": "sundaz (Dev)"},
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

@app.route('/api/users/delete', methods=['DELETE'])
def delete_account():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    username = session['user']['username']
    
    for p in projects:
        if username in p.get('developer_usernames', []):
            p['developer_usernames'].remove(username)
        if username in p.get('developers', []):
            dev_display = users[username]['name'] if username in users else username
            if dev_display in p['developers']:
                p['developers'].remove(dev_display)
        for st in p.get('subtasks', []):
            if st.get('assigned_to') == username:
                st['assigned_to'] = "Unassigned"

    if username in users:
        del users[username]
        
    session.pop('user', None)
    return jsonify({"message": "Account deleted successfully"}), 200

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
    today = datetime.now().strftime("%Y-%m-%d")

    for p in projects:
        if p['status'] != 'Completed' and p['deadline'] < today:
            p['status'] = 'Overdue'

    if current_user['role'] == 'developer':
        filtered = [p for p in projects if current_user['username'] in p.get('developer_usernames', [])]
        return jsonify(filtered)
    
    return jsonify(projects)

@app.route('/api/projects', methods=['POST'])
def create_project():
    if 'user' not in session or session['user']['role'] != 'manager':
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
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

@app.route('/api/projects/<project_id>/complete', methods=['PATCH'])
def complete_project(project_id):
    if 'user' not in session or session['user']['role'] != 'manager':
        return jsonify({"error": "Only Project Manager can mark the project as completed!"}), 403

    project = next((p for p in projects if p['id'] == project_id), None)
    if project:
        all_done = all(st['completed'] for st in project['subtasks']) if project['subtasks'] else False
        if not all_done and len(project['subtasks']) > 0:
            return jsonify({"error": "All subtasks must be completed by developers before marking project complete!"}), 400
        
        project['status'] = "Completed"
        return jsonify(project), 200
    return jsonify({"error": "Project not found"}), 404

@app.route('/api/projects/<project_id>/subtasks', methods=['POST'])
def add_subtask(project_id):
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    current_user = session['user']
    project = next((p for p in projects if p['id'] == project_id), None)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    if current_user['role'] == 'developer' and current_user['username'] not in project.get('developer_usernames', []):
        return jsonify({"error": "You are not assigned to this project!"}), 403

    data = request.get_json()
    assigned_to = data.get('assigned_to')
    if current_user['role'] == 'developer':
        assigned_to = current_user['username']

    subtask_item = {
        "id": str(uuid.uuid4())[:8],
        "name": data.get('subtaskName'),
        "assigned_to": assigned_to,
        "completed": False,
        "creator_role": current_user['role']  # Tracking who created it ('manager' or 'developer')
    }
    project['subtasks'].append(subtask_item)
    return jsonify(project), 200

@app.route('/api/projects/<project_id>/subtasks/<subtask_id>/reassign', methods=['PATCH'])
def reassign_subtask(project_id, subtask_id):
    if 'user' not in session or session['user']['role'] != 'manager':
        return jsonify({"error": "Only managers can reassign subtasks!"}), 403

    project = next((p for p in projects if p['id'] == project_id), None)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    subtask = next((s for s in project['subtasks'] if s['id'] == subtask_id), None)
    if not subtask:
        return jsonify({"error": "Subtask not found"}), 404

    # Prevent manager from reassigning subtasks created by developers
    if subtask.get('creator_role') == 'developer':
        return jsonify({"error": "Manager cannot change developer for subtasks created by developers!"}), 403

    data = request.get_json()
    subtask['assigned_to'] = data.get('assigned_to')
    return jsonify(project), 200

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