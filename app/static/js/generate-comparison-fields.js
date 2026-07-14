const fs = require('fs');
const path = require('path');

const dataPath = path.join(__dirname, '..', 'data', 'rp-modules-final.json');

const themeRules = [
    {
        pattern: /3d print|additive manufactur|prototype|printed object/i,
        feature: '3D design, printing, prototyping, and post-processing',
        audience: 'hands-on making, product design, prototyping, and creative technology'
    },
    {
        pattern: /\b(food|nutrition|diet|wellness|eating)\b|health benefit/i,
        feature: 'food, nutrition, wellness, and healthy lifestyle choices',
        audience: 'food, nutrition, wellness, and making healthier lifestyle decisions'
    },
    {
        pattern: /sustainab|green|environment|planet|climate|ecology|ecological/i,
        feature: 'sustainability, environmental practices, and social responsibility',
        audience: 'sustainability, environmental issues, and community impact'
    },
    {
        pattern: /biodiversity|wildlife|plants|geography|ecology|ecosystem/i,
        feature: 'biodiversity, local wildlife, plant life, geography, and ecological patterns',
        audience: 'nature, biodiversity, environmental awareness, and local ecosystems'
    },
    {
        pattern: /anatomy|physiology|human body|skeletal|muscular|nervous|respiratory/i,
        feature: 'human body systems, anatomy, physiology, and biological functions',
        audience: 'health sciences, human biology, sports science, and healthcare pathways'
    },
    {
        pattern: /patient care|healthcare|health professional|hospital|clinical|medical record|patient/i,
        feature: 'patient care, healthcare settings, communication, and professional practice',
        audience: 'healthcare, patient support, clinical environments, and people-centred service'
    },
    {
        pattern: /\b(biology|biological|bio-innovation|biodiversity|cell|cells|genetic|genetics|evolution|biomolecule|microbiology)\b/i,
        feature: 'biological concepts, cells, genetics, and scientific investigation',
        audience: 'biology, life sciences, research, and scientific problem-solving'
    },
    {
        pattern: /chemistry|chemical|organic|inorganic|molecule|titration|stoichiometry/i,
        feature: 'chemical principles, laboratory techniques, reactions, and data interpretation',
        audience: 'chemistry, applied science, laboratory work, and analytical thinking'
    },
    {
        pattern: /physics|kinematic|thermodynamic|optics|electromagnet|mechanics|force|energy/i,
        feature: 'physics principles, calculations, real-life applications, and practical activities',
        audience: 'physics, engineering, applied science, and quantitative problem-solving'
    },
    {
        pattern: /facilit(?:y|ies) management|building facilit|fire protection|hazard mitigation|housekeeping/i,
        feature: 'facilities management, building systems, safety, risk control, and operations',
        audience: 'built environments, facilities operations, workplace safety, and service management'
    },
    {
        pattern: /laboratory|lab |glp|documentation|iso|quality management/i,
        feature: 'laboratory practices, safety, documentation, quality standards, and compliance',
        audience: 'laboratory work, applied science operations, quality control, and safe practice'
    },
    {
        pattern: /programming|software|coding|app development|web development|\bweb\b|database|python|java|javascript/i,
        feature: 'programming, software development, applications, and technical problem-solving',
        audience: 'coding, software development, digital products, and computational thinking'
    },
    {
        pattern: /\bdata analytics\b|\banalytics\b|statistics|visuali[sz]ation|dashboard|database|machine learning|artificial intelligence|\bai\b/i,
        feature: 'data analysis, digital tools, evidence-based insights, and decision support',
        audience: 'data, analytics, technology, research, and evidence-based decision-making'
    },
    {
        pattern: /data communication|network technology|networking|computer network/i,
        feature: 'networking technologies, data communication concepts, and industry-relevant IT infrastructure',
        audience: 'networking, IT infrastructure, communications technology, and technical systems'
    },
    {
        pattern: /cyber|security|forensic|threat|vulnerab|encryption/i,
        feature: 'cybersecurity, networks, digital risks, and protection strategies',
        audience: 'cybersecurity, IT infrastructure, digital defence, and technical investigation'
    },
    {
        pattern: /business|marketing|entrepreneur|customer|consumer|retail|brand|sales/i,
        feature: 'business concepts, market awareness, customer needs, and practical decision-making',
        audience: 'business, entrepreneurship, marketing, customer experience, and commercial strategy'
    },
    {
        pattern: /finance|accounting|financial|investment|bank|budget|cost/i,
        feature: 'financial concepts, accounting practices, analysis, and business decision-making',
        audience: 'finance, accounting, business planning, and analytical decision-making'
    },
    {
        pattern: /live sound|sound event|audio|broadcast|recording|front of house|\bfoh\b/i,
        feature: 'audio production, live sound techniques, recording, and broadcast applications',
        audience: 'audio production, live events, sound engineering, and technical media work'
    },
    {
        pattern: /hospitality|hotel|tourism|travel|event|leisure|guest/i,
        feature: 'hospitality, tourism, service operations, guest experience, and event contexts',
        audience: 'hospitality, tourism, events, service design, and people-focused work'
    },
    {
        pattern: /media|design|animation|game|creative|visual|story|content|film|audio/i,
        feature: 'creative production, design thinking, media tools, and visual communication',
        audience: 'design, media, storytelling, creative production, and visual expression'
    },
    {
        pattern: /engineering|electronic|robot|iot|sensor|manufactur|automation|mechanical/i,
        feature: 'engineering concepts, technical systems, applied design, and practical problem-solving',
        audience: 'engineering, technology, systems thinking, and hands-on technical work'
    },
    {
        pattern: /challenge course|adventure programming|outdoor|participant profile/i,
        feature: 'challenge course operations, adventure learning, participant needs, and safety-aware management',
        audience: 'outdoor learning, adventure education, facilitation, and activity management'
    },
    {
        pattern: /sport|exercise|fitness|health promotion|rehabilitation|coaching/i,
        feature: 'sports science, health, fitness, movement, and performance-related concepts',
        audience: 'sports, health promotion, exercise science, coaching, and active lifestyles'
    },
    {
        pattern: /communication|writing|presentation|language|interpersonal|negotiation/i,
        feature: 'communication skills, writing, presentation, and interpersonal effectiveness',
        audience: 'communication, writing, teamwork, presentations, and people-facing roles'
    },
    {
        pattern: /psychology|social|counselling|community|behaviour|human service/i,
        feature: 'human behaviour, social issues, community contexts, and people-centred practice',
        audience: 'psychology, social service, community work, and understanding people'
    },
    {
        pattern: /logistics|supply chain|transport|procurement|operation/i,
        feature: 'operations, logistics, supply chain processes, and resource coordination',
        audience: 'logistics, operations, supply chain management, and process improvement'
    },
    {
        pattern: /math|calculus|algebra|statistic|quantitative|probability/i,
        feature: 'mathematical concepts, quantitative reasoning, and problem-solving techniques',
        audience: 'mathematics, analytics, engineering, science, and structured problem-solving'
    }
];

