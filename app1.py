import sqlite3
from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)
DB_NAME = "tasks.db"


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                priority TEXT DEFAULT 'Medium',
                completed INTEGER DEFAULT 0
            )
        ''')
        conn.commit()


init_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Task & Workflow Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background: #0f172a; color: #f8fafc; display: flex; justify-content: center; padding: 40px 20px; }
        .container { width: 100%; max-width: 600px; background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        h1 { font-size: 24px; margin-bottom: 20px; color: #38bdf8; text-align: center; }
        .input-group { display: flex; gap: 10px; margin-bottom: 25px; }
        input[type="text"] { flex: 1; padding: 12px; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; outline: none; }
        select { padding: 12px; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; }
        button.add-btn { background: #38bdf8; color: #0f172a; border: none; padding: 12px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; }
        button.add-btn:hover { background: #0ea5e9; }
        ul { list-style: none; }
        li { background: #0f172a; padding: 14px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid #38bdf8; }
        li.completed { opacity: 0.5; text-decoration: line-through; border-left-color: #22c55e; }
        .badge { font-size: 11px; padding: 3px 8px; border-radius: 12px; background: #334155; margin-left: 8px; }
        .delete-btn { background: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; }
        .task-info { display: flex; align-items: center; cursor: pointer; }
        .error-msg { color: #f87171; font-size: 13px; margin-bottom: 15px; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Task & Workflow Tracker</h1>
        <div class="error-msg" id="errorMsg"></div>
        <div class="input-group">
            <input type="text" id="taskInput" placeholder="Add a new technical task...">
            <select id="priorityInput">
                <option value="Low">Low</option>
                <option value="Medium" selected>Medium</option>
                <option value="High">High</option>
            </select>
            <button class="add-btn" onclick="addTask()">Add</button>
        </div>
        <ul id="taskList"></ul>
    </div>

    <script>
        function showError(msg) {
            const box = document.getElementById('errorMsg');
            box.textContent = msg;
            box.style.display = 'block';
            setTimeout(() => { box.style.display = 'none'; }, 3000);
        }

        async function fetchTasks() {
            const res = await fetch('/api/tasks');
            if (!res.ok) { showError('Görevler yüklenemedi.'); return; }
            const tasks = await res.json();
            const list = document.getElementById('taskList');
            list.innerHTML = '';
            tasks.forEach(t => {
                const li = document.createElement('li');
                if (t.completed) li.classList.add('completed');

                const info = document.createElement('div');
                info.className = 'task-info';
                info.onclick = () => toggleTask(t.id, t.completed);

                const span = document.createElement('span');
                span.textContent = t.title; // XSS'e karşı güvenli: textContent kullanılıyor

                const badge = document.createElement('span');
                badge.className = 'badge';
                badge.textContent = t.priority;

                info.appendChild(span);
                info.appendChild(badge);

                const delBtn = document.createElement('button');
                delBtn.className = 'delete-btn';
                delBtn.textContent = 'Delete';
                delBtn.onclick = () => deleteTask(t.id);

                li.appendChild(info);
                li.appendChild(delBtn);
                list.appendChild(li);
            });
        }

        async function addTask() {
            const titleField = document.getElementById('taskInput');
            const title = titleField.value.trim();
            const priority = document.getElementById('priorityInput').value;
            if (!title) { showError('Görev başlığı boş olamaz.'); return; }

            const res = await fetch('/api/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, priority })
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                showError(err.error || 'Görev eklenemedi.');
                return;
            }
            titleField.value = '';
            fetchTasks();
        }

        async function toggleTask(id, currentStatus) {
            const res = await fetch(`/api/tasks/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ completed: currentStatus ? 0 : 1 })
            });
            if (!res.ok) { showError('Görev güncellenemedi.'); return; }
            fetchTasks();
        }

        async function deleteTask(id) {
            const res = await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
            if (!res.ok) { showError('Görev silinemedi.'); return; }
            fetchTasks();
        }

        fetchTasks();
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tasks ORDER BY id DESC')
        rows = cursor.fetchall()
        return jsonify([dict(row) for row in rows])


@app.route('/api/tasks', methods=['POST'])
def add_task():
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({"error": "title alanı zorunludur"}), 400

    priority = data.get('priority', 'Medium')
    if priority not in ('Low', 'Medium', 'High'):
        priority = 'Medium'

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO tasks (title, priority) VALUES (?, ?)',
                       (title, priority))
        conn.commit()
        return jsonify({"status": "success", "id": cursor.lastrowid}), 201


@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.get_json(silent=True) or {}
    if 'completed' not in data:
        return jsonify({"error": "completed alanı zorunludur"}), 400

    completed = 1 if data.get('completed') else 0

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE tasks SET completed = ? WHERE id = ?', (completed, task_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Görev bulunamadı"}), 404
        return jsonify({"status": "updated"})


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Görev bulunamadı"}), 404
        return jsonify({"status": "deleted"})


if __name__ == '__main__':
    # Not: debug=True sadece geliştirme ortamında kullanılmalı.
    # Production'da debug=False yapıp WSGI sunucusu (gunicorn vb.) ile çalıştırın.
    app.run(debug=True, port=5000)