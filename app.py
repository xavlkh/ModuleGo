from flask import Flask, request, jsonify, render_template
from contextlib import contextmanager
import os
import sqlite3


app = Flask(
    __name__,
    static_folder="app/static",
    template_folder="app/templates",
)

_base_dir = os.path.dirname(os.path.abspath(__file__))
db_name = os.environ.get(
    "DATABASE_PATH",
    "/tmp/modulego.db"
    if os.environ.get("VERCEL")
    else os.path.join(_base_dir, "modulego.db"),
)
MAX_COMMENT_LENGTH = 500


def get_db():
    """Open a database connection that returns rows as dictionaries."""
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def database_connection():
    """Commit successful work and always close the SQLite connection."""
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create and safely upgrade the local reviews table."""
    with database_connection() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS REVIEWS
               (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                MODULE_CODE TEXT NOT NULL,
                RATING INTEGER NOT NULL,
                COMMENT TEXT NOT NULL DEFAULT '',
                TIMESTAMP DATETIME DEFAULT CURRENT_TIMESTAMP,
                UPDATED_AT DATETIME)"""
        )

        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(REVIEWS)").fetchall()
        }
        if "UPDATED_AT" not in columns:
            conn.execute("ALTER TABLE REVIEWS ADD COLUMN UPDATED_AT DATETIME")

        conn.execute(
            "CREATE INDEX IF NOT EXISTS IDX_REVIEWS_MODULE_CODE "
            "ON REVIEWS (MODULE_CODE)"
        )


def validate_review_payload(data, require_module_code=False):
    """Validate and normalize JSON sent when creating or updating a review."""
    if not isinstance(data, dict):
        return None, "A JSON request body is required."

    rating = data.get("rating")
    if isinstance(rating, bool) or not isinstance(rating, int):
        return None, "Rating must be an integer from 1 to 5."
    if rating < 1 or rating > 5:
        return None, "Rating must be between 1 and 5."

    comment = data.get("comment", "")
    if comment is None:
        comment = ""
    if not isinstance(comment, str):
        return None, "Comment must be text."
    comment = comment.strip()
    if len(comment) > MAX_COMMENT_LENGTH:
        return None, f"Comment must be {MAX_COMMENT_LENGTH} characters or fewer."

    payload = {"rating": rating, "comment": comment}

    if require_module_code:
        module_code = data.get("module_code")
        if not isinstance(module_code, str) or not module_code.strip():
            return None, "Module code is required."
        module_code = module_code.strip().upper()
        if len(module_code) > 20:
            return None, "Module code is too long."
        payload["module_code"] = module_code

    return payload, None


def review_to_dict(row):
    """Convert a database row into the public review API shape."""
    return {
        "id": row["ID"],
        "module_code": row["MODULE_CODE"],
        "rating": row["RATING"],
        "comment": row["COMMENT"],
        "timestamp": row["TIMESTAMP"],
        "updated_at": row["UPDATED_AT"],
    }


def select_review(conn, review_id):
    return conn.execute(
        """SELECT ID, MODULE_CODE, RATING, COMMENT, TIMESTAMP, UPDATED_AT
           FROM REVIEWS
           WHERE ID = ?""",
        (review_id,),
    ).fetchone()


init_db()


@app.route("/")
def serve_index():
    return render_template("modules/index.html")


@app.route("/comparison")
def serve_comparison():
    return render_template("modules/comparison.html")


@app.route("/reviews")
def serve_reviews():
    return render_template("modules/reviews.html")


@app.route("/api/reviews", methods=["GET"])
def list_reviews():
    """Return every review for the review dashboard."""
    with database_connection() as conn:
        rows = conn.execute(
            """SELECT ID, MODULE_CODE, RATING, COMMENT, TIMESTAMP, UPDATED_AT
               FROM REVIEWS
               ORDER BY TIMESTAMP DESC, ID DESC"""
        ).fetchall()

    return jsonify([review_to_dict(row) for row in rows]), 200


@app.route("/api/reviews", methods=["POST"])
def add_review():
    payload, error = validate_review_payload(
        request.get_json(silent=True),
        require_module_code=True,
    )
    if error:
        return jsonify({"error": error}), 400

    with database_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO REVIEWS (MODULE_CODE, RATING, COMMENT)
               VALUES (?, ?, ?)""",
            (payload["module_code"], payload["rating"], payload["comment"]),
        )
        row = select_review(conn, cursor.lastrowid)

    return jsonify(review_to_dict(row)), 201


@app.route("/api/reviews/<module_code>", methods=["GET"])
def get_reviews(module_code):
    with database_connection() as conn:
        rows = conn.execute(
            """SELECT ID, MODULE_CODE, RATING, COMMENT, TIMESTAMP, UPDATED_AT
               FROM REVIEWS
               WHERE MODULE_CODE = ?
               ORDER BY TIMESTAMP DESC, ID DESC""",
            (module_code.strip().upper(),),
        ).fetchall()

    return jsonify([review_to_dict(row) for row in rows]), 200


@app.route("/api/reviews/<int:review_id>", methods=["PUT"])
def update_review(review_id):
    payload, error = validate_review_payload(request.get_json(silent=True))
    if error:
        return jsonify({"error": error}), 400

    with database_connection() as conn:
        cursor = conn.execute(
            """UPDATE REVIEWS
               SET RATING = ?, COMMENT = ?, UPDATED_AT = CURRENT_TIMESTAMP
               WHERE ID = ?""",
            (payload["rating"], payload["comment"], review_id),
        )
        if cursor.rowcount == 0:
            return jsonify({"error": "Review not found."}), 404
        row = select_review(conn, review_id)

    return jsonify(review_to_dict(row)), 200


@app.route("/api/reviews/<int:review_id>", methods=["DELETE"])
def delete_review(review_id):
    with database_connection() as conn:
        cursor = conn.execute("DELETE FROM REVIEWS WHERE ID = ?", (review_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Review not found."}), 404

    return "", 204


@app.route("/api/ratings", methods=["GET"])
def get_rating_summaries():
    """Return one aggregate rating record per reviewed module."""
    with database_connection() as conn:
        rows = conn.execute(
            """SELECT MODULE_CODE,
                      ROUND(AVG(RATING), 2) AS AVERAGE_RATING,
                      COUNT(*) AS REVIEW_COUNT
               FROM REVIEWS
               GROUP BY MODULE_CODE
               ORDER BY MODULE_CODE"""
        ).fetchall()

    summaries = {
        row["MODULE_CODE"]: {
            "average_rating": row["AVERAGE_RATING"],
            "review_count": row["REVIEW_COUNT"],
        }
        for row in rows
    }
    return jsonify(summaries), 200


if __name__ == "__main__":
    print("ModuleGo Backend Server running on http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