const practiceRules = [
    { pattern: /hands-on|practical|practice session|workshop|build|create|design/i, phrase: 'hands-on activities' },
    { pattern: /laboratory|lab |experiment|testing/i, phrase: 'laboratory practice' },
    { pattern: /project|prototype|develop|produce/i, phrase: 'project-based work' },
    { pattern: /case stud|real[- ]life|industry|workplace|scenario/i, phrase: 'real-world applications' },
    { pattern: /problem|solve|calculat|interpret|analyse|analyze/i, phrase: 'problem-solving tasks' }
];

function cleanText(value) {
    return String(value || '')
        .replace(/\s+/g, ' ')
        .trim();
}

function unique(items) {
    return [...new Set(items.filter(Boolean))];
}

function joinHuman(items) {
    const cleanItems = unique(items);
    if (cleanItems.length === 0) return '';
    if (cleanItems.length === 1) return cleanItems[0];
    if (cleanItems.length === 2) return `${cleanItems[0]} and ${cleanItems[1]}`;
    return `${cleanItems.slice(0, -1).join(', ')}, and ${cleanItems[cleanItems.length - 1]}`;
}

function titleTopic(module) {
    const name = cleanText(module.name)
        .replace(/\b(introduction to|introductory|fundamentals of|principles of)\b/gi, '')
        .replace(/[^\w\s&-]/g, '')
        .replace(/\s+/g, ' ')
        .trim()
        .toLowerCase();

    return name || 'this topic';
}

function matchTheme(module) {
    const name = cleanText(module.name);
    const body = `${cleanText(module.description)} ${cleanText(module.school)} ${cleanText(module.category)}`;

    const nameMatch = themeRules.find(rule => rule.pattern.test(name));
    if (nameMatch) return nameMatch;

    return themeRules.find(rule => rule.pattern.test(body));
}

function matchPractice(text) {
    return practiceRules
        .filter(rule => rule.pattern.test(text))
        .map(rule => rule.phrase);
}

function generateFields(module) {
    const text = `${cleanText(module.name)}. ${cleanText(module.description)} ${cleanText(module.school)} ${cleanText(module.category)}`;
    const theme = matchTheme(module);
    const practices = matchPractice(text).slice(0, 2);

    const topic = titleTopic(module);

    let features;
    if (theme) {
        features = `Covers ${theme.feature}`;
    } else {
        features = `Introduces key concepts and practical understanding in ${topic}`;
    }

    if (practices.length > 0) {
        features += ` through ${joinHuman(practices)}`;
    }
    features += '.';

    let suitableFor;
    if (theme) {
        suitableFor = `Students interested in ${theme.audience}.`;
    } else {
        suitableFor = `Students who want an introductory understanding of ${topic}.`;
    }

    return { features, suitableFor };
}

const modules = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
const updatedModules = modules.map(module => {
    const generated = generateFields(module);
    return {
        ...module,
        features: generated.features,
        suitableFor: generated.suitableFor
    };
});

fs.writeFileSync(dataPath, `${JSON.stringify(updatedModules, null, 2)}\n`);

console.log(`Generated comparison fields for ${updatedModules.length} modules.`);
