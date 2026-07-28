"""Generate career paths by analyzing module data against seed careers + diplomas.

Strategy:
- Keep the original 14 curated careers with their exact keywords (they're quality)
- Enhance each career with a FEW highly specific technical terms from module synopses
- Generate new careers from diploma data using TF-IDF keyword selection
- Output rp_career_paths.json with match statistics
"""
import json
import os
import re
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')

COMMON_WORDS = {
    'the','a','an','and','or','of','in','on','at','to','for','with','by','from',
    'as','is','are','was','were','be','been','has','have','had','do','does','did',
    'will','would','can','could','may','might','shall','should','this','that',
    'these','those','it','its','they','them','their','we','our','you','your',
    'he','she','him','her','his','not','no','nor','but','if','because','so',
    'than','very','just','about','also','into','through','during','before',
    'after','above','below','between','such','each','all','both','few',
    'more','most','other','some','only','own','same','too','which','what','who','whom','how','where','when','why','upon','within',
    'without','including','various','different','related','based','using',
    'provide','learn','develop','understand','apply','focus','throughout',
    'well','along','among','across','become','introduction','overview',
    'fundamental','principle','concept','technique','skill','knowledge',
    'ability','area','topic','field','project','practical','theoretical',
    'basic','core','key','main','broad','wide','range','variety','aspect',
    'element','component','part','role','function','process','method',
    'approach','strategy','tool','technology','system','course','module',
    'student','learner','participant','people','individual','team','group',
    'work','study','explore','examine','investigate','analyse','evaluate',
    'create','design','implement','build','construct','solve','address',
    'manage','plan','organise','communicate','present','discuss','demonstrate',
    'show','identify','describe','explain','able','enable','allow','help',
    'support','require','need','must','outcome','result','goal','objective',
    'purpose','context','setting','environment','situation','scenario','case',
    'example','cover','include','consist','involve',
    'feature','offer','deliver','gain','acquire','enhance','improve',
    'industrial','hand','unit','lesson','session','week','hour','minute',
    'online','face','assessment','assignment','activity','exercise','task',
    'problem','question','answer','feedback','data','analysis','information',
    'digital','technical','professional','personal','social',
    'cultural','global','local','national','international','community',
    'industry','business','organisation','service','product','customer',
    'client','user','consumer','market','economic','financial','legal',
    'ethical','sustainable','environmental','quality','safety','health',
    'security','risk','innovation','entrepreneurship','leadership',
    'management','administration','operation','performance','efficiency',
    'effective','appropriate','relevant','significant','important','essential',
    'necessary','potential','current','emerging','new','modern','contemporary',
    'traditional','existing','future','recent','multiple','numerous',
    'specific','particular','unique','distinct','separate',
    'common','typical','standard','normal','regular','general','overall',
    'comprehensive','integrated','interdisciplinary','multidisciplinary',
}

# The 14 original seed careers — kept exactly as curated
SEED_CAREERS = [
    {"id": "data-analyst", "label": "Data Analyst", "keywords": ["data","analytics","python","sql","visualization","power bi","statistics","excel","tableau"]},
    {"id": "data-scientist", "label": "Data Scientist", "keywords": ["machine learning","deep learning","python","statistics","ai","neural network","predictive","nlp"]},
    {"id": "cybersecurity", "label": "Cybersecurity", "keywords": ["security","cyber","network","ethical hacking","forensic","encryption","firewall","penetration"]},
    {"id": "software-engineer", "label": "Software Engineer", "keywords": ["programming","software","web","app","java","agile","javascript","python","testing","api"]},
    {"id": "ui-ux", "label": "UI/UX Designer", "keywords": ["design","ui","ux","figma","user experience","wireframe","prototype","accessibility","interaction"]},
    {"id": "ai-ml-engineer", "label": "AI/ML Engineer", "keywords": ["artificial intelligence","machine learning","deep learning","neural","nlp","computer vision","tensorflow","pytorch"]},
    {"id": "cloud-devops", "label": "Cloud / DevOps Engineer", "keywords": ["cloud","devops","docker","kubernetes","ci/cd","aws","azure","infrastructure","automation","deployment"]},
    {"id": "mobile-developer", "label": "Mobile App Developer", "keywords": ["mobile","android","ios","flutter","react native","swift","kotlin","app development"]},
    {"id": "game-developer", "label": "Game Developer", "keywords": ["game","unity","unreal","3d","animation","graphics","rendering","physics"]},
    {"id": "business-analyst", "label": "Business Analyst", "keywords": ["business","requirements","process","stakeholder","documentation","uml","agile","project management"]},
    {"id": "network-engineer", "label": "Network Engineer", "keywords": ["network","routing","switching","tcp/ip","cisco","infrastructure","protocol","lan","wan"]},
    {"id": "digital-marketer", "label": "Digital Marketing", "keywords": ["marketing","social media","seo","analytics","content","e-commerce","campaign","brand"]},
    {"id": "fintech-developer", "label": "Fintech Developer", "keywords": ["fintech","blockchain","payment","banking","cryptocurrency","smart contract","financial"]},
    {"id": "iot-engineer", "label": "IoT / Embedded Systems Engineer", "keywords": ["iot","embedded","sensor","microcontroller","arduino","raspberry pi","firmware","hardware"]},
]


