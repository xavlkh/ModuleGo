from flask import Flask, request, jsonify, render_template
from contextlib import contextmanager
from datetime import datetime, timezone
import sqlite3
import os
import re
from dotenv import load_dotenv
from supabase import create_client
from postgrest.exceptions import APIError

load_dotenv()

app = Flask(__name__,
            static_folder='app/static',
            template_folder='app/templates')

_base_dir = os.path.dirname(os.path.abspath(__file__))
MAX_COMMENT_LENGTH = 500

supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_KEY')
supabase = None

if supabase_url and supabase_key:
    if not supabase_url.startswith(('https://', 'http://')):
        raise RuntimeError('SUPABASE_URL must be a complete HTTP(S) URL.')
    if supabase_key.startswith('sb_publishable_'):
        raise RuntimeError(
            'SUPABASE_KEY must use the backend-only sb_secret_ key, not a '
            'publishable browser key.'
        )
    supabase = create_client(supabase_url, supabase_key)
db_name = os.environ.get('DATABASE_PATH', os.path.join(_base_dir, 'modulego.db'))


def get_db():
    """Open a local review database connection with dictionary-like rows."""
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def database_connection():
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
    """Create or upgrade the SQLite review table used locally and in tests."""
    with database_connection() as conn:
        conn.execute(
            '''CREATE TABLE IF NOT EXISTS REVIEWS
               (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                MODULE_CODE TEXT NOT NULL,
                RATING INTEGER NOT NULL,
                COMMENT TEXT NOT NULL DEFAULT '',
                TIMESTAMP DATETIME DEFAULT CURRENT_TIMESTAMP,
                UPDATED_AT DATETIME)'''
        )
        columns = {
            row['name']
            for row in conn.execute('PRAGMA table_info(REVIEWS)').fetchall()
        }
        if 'UPDATED_AT' not in columns:
            conn.execute('ALTER TABLE REVIEWS ADD COLUMN UPDATED_AT DATETIME')
        conn.execute(
            'CREATE INDEX IF NOT EXISTS IDX_REVIEWS_MODULE_CODE '
            'ON REVIEWS (MODULE_CODE)'
        )


def validate_review_payload(data, require_module_code=False):
    if not isinstance(data, dict):
        return None, 'A JSON request body is required.'

    rating = data.get('rating')
    if isinstance(rating, bool) or not isinstance(rating, int):
        return None, 'Rating must be an integer from 1 to 5.'
    if rating < 1 or rating > 5:
        return None, 'Rating must be between 1 and 5.'

    comment = data.get('comment', '')
    if comment is None:
        comment = ''
    if not isinstance(comment, str):
        return None, 'Comment must be text.'
    comment = comment.strip()
    if len(comment) > MAX_COMMENT_LENGTH:
        return None, f'Comment must be {MAX_COMMENT_LENGTH} characters or fewer.'

    payload = {'rating': rating, 'comment': comment}
    if require_module_code:
        module_code = data.get('module_code')
        if not isinstance(module_code, str) or not module_code.strip():
            return None, 'Module code is required.'
        module_code = module_code.strip().upper()
        if len(module_code) > 20:
            return None, 'Module code is too long.'
        payload['module_code'] = module_code

    return payload, None


def review_to_dict(row):
    return {
        'id': row['ID'],
        'module_code': row['MODULE_CODE'],
        'rating': row['RATING'],
        'comment': row['COMMENT'],
        'timestamp': row['TIMESTAMP'],
        'updated_at': row['UPDATED_AT'],
    }


def select_review(conn, review_id):
    return conn.execute(
        '''SELECT ID, MODULE_CODE, RATING, COMMENT, TIMESTAMP, UPDATED_AT
           FROM REVIEWS WHERE ID = ?''',
        (review_id,),
    ).fetchone()


def use_sqlite_reviews():
    """Keep SQLite isolated to automated tests."""
    return bool(app.config.get('TESTING'))


def supabase_unavailable():
    return jsonify({
        'error': (
            'Supabase is not configured. Set SUPABASE_URL and the '
            'backend-only SUPABASE_KEY.'
        )
    }), 503

