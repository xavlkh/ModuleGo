from flask import Flask, request, jsonify, render_template
import sqlite3
import os

app = Flask(__name__,
            static_folder='app/static',
            template_folder='app/templates')
_base_dir = os.path.dirname(os.path.abspath(__file__))
db_name = '/tmp/modulego.db' if os.environ.get('VERCEL') else os.path.join(_base_dir, 'modulego.db')

def init_db():
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS REVIEWS
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                  MODULE_CODE TEXT NOT NULL,
                  RATING INTEGER NOT NULL,
                  COMMENT TEXT,
                  TIMESTAMP DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def serve_index():
    return render_template('modules/index.html')

@app.route('/comparison')
def serve_comparison():
    return render_template('modules/comparison.html')

@app.route('/api/reviews', methods=['POST'])
def add_review():
    data = request.json
    module_code = data.get('module_code')
    rating = data.get('rating')
    comment = data.get('comment', '')

    if not module_code or not rating:
        return jsonify({"error": "Module code and rating are required"}), 400

    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("INSERT INTO REVIEWS (MODULE_CODE, RATING, COMMENT) VALUES (?, ?, ?)",
              (module_code, rating, comment))
    conn.commit()
    conn.close()

    return jsonify({"message": "Review added successfully!"}), 201

@app.route('/api/reviews/<module_code>', methods=['GET'])
def get_reviews(module_code):
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT RATING, COMMENT, TIMESTAMP FROM REVIEWS WHERE MODULE_CODE = ? ORDER BY TIMESTAMP DESC", (module_code,))
    rows = c.fetchall()
    conn.close()

    reviews = [dict(row) for row in rows]
    return jsonify(reviews), 200

if __name__ == '__main__':
    print("ModuleGo Backend Server running on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