def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def tokenize(text):
    tokens = re.findall(r'[a-z]{3,}', text.lower())
    return [t for t in tokens if t not in COMMON_WORDS]


def compute_global_freq(modules):
    counts = Counter()
    for m in modules:
        text = f" {m.get('module_name', '')} {m.get('synopsis', '')} ".lower()
        counts.update(tokenize(text))
    return counts


def score_modules(keywords, modules):
    results = []
    kw_set = {k.lower() for k in keywords}
    for m in modules:
        haystack = f" {m.get('module_name', '')} {m.get('synopsis', '')} ".lower()
        score = sum(1 for kw in kw_set if f" {kw} " in haystack)
        if score > 0:
            results.append((score, m))
    results.sort(key=lambda x: (-x[0], x[1].get('module_code', '')))
    return results


def enhance_keywords(seed_kws, modules, global_freq, specificity_min=4.0):
    """Add a FEW highly specific technical terms to seed keywords.
    
    Only adds words that are >= specificity_min times more common in
    strongly-matching modules than overall.
    """
    seed_set = {k.lower() for k in seed_kws}
    total = len(modules)

    matching_synopses = []
    for m in modules:
        haystack = f" {m.get('module_name', '')} {m.get('synopsis', '')} ".lower()
        score = sum(1 for kw in seed_set if f" {kw} " in haystack)
        if score >= 2:
            matching_synopses.append(haystack)

    if len(matching_synopses) < 3:
        matching_synopses = []
        for m in modules:
            haystack = f" {m.get('module_name', '')} {m.get('synopsis', '')} ".lower()
            if any(f" {kw} " in haystack for kw in seed_set):
                matching_synopses.append(haystack)

    if not matching_synopses:
        return list(seed_kws)

    career_count = Counter()
    for syn in matching_synopses:
        career_count.update(tokenize(syn))

    n_career = len(matching_synopses)
    result = list(seed_kws)
    seen = set(seed_kws)

    candidates = []
    for word, count in career_count.most_common(80):
        if word in seen:
            continue
        if len(word) <= 2:
            continue
        global_c = global_freq.get(word, 1)
        specificity = (count / n_career) / (global_c / total)
        if specificity >= specificity_min and count >= 2:
            candidates.append((specificity, word))

    candidates.sort(key=lambda x: -x[0])
    for _, word in candidates[:5]:
        result.append(word)
        seen.add(word)

    return result


def generate_diploma_careers(courses, modules, global_freq, specificity_min=3.0):
    """Generate careers from diploma data with distinctive keywords."""
    result = []
    module_index = {m['module_code']: m for m in modules}

    for course in (courses or []):
        all_codes = set()
        for bucket in ['major_modules', 'discipline_modules', 'elective_modules', 'general_modules', 'industry_modules']:
            for entry in course.get(bucket, []):
                if 'code' in entry:
                    all_codes.add(entry['code'])

        cmods = [module_index[c] for c in all_codes if c in module_index]
        if len(cmods) < 4:
            continue

        combined = ' '.join(
            f"{m.get('module_name', '')} {m.get('synopsis', '')}" for m in cmods
        )
        wc = Counter(tokenize(combined))
        n_cmods = len(cmods)
        total = len(modules)

        candidates = []
        for word, count in wc.most_common(50):
            if len(word) <= 2:
                continue
            global_c = global_freq.get(word, 1)
            specificity = (count / n_cmods) / (global_c / total)
            if specificity >= specificity_min and count >= 2:
                candidates.append((specificity, word))

        candidates.sort(key=lambda x: -x[0])
        top_kws = [w for _, w in candidates[:10]]
        if len(top_kws) < 4:
            continue

        label = course.get('course_name', '')
        label = re.sub(r'^Diploma in\s+', '', label).strip()
        if len(label) > 45:
            label = label[:42] + '...'

        career_id = f"diploma-{course['course_code'].lower()}"

        test = score_modules(top_kws, modules)
        if sum(1 for s, _ in test if s >= 2) < 4:
            continue

        result.append({'id': career_id, 'label': label, 'keywords': top_kws})

    return result


