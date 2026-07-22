"""Generate summary + suitable_for CSV for Supabase import.

Reads rp_modules_synopsis.json and generates:
- summary: features text (e.g. "Covers healthcare through hands-on activities")
- suitable_for: interest-based text (e.g. "Students interested in healthcare and biomedical sciences.")

Output: rp_modules_suitable_for.csv with columns: module_code, summary, suitable_for
"""

import csv
import json
import os
import re


THEME_RULES = [
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

INTEREST_KEYWORDS = [
    (r"\b(programming|software develop|web develop|app develop|coding|database)\b", "programming and software development"),
    (r"\b(data analy|statistic|machine learn|artificial intellig|algorithm)\b", "data analysis and analytics"),
    (r"\b(design|creative|visual|aesthetic|ux|ui|graphic|typograph)\w*\b", "design and creative thinking"),
    (r"\b(engineer|mechanical|electrical|robot|automat|manufactur|circuit)\w*\b", "engineering and technical problem-solving"),
    (r"\b(manag|market|financ|account|entrepreneur|strateg|leadership|business)\w*\b", "business and management"),
    (r"\b(health|nurs|medic|clinic|biomed|pharma|wellness|anatomy|diagnostic)\w*\b", "healthcare and biomedical sciences"),
    (r"\b(biolog|chem|physic|laborat|experiment|scientific)\w*\b", "scientific inquiry and research"),
    (r"\b(communicat|writing|journal|present|media|content creat|speech)\w*\b", "communication and media"),
    (r"\b(psycholog|counsell|communit|behaviou|social work|human service)\w*\b", "psychology and social sciences"),
    (r"\b(math|calculus|algebra|statistic|quantit|probabilit)\w*\b", "mathematics and quantitative reasoning"),
    (r"\b(cyber|secur|network|infrastructure|cloud|devops)\w*\b", "cybersecurity and infrastructure"),
    (r"\b(environment|sustain|ecolog|climate|marine|biodiversit)\w*\b", "environmental and sustainability studies"),
    (r"\b(event|hospit|tourism|hotel|food service|entertain|leisure)\w*\b", "hospitality and events management"),
    (r"\b(logist|supply chain|transport|procure|warehous|inventory)\w*\b", "logistics and supply chain operations"),
    (r"\b(film|video|animat|motion|sound|audio|music|theatre|perform)\w*\b", "film, audio, and performing arts"),
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


def match_theme(name, synopsis, school):
    body = f"{synopsis} {school}"
    for pattern, feature, audience in THEME_RULES:
        if re.search(pattern, name, re.IGNORECASE):
            return feature, audience
    for pattern, feature, audience in THEME_RULES:
        if re.search(pattern, body, re.IGNORECASE):
            return feature, audience
    return None, None


def match_practices(text):
    return [phrase for pattern, phrase in PRACTICE_RULES if re.search(pattern, text, re.IGNORECASE)][:2]


def extract_interests(text):
    text_lower = text.lower()
    found = []
    for pattern, label in INTEREST_KEYWORDS:
        if re.search(pattern, text_lower):
            found.append(label)
    return found[:3]


def format_suitable_for(interests):
    if not interests:
        return "Students seeking a general foundation module."
    if len(interests) == 1:
        return f"Students interested in {interests[0]}."
    if len(interests) == 2:
        return f"Students interested in {interests[0]} and {interests[1]}."
    return f"Students interested in {interests[0]}, {interests[1]}, and {interests[2]}."


def generate_summary(module):
    name = clean_text(module.get('module_name', ''))
    desc = clean_text(module.get('synopsis', ''))
    school = clean_text(module.get('school_name', ''))
    text = f"{name}. {desc} {school}"

    feature, _ = match_theme(name, desc, school)
    practices = match_practices(text)
    topic = title_topic(name)

    summary = f'Covers {feature}' if feature else f'Introduces key concepts and practical understanding in {topic}'
    if practices:
        summary += f' through {join_human(practices)}'
    summary += '.'
    return summary


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")
    input_path = os.path.join(data_dir, "rp_modules_synopsis.json")
    output_csv = os.path.join(data_dir, "rp_modules_comparison.csv")
    output_json = os.path.join(data_dir, "rp_modules_comparison.json")

    with open(input_path, "r", encoding="utf-8") as f:
        modules = json.load(f)

    seen_sf = {}
    rows = []
    for m in modules:
        code = m.get("module_code", "")
        summary = generate_summary(m)
        text = f"{m.get('module_name', '')} {m.get('synopsis', '')}"
        interests = tuple(extract_interests(text))
        if interests not in seen_sf:
            seen_sf[interests] = format_suitable_for(list(interests))
        suitable_for = seen_sf[interests]
        rows.append({"module_code": code, "summary": summary, "suitable_for": suitable_for})

    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["module_code", "summary", "suitable_for"])
        writer.writeheader()
        writer.writerows(rows)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"Generated {output_csv} and {output_json} with {len(modules)} modules, {len(seen_sf)} unique suitable_for values")


if __name__ == "__main__":
    main()
