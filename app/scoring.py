import re
from html import unescape


PROFILE_KEYWORDS = {
    "power bi": 16,
    "dashboard": 15,
    "data visualization": 14,
    "business intelligence": 13,
    "bi developer": 12,
    "data analyst": 12,
    "data scientist": 11,
    "analytics engineer": 10,
    "data engineer": 10,
    "sql": 9,
    "python": 9,
    "api": 8,
    "dax": 8,
    "power query": 8,
    "monitoring and evaluation": 8,
    "m&e": 8,
    "kobo": 7,
    "odk": 7,
    "rapidpro": 6,
    "tableau": 6,
    "looker": 5,
    "superset": 5,
    "grafana": 5,
    "survey": 5,
    "health information": 5,
    "gis": 4,
}

DOMAIN_KEYWORDS = {
    "data-bi": [
        "power bi",
        "dashboard",
        "data visualization",
        "business intelligence",
        "bi developer",
        "data analyst",
        "data scientist",
        "analytics engineer",
        "data engineer",
        "sql",
        "dax",
        "power query",
        "tableau",
        "looker",
        "superset",
        "grafana",
        "cognos",
    ],
    "suivi-evaluation-etudes": [
        "monitoring and evaluation",
        "m&e",
        "mel",
        "meal",
        "research",
        "study",
        "survey",
        "evaluation",
        "impact",
        "indicator",
        "data collection",
        "charged etude",
        "charge d'etude",
        "chargé d'étude",
        "suivi evaluation",
        "suivi-evaluation",
    ],
    "developpement-app": [
        "application",
        "app developer",
        "software developer",
        "web developer",
        "full stack",
        "full-stack",
        "frontend",
        "backend",
        "react",
        "vue",
        "angular",
        "django",
        "flask",
        "api",
        "platform",
        "systems integration",
        "website",
        "mobile app",
    ],
    "communication": [
        "communication",
        "communications",
        "content",
        "storytelling",
        "infographic",
        "infographics",
        "advocacy",
        "campaign",
        "social media",
        "digital media",
        "graphic design",
        "report writing",
        "editorial",
        "publication",
    ],
}

TRACK_TERMS = {
    "consultance": [
        "consultant",
        "consultancy",
        "individual consultant",
        "freelance",
        "contractor",
        "request for proposal",
        "request for proposals",
        "request for quote",
        "request for quotes",
        "request for quotation",
        "rfp",
        "rfq",
        "tor",
        "terms of reference",
        "call for proposals",
        "expression of interest",
        "eoi",
    ],
    "emploi-data": [
        "full-time",
        "part-time",
        "permanent",
        "employee",
        "job",
        "analyst",
        "scientist",
        "engineer",
        "manager",
        "officer",
        "specialist",
    ],
}

TITLE_ANCHORS = [
    "power bi",
    "dashboard",
    "data visualization",
    "business intelligence",
    "bi developer",
    "data analyst",
    "data scientist",
    "analytics engineer",
    "data engineer",
    "information management",
    "monitoring and evaluation",
    "m&e",
    "kobo",
    "odk",
    "tableau",
    "looker",
    "superset",
    "grafana",
]

DESCRIPTION_STRONG_ANCHORS = [
    "power bi",
    "dashboard",
    "business intelligence",
    "data visualization",
    "dax",
    "power query",
    "tableau",
    "looker",
    "superset",
    "grafana",
    "kobo",
    "odk",
    "monitoring and evaluation",
    "m&e",
]

ENGINEERING_TITLE_TERMS = [
    "software engineer",
    "product engineer",
    "devops engineer",
    "ai engineer",
    "genai engineer",
    "frontend engineer",
    "front-end engineer",
    "backend engineer",
    "back-end engineer",
    "full stack engineer",
    "full-stack engineer",
]