def generate_minor_careers(minors, modules, global_freq, specificity_min=2.5):
    """Generate careers from minor programmes with distinctive keywords."""
    result = []
    module_index = {m['module_code']: m for m in modules}

    for minor in (minors or []):
        codes = set()
        for entry in minor.get('modules', []):
            if isinstance(entry, dict) and 'code' in entry:
                codes.add(entry['code'])

        mmods = [module_index[c] for c in codes if c in module_index]
        if len(mmods) < 3:
            continue

        combined = ' '.join(
            f"{m.get('module_name', '')} {m.get('synopsis', '')}" for m in mmods
        )
        wc = Counter(tokenize(combined))
        n_mmods = len(mmods)
        total = len(modules)

        candidates = []
        for word, count in wc.most_common(50):
            if len(word) <= 2:
                continue
            global_c = global_freq.get(word, 1)
            specificity = (count / n_mmods) / (global_c / total)
            if specificity >= specificity_min and count >= 2:
                candidates.append((specificity, word))

        candidates.sort(key=lambda x: -x[0])
        top_kws = [w for _, w in candidates[:10]]
        if len(top_kws) < 3:
            continue

        label = minor.get('minor_name', '')
        label = re.sub(r'^Minor in\s+', '', label).strip()
        if len(label) > 45:
            label = label[:42] + '...'

        slug = re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')
        career_id = f"minor-{slug}"

        test = score_modules(top_kws, modules)
        if sum(1 for s, _ in test if s >= 2) < 3:
            continue

        result.append({'id': career_id, 'label': label, 'keywords': top_kws})

    return result


def main():
    modules = load_json('rp_modules_synopsis.json')
    courses = load_json('rp_courses.json')
    minors = load_json('rp_minors.json')

    if not modules:
        print('[SKIP] No module data.')
        return

    print(f'Modules: {len(modules)}, Courses: {len(courses or [])}, Minors: {len(minors or [])}')
    global_freq = compute_global_freq(modules)
    print(f'Vocabulary: {len(global_freq)} unique words')

    # Phase 1: Seed careers + targeted enhancement
    careers = []
    for seed in SEED_CAREERS:
        enhanced = enhance_keywords(seed['keywords'], modules, global_freq)
        scored = score_modules(enhanced, modules)
        ge2 = sum(1 for s, _ in scored if s >= 2)
        ge1 = len(scored)
        added = len(enhanced) - len(seed['keywords'])
        careers.append({
            'id': seed['id'], 'label': seed['label'],
            'keywords': enhanced,
            'module_count': ge2, 'total_matches': ge1,
        })
        print(f"  {seed['label']}: {len(seed['keywords'])} +{added} = {len(enhanced)} kws, {ge2} modules (>=2)")

    # Phase 2: Diploma-based careers
    diploma = generate_diploma_careers(courses, modules, global_freq)
    existing_ids = {c['id'] for c in careers}
    added_count = 0
    for dc in diploma:
        if dc['id'] in existing_ids:
            continue
        scored = score_modules(dc['keywords'], modules)
        ge2 = sum(1 for s, _ in scored if s >= 2)
        if ge2 < 4:
            continue
        careers.append({
            'id': dc['id'], 'label': dc['label'],
            'keywords': dc['keywords'],
            'module_count': ge2, 'total_matches': len(scored),
        })
        added_count += 1
        print(f"  [NEW] {dc['label']}: {len(dc['keywords'])} kws, {ge2} modules (>=2)")

    print(f'\nDiploma careers added: {added_count}')

    # Phase 3: Minor-based careers
    minor_careers = generate_minor_careers(minors, modules, global_freq)
    minor_added = 0
    existing_ids = {c['id'] for c in careers}
    for mc in minor_careers:
        if mc['id'] in existing_ids:
            continue
        scored = score_modules(mc['keywords'], modules)
        ge2 = sum(1 for s, _ in scored if s >= 2)
        if ge2 < 3:
            continue
        careers.append({
            'id': mc['id'], 'label': mc['label'],
            'keywords': mc['keywords'],
            'module_count': ge2, 'total_matches': len(scored),
        })
        minor_added += 1
        print(f"  [MINOR] {mc['label']}: {len(mc['keywords'])} kws, {ge2} modules (>=2)")

    print(f'Minor careers added: {minor_added}')

    out_path = os.path.join(DATA_DIR, 'rp_career_paths.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(careers, f, ensure_ascii=False, indent=2)

    # Coverage stats
    covered = set()
    for career in careers:
        kws = {k.lower() for k in career['keywords']}
        for m in modules:
            haystack = f" {m.get('module_name', '')} {m.get('synopsis', '')} ".lower()
            if sum(1 for kw in kws if f" {kw} " in haystack) >= 2:
                covered.add(m['module_code'])

    print(f'Written: {len(careers)} career paths')
    print(f'Coverage: {len(covered)}/{len(modules)} modules (>=2 keyword matches)')


if __name__ == '__main__':
    main()