THEME_RULES = [
    (r'3d print|additive manufactur|prototype|printed object', '3D design, printing, prototyping, and post-processing', 'hands-on making, product design, prototyping, and creative technology'),
    (r'(food|nutrition|diet|wellness|eating)|health benefit', 'food, nutrition, wellness, and healthy lifestyle choices', 'food, nutrition, wellness, and making healthier lifestyle decisions'),
    (r'sustainab|green|environment|planet|climate|ecology|ecological', 'sustainability, environmental practices, and social responsibility', 'sustainability, environmental issues, and community impact'),
    (r'biodiversity|wildlife|plants|geography|ecology|ecosystem', 'biodiversity, local wildlife, plant life, geography, and ecological patterns', 'nature, biodiversity, environmental awareness, and local ecosystems'),
    (r'anatomy|physiology|human body|skeletal|muscular|nervous|respiratory', 'human body systems, anatomy, physiology, and biological functions', 'health sciences, human biology, sports science, and healthcare pathways'),
    (r'patient care|healthcare|health professional|hospital|clinical|medical record|patient', 'patient care, healthcare settings, communication, and professional practice', 'healthcare, patient support, clinical environments, and people-centred service'),
    (r'(biology|biological|bio-innovation|biodiversity|cell|cells|genetic|genetics|evolution|biomolecule|microbiology)', 'biological concepts, cells, genetics, and scientific investigation', 'biology, life sciences, research, and scientific problem-solving'),
    (r'chemistry|chemical|organic|inorganic|molecule|titration|stoichiometry', 'chemical principles, laboratory techniques, reactions, and data interpretation', 'chemistry, applied science, laboratory work, and analytical thinking'),
    (r'physics|kinematic|thermodynamic|optics|electromagnet|mechanics|force|energy', 'physics principles, calculations, real-life applications, and practical activities', 'physics, engineering, applied science, and quantitative problem-solving'),
    (r'facilit(?:y|ies) management|building facilit|fire protection|hazard mitigation|housekeeping', 'facilities management, building systems, safety, risk control, and operations', 'built environments, facilities operations, workplace safety, and service management'),
    (r'laboratory|lab |glp|documentation|iso|quality management', 'laboratory practices, safety, documentation, quality standards, and compliance', 'laboratory work, applied science operations, quality control, and safe practice'),
    (r'programming|software|coding|app development|web development|web|database|python|java|javascript', 'programming, software development, applications, and technical problem-solving', 'coding, software development, digital products, and computational thinking'),
    (r'data analytics|analytics|statistics|visualization|dashboard|database|machine learning|artificial intelligence|\bai\b', 'data analysis, digital tools, evidence-based insights, and decision support', 'data, analytics, technology, research, and evidence-based decision-making'),
    (r'data communication|network technology|networking|computer network', 'networking technologies, data communication concepts, and industry-relevant IT infrastructure', 'networking, IT infrastructure, communications technology, and technical systems'),
    (r'cyber|security|forensic|threat|vulnerab|encryption', 'cybersecurity, networks, digital risks, and protection strategies', 'cybersecurity, IT infrastructure, digital defence, and technical investigation'),
    (r'business|marketing|entrepreneur|customer|consumer|retail|brand|sales', 'business concepts, market awareness, customer needs, and practical decision-making', 'business, entrepreneurship, marketing, customer experience, and commercial strategy'),
    (r'finance|accounting|financial|investment|bank|budget|cost', 'financial concepts, accounting practices, analysis, and business decision-making', 'finance, accounting, business planning, and analytical decision-making'),
    (r'live sound|sound event|audio|broadcast|recording|front of house|foh', 'audio production, live sound techniques, recording, and broadcast applications', 'audio production, live events, sound engineering, and technical media work'),
    (r'hospitality|hotel|tourism|travel|event|leisure|guest', 'hospitality, tourism, service operations, guest experience, and event contexts', 'hospitality, tourism, events, service design, and people-focused work'),
    (r'media|design|animation|game|creative|visual|story|content|film|audio', 'creative production, design thinking, media tools, and visual communication', 'design, media, storytelling, creative production, and visual expression'),
    (r'engineering|electronic|robot|iot|sensor|manufactur|automation|mechanical', 'engineering concepts, technical systems, applied design, and practical problem-solving', 'engineering, technology, systems thinking, and hands-on technical work'),
    (r'challenge course|adventure programming|outdoor|participant profile', 'challenge course operations, adventure learning, participant needs, and safety-aware management', 'outdoor learning, adventure education, facilitation, and activity management'),
    (r'sport|exercise|fitness|health promotion|rehabilitation|coaching', 'sports science, health, fitness, movement, and performance-related concepts', 'sports, health promotion, exercise science, coaching, and active lifestyles'),
    (r'communication|writing|presentation|language|interpersonal|negotiation', 'communication skills, writing, presentation, and interpersonal effectiveness', 'communication, writing, teamwork, presentations, and people-facing roles'),
    (r'psychology|social|counselling|community|behaviour|human service', 'human behaviour, social issues, community contexts, and people-centred practice', 'psychology, social service, community work, and understanding people'),
    (r'logistics|supply chain|transport|procurement|operation', 'operations, logistics, supply chain processes, and resource coordination', 'logistics, operations, supply chain management, and process improvement'),
    (r'math|calculus|algebra|statistic|quantitative|probability', 'mathematical concepts, quantitative reasoning, and problem-solving techniques', 'mathematics, analytics, engineering, science, and structured problem-solving'),
]