VERY_STRONG_DESCRIPTION_ANCHORS = [
    "power bi",
    "dax",
    "power query",
    "tableau",
    "looker",
    "superset",
    "grafana",
    "kobo",
    "odk",
]

REMOTE_TERMS = [
    "remote",
    "fully remote",
    "full remote",
    "work from anywhere",
    "anywhere",
    "home-based",
    "home based",
    "telework",
    "teletravail",
    "tele-travail",
    "worldwide",
    "global",
    "africa remote",
    "remote africa",
    "distributed",
]

ONSITE_TERMS = [
    "on-site",
    "onsite",
    "on site",
    "must be based in",
    "based in office",
    "office-based",
    "full-time office",
    "in-office",
    "relocation required",
    "requires being onsite",
    "required onsite",
    "no remote",
    "not remote",
    "remote work not considered",
    "remote not considered",
    "must spend at least",
]


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize(value: str | None) -> str:
    return clean_text(value).lower()


def classify_remote(title: str, location: str, description: str) -> tuple[str, bool]:
    text = normalize(" ".join([title or "", location or "", description or ""]))
    hard_onsite = [
        "no remote",
        "not remote",
        "remote option is not available",
        "remote work not considered",
        "remote not considered",
        "requires being onsite",
        "must spend at least 50% of their time in-office",
        "must be present in these locations",
    ]
    if any(term in text for term in hard_onsite):
        return "onsite", False
    if any(term in text for term in ONSITE_TERMS) and not any(term in text for term in REMOTE_TERMS):
        return "onsite", False
    if any(term in text for term in REMOTE_TERMS):
        if "hybrid" in text or "hybride" in text:
            return "hybrid-remote", True
        return "remote", True
    if re.search(r"\b(utc|gmt)[+-]?\d|\bemea\b|\bglobal\b|\bworldwide\b", text):
        return "remote-likely", True
    return "unknown", False


def score_opportunity(title: str, organization: str, location: str, description: str) -> tuple[int, list[str], str, bool]:
    text = normalize(" ".join([title or "", organization or "", location or "", description or ""]))
    score = 0
    matched = []
    for keyword, weight in PROFILE_KEYWORDS.items():
        if keyword in text:
            score += weight
            matched.append(keyword)

    remote_type, is_remote = classify_remote(title, location, description)
    if is_remote:
        score += 25
    else:
        score -= 35

    if any(term in text for term in ["contract", "consultant", "freelance", "temporary", "short-term"]):
        score += 8
        matched.append("consultance/contract")

    if any(term in text for term in ["united states only", "us only", "u.s. only", "must reside in the us"]):
        score -= 30
        matched.append("restriction pays")

    return max(0, min(100, score)), sorted(set(matched)), remote_type, is_remote


def classify_track_domain(title: str, opportunity_type: str, description: str) -> tuple[str, str]:
    text = normalize(" ".join([title or "", opportunity_type or "", description or ""]))

    consultance_score = sum(1 for term in TRACK_TERMS["consultance"] if term in text)
    emploi_score = sum(1 for term in TRACK_TERMS["emploi-data"] if term in text)
    track = "consultance" if consultance_score >= max(1, emploi_score) else "emploi-data"

    domain_scores = {
        domain: sum(1 for keyword in keywords if keyword in text)
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }
    domain = max(domain_scores, key=domain_scores.get)
    if domain_scores[domain] == 0:
        domain = "autres"

    return track, domain


def has_profile_anchor(title: str, description: str) -> bool:
    title_text = normalize(title)
    body_text = normalize(description)
    title_match = any(anchor in title_text for anchor in TITLE_ANCHORS)
    body_match = any(anchor in body_text for anchor in DESCRIPTION_STRONG_ANCHORS)
    engineering_title = any(term in title_text for term in ENGINEERING_TITLE_TERMS)
    if engineering_title and not title_match:
        return any(anchor in body_text for anchor in VERY_STRONG_DESCRIPTION_ANCHORS)
    return title_match or body_match
