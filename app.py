from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os

# Initialize Flask to serve the current directory as static files
app = Flask(__name__, static_folder='.', static_url_path='')
db_name = 'modulego.db'

# 1. Database Initialization (Just like Lab 6.5.10)
def init_db():
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    # Create a table for comments and ratings (CRUD - Create & Read)
    c.execute('''CREATE TABLE IF NOT EXISTS REVIEWS
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                  MODULE_CODE TEXT NOT NULL,
                  RATING INTEGER NOT NULL,
                  COMMENT TEXT,
                  TIMESTAMP DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# 2. Serve the Frontend (html)
@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

# 3. API Endpoint: CREATE a new review (POST)
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

# 4. API Endpoint: READ reviews for a specific module (GET)
@app.route('/api/reviews/<module_code>', methods=['GET'])
def get_reviews(module_code):
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row # Returns rows as dictionaries
    c = conn.cursor()
    c.execute("SELECT RATING, COMMENT, TIMESTAMP FROM REVIEWS WHERE MODULE_CODE = ? ORDER BY TIMESTAMP DESC", (module_code,))
    rows = c.fetchall()
    conn.close()

    reviews = [dict(row) for row in rows]
    return jsonify(reviews), 200

if __name__ == '__main__':
    # Initialize the database when the server starts
    init_db()
    print("ModuleGo Backend Server running on http://127.0.0.1:5000")
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)