PRACTICE_RULES = [
    (r'hands-on|practical|practice session|workshop|build|create|design', 'hands-on activities'),
    (r'laboratory|lab |experiment|testing', 'laboratory practice'),
    (r'project|prototype|develop|produce', 'project-based work'),
    (r'case stud|real[- ]life|industry|workplace|scenario', 'real-world applications'),
    (r'problem|solve|calculat|interpret|analyse|analyze', 'problem-solving tasks'),
]


def clean_text(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def join_human(items):
    items = list(dict.fromkeys(items))
    if len(items) == 0:
        return ''
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f'{items[0]} and {items[1]}'
    return f'{", ".join(items[:-1])}, and {items[-1]}'


def title_topic(name):
    t = re.sub(r'\b(introduction to|introductory|fundamentals of|principles of)\b', '', name, flags=re.IGNORECASE)
    t = re.sub(r'[^\w\s&-]', '', t)
    t = re.sub(r'\s+', ' ', t).strip().lower()
    return t or 'this topic'


def match_theme(module):
    name = clean_text(module.get('name', ''))
    body = f"{clean_text(module.get('description', ''))} {clean_text(module.get('school', ''))} {clean_text(module.get('category', ''))}"
    for pattern, feature, audience in THEME_RULES:
        if re.search(pattern, name, re.IGNORECASE):
            return feature, audience
    for pattern, feature, audience in THEME_RULES:
        if re.search(pattern, body, re.IGNORECASE):
            return feature, audience
    return None, None


def match_practices(text):
    return [phrase for pattern, phrase in PRACTICE_RULES if re.search(pattern, text, re.IGNORECASE)][:2]


def generate_comparison_fields(module):
    name = clean_text(module.get('name', ''))
    desc = clean_text(module.get('description', ''))
    school = clean_text(module.get('school', ''))
    category = clean_text(module.get('category', ''))
    text = f"{name}. {desc} {school} {category}"

    feature, audience = match_theme(module)
    practices = match_practices(text)
    topic = title_topic(name)

    if feature:
        features = f'Covers {feature}'
    else:
        features = f'Introduces key concepts and practical understanding in {topic}'

    if practices:
        features += f' through {join_human(practices)}'
    features += '.'

    if audience:
        suitable_for = f'Students interested in {audience}.'
    else:
        suitable_for = f'Students who want an introductory understanding of {topic}.'

    return features, suitable_for


@app.route('/api/modules', methods=['GET'])
def get_modules():
    if supabase is None:
        return jsonify({'error': 'Supabase is not configured.'}), 503
    result = supabase.table("rp_modules").select("*").execute()

    school_map = {
        "Science": "School of Applied Science",
        "Business": "School of Business",
        "Engineering": "School of Engineering",
        "Hospitality": "School of Hospitality",
        "Infocomm": "School of Infocomm",
        "Sports and Health": "School of Sports and Health",
        "Arts, Media and Design": "School of Technology for Arts, Media and Design",
        "Mass Communication": "School of Business",
        "General Life Skills": "School of Applied Science",
    }

    modules = []
    for row in result.data:
        raw_school = row.get("school", "")
        module = {
            "code": row.get("module_code", ""),
            "name": row.get("module_name", ""),
            "description": row.get("module_description", ""),
            "school": school_map.get(raw_school, raw_school),
            "url": row.get("link", ""),
        }
        features, suitable_for = generate_comparison_fields(module)
        module["features"] = features
        module["suitableFor"] = suitable_for
        modules.append(module)
    return jsonify(modules), 200


@app.route('/')
def serve_index():
    return render_template('modules/index.html')

@app.route('/comparison')
def serve_comparison():
    return render_template('modules/comparison.html')


@app.route('/reviews')
def serve_reviews():
    return render_template('modules/reviews.html')


@app.route('/api/reviews', methods=['GET'])
def list_reviews():
    if use_sqlite_reviews():
        with database_connection() as conn:
            rows = conn.execute(
                '''SELECT ID, MODULE_CODE, RATING, COMMENT, TIMESTAMP, UPDATED_AT
                   FROM REVIEWS ORDER BY TIMESTAMP DESC, ID DESC'''
            ).fetchall()
        return jsonify([review_to_dict(row) for row in rows]), 200

    if supabase is None:
        return supabase_unavailable()
    result = (
        supabase.table('reviews')
        .select('id,module_code,rating,comment,timestamp,updated_at')
        .order('timestamp', desc=True)
        .execute()
    )
    return jsonify(result.data), 200


@app.route('/api/reviews', methods=['POST'])
def add_review():
    payload, error = validate_review_payload(
        request.get_json(silent=True),
        require_module_code=True,
    )
    if error:
        return jsonify({'error': error}), 400

    if use_sqlite_reviews():
        with database_connection() as conn:
            cursor = conn.execute(
                '''INSERT INTO REVIEWS (MODULE_CODE, RATING, COMMENT)
                   VALUES (?, ?, ?)''',
                (payload['module_code'], payload['rating'], payload['comment']),
            )
            row = select_review(conn, cursor.lastrowid)
        return jsonify(review_to_dict(row)), 201

    if supabase is None:
        return supabase_unavailable()
    try:
        result = supabase.table('reviews').insert(payload).execute()
    except APIError as error:
        if error.code == '23503':
            return jsonify({'error': 'Module code does not exist.'}), 400
        raise
    return jsonify(result.data[0]), 201


@app.route('/api/reviews/<module_code>', methods=['GET'])
def get_reviews(module_code):
    normalized_code = module_code.strip().upper()
    if use_sqlite_reviews():
        with database_connection() as conn:
            rows = conn.execute(
                '''SELECT ID, MODULE_CODE, RATING, COMMENT, TIMESTAMP, UPDATED_AT
                   FROM REVIEWS WHERE MODULE_CODE = ?
                   ORDER BY TIMESTAMP DESC, ID DESC''',
                (normalized_code,),
            ).fetchall()
        return jsonify([review_to_dict(row) for row in rows]), 200

    if supabase is None:
        return supabase_unavailable()
    result = (
        supabase.table('reviews')
        .select('id,module_code,rating,comment,timestamp,updated_at')
        .eq('module_code', normalized_code)
        .order('timestamp', desc=True)
        .execute()
    )
    return jsonify(result.data), 200


@app.route('/api/reviews/<int:review_id>', methods=['PUT'])
def update_review(review_id):
    payload, error = validate_review_payload(request.get_json(silent=True))
    if error:
        return jsonify({'error': error}), 400

    if use_sqlite_reviews():
        with database_connection() as conn:
            cursor = conn.execute(
                '''UPDATE REVIEWS
                   SET RATING = ?, COMMENT = ?, UPDATED_AT = CURRENT_TIMESTAMP
                   WHERE ID = ?''',
                (payload['rating'], payload['comment'], review_id),
            )
            if cursor.rowcount == 0:
                return jsonify({'error': 'Review not found.'}), 404
            row = select_review(conn, review_id)
        return jsonify(review_to_dict(row)), 200

    if supabase is None:
        return supabase_unavailable()
    payload['updated_at'] = datetime.now(timezone.utc).isoformat()
    result = (
        supabase.table('reviews')
        .update(payload)
        .eq('id', review_id)
        .execute()
    )
    if not result.data:
        return jsonify({'error': 'Review not found.'}), 404
    return jsonify(result.data[0]), 200


@app.route('/api/reviews/<int:review_id>', methods=['DELETE'])
def delete_review(review_id):
    if use_sqlite_reviews():
        with database_connection() as conn:
            cursor = conn.execute('DELETE FROM REVIEWS WHERE ID = ?', (review_id,))
            if cursor.rowcount == 0:
                return jsonify({'error': 'Review not found.'}), 404
        return '', 204

    if supabase is None:
        return supabase_unavailable()
    existing = (
        supabase.table('reviews')
        .select('id')
        .eq('id', review_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        return jsonify({'error': 'Review not found.'}), 404
    supabase.table('reviews').delete().eq('id', review_id).execute()
    return '', 204


@app.route('/api/ratings', methods=['GET'])
def get_rating_summaries():
    if use_sqlite_reviews():
        with database_connection() as conn:
            rows = conn.execute(
                '''SELECT MODULE_CODE,
                          ROUND(AVG(RATING), 2) AS AVERAGE_RATING,
                          COUNT(*) AS REVIEW_COUNT
                   FROM REVIEWS GROUP BY MODULE_CODE ORDER BY MODULE_CODE'''
            ).fetchall()
        summaries = {
            row['MODULE_CODE']: {
                'average_rating': row['AVERAGE_RATING'],
                'review_count': row['REVIEW_COUNT'],
            }
            for row in rows
        }
        return jsonify(summaries), 200

    if supabase is None:
        return supabase_unavailable()
    result = supabase.table('reviews').select('module_code,rating').execute()
    grouped = {}
    for review in result.data:
        code = review['module_code']
        grouped.setdefault(code, []).append(review['rating'])
    summaries = {
        code: {
            'average_rating': round(sum(ratings) / len(ratings), 2),
            'review_count': len(ratings),
        }
        for code, ratings in grouped.items()
    }
    return jsonify(summaries), 200


if __name__ == '__main__':
    print("ModuleGo Backend Server running on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
