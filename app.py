from flask import Flask, request, jsonify, render_template
import sqlite3
import os
import re
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

app = Flask(__name__,
            static_folder='app/static',
            template_folder='app/templates')

_base_dir = os.path.dirname(os.path.abspath(__file__))
IS_VERCEL = bool(os.environ.get('VERCEL'))

supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_KEY')
supabase = create_client(supabase_url, supabase_key)

if not IS_VERCEL:
    db_name = os.path.join(_base_dir, 'modulego.db')
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

@app.route('/api/reviews', methods=['POST'])
def add_review():
    data = request.json
    module_code = data.get('module_code')
    rating = data.get('rating')
    comment = data.get('comment', '')

    if not module_code or not rating:
        return jsonify({"error": "Module code and rating are required"}), 400

    if IS_VERCEL:
        supabase.table("reviews").insert({
            "module_code": module_code,
            "rating": rating,
            "comment": comment
        }).execute()
    else:
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        c.execute("INSERT INTO REVIEWS (MODULE_CODE, RATING, COMMENT) VALUES (?, ?, ?)",
                  (module_code, rating, comment))
        conn.commit()
        conn.close()

    return jsonify({"message": "Review added successfully!"}), 201


@app.route('/api/reviews/<module_code>', methods=['GET'])
def get_reviews(module_code):
    if IS_VERCEL:
        result = supabase.table("reviews") \
            .select("rating, comment, timestamp") \
            .eq("module_code", module_code) \
            .order("timestamp", desc=True) \
            .execute()
        reviews = result.data
    else:
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
