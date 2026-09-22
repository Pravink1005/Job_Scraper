from pathlib import Path
import re
import joblib


# ==============================
# MODEL FOLDER PATH
# ==============================

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"


# ==============================
# SAFELY LOAD MODELS
# ==============================

def safe_load_model(path):
    try:
        return joblib.load(path)
    except Exception as error:
        print(f"[ML Model Error] Failed to load {path}: {error}")
        return None


degree_vectorizer = safe_load_model(MODEL_DIR / "degree_vectorizer.pkl")
degree_model = safe_load_model(MODEL_DIR / "degree_model.pkl")
specialization_vectorizer = safe_load_model(MODEL_DIR / "specialization_vectorizer.pkl")
specialization_model = safe_load_model(MODEL_DIR / "specialization_model.pkl")


SKILL_CATALOG = {
    "programming_languages": {
        "Python": ["python"],
        "SQL": ["sql", "sql server", "t-sql", "pl/sql"],
        "R": ["r programming", "r language"],
        "Java": ["java"],
        "JavaScript": ["javascript", "js"],
        "TypeScript": ["typescript", "ts"],
        "Node.js": ["node.js", "nodejs", "node js"],
        "PHP": ["php"],
        "C#": ["c#", "c sharp", "csharp"],
        "C++": ["c++", "cpp"],
        ".NET": [".net", "dotnet"],
    },
    "frameworks_and_apis": {
        "React": ["react", "react.js", "reactjs"],
        "Angular": ["angular", "angular.js", "angularjs"],
        "Vue.js": ["vue", "vue.js", "vuejs"],
        "Django": ["django"],
        "Flask": ["flask"],
        "FastAPI": ["fastapi", "fast api"],
        "Spring": ["spring", "spring boot"],
        "REST APIs": ["rest api", "rest apis", "restful api", "api development"],
        "GraphQL": ["graphql"],
        "Microservices": ["microservices", "micro-services"],
    },
    "data_and_ai": {
        "Pandas": ["pandas"],
        "NumPy": ["numpy"],
        "Spark": ["spark", "apache spark"],
        "PySpark": ["pyspark"],
        "Airflow": ["airflow", "apache airflow"],
        "ETL": ["etl", "extract transform load"],
        "ELT": ["elt", "extract load transform"],
        "Data Warehousing": ["data warehouse", "data warehousing"],
        "Data Modeling": ["data modeling", "data modelling"],
        "Machine Learning": ["machine learning", "ml"],
        "Deep Learning": ["deep learning"],
        "Natural Language Processing": ["natural language processing", "nlp"],
        "Generative AI": ["generative ai", "genai"],
        "LLMs": ["llm", "llms", "large language model", "large language models"],
        "Computer Vision": ["computer vision"],
    },
    "databases": {
        "PostgreSQL": ["postgresql", "postgres"],
        "MySQL": ["mysql"],
        "Microsoft SQL Server": ["sql server", "mssql"],
        "Oracle Database": ["oracle database", "oracle db"],
        "MongoDB": ["mongodb", "mongo db"],
        "Redis": ["redis"],
        "Elasticsearch": ["elasticsearch", "elastic search"],
    },
    "cloud_and_devops": {
        "AWS": ["aws", "amazon web services"],
        "Azure": ["azure", "microsoft azure"],
        "GCP": ["gcp", "google cloud", "google cloud platform"],
        "Docker": ["docker", "containerization", "containerisation"],
        "Kubernetes": ["kubernetes", "k8s"],
        "Terraform": ["terraform"],
        "CI/CD": ["ci/cd", "continuous integration", "continuous delivery", "continuous deployment"],
        "Git": ["git", "github", "gitlab", "bitbucket"],
        "Linux": ["linux"],
    },
    "business_and_analytics": {
        "Power BI": ["power bi", "powerbi"],
        "Tableau": ["tableau"],
        "Excel": ["excel", "microsoft excel"],
        "Statistics": ["statistics", "statistical analysis"],
        "A/B Testing": ["a/b testing", "ab testing", "split testing"],
        "Forecasting": ["forecasting", "forecast models"],
        "Business Analysis": ["business analysis", "business analyst"],
    },
    "professional_skills": {
        "Communication": ["communication skills", "written communication", "verbal communication"],
        "Leadership": ["leadership", "team leadership", "people management"],
        "Problem Solving": ["problem solving", "problem-solving", "troubleshooting"],
        "Project Management": ["project management", "project manager"],
        "Agile": ["agile", "scrum", "kanban"],
    },
}


def _skill_pattern(alias):
    escaped = re.escape(alias).replace(r"\ ", r"\s+")
    return rf"(?<!\w){escaped}(?!\w)"


DISCOVERY_PREFIXES = re.compile(
    r"^\s*(?:(?:required|preferred|mandatory|nice\s+to\s+have)\s+)?"
    r"(?:skills?|technologies?|tools?|platforms?|frameworks?|knowledge|"
    r"proficiency|experience|familiarity|hands[- ]on experience|using|including)"
    r"\s*(?:with|in|of|on|such as|like)?\s*[:\-]?\s*",
    re.IGNORECASE,
)
DISCOVERY_ACTIONS = {
    "apply", "build", "collaborate", "contribute", "create", "develop",
    "design", "ensure", "implement", "integrate", "maintain", "manage",
    "optimize", "participate", "perform", "provide", "support", "use",
    "write",
}
DISCOVERY_STOP_WORDS = {
    "and", "or", "the", "a", "an", "of", "with", "in", "on", "to",
    "experience", "knowledge", "proficiency", "familiarity", "skills",
    "tools", "platforms", "systems", "solutions", "development", "working",
    "team", "teams", "clients", "customers", "business", "technology",
    "skills", "skill", "communication", "teamwork",
}


def _discover_skill_candidates(text):
    candidates = []
    lines = re.split(r"\r?\n+", str(text))
    for line in lines:
        line = re.sub(r"^[\s*•▪◦\-]+", "", line).strip()
        if not line:
            continue
        is_bullet = bool(re.match(r"^[\s*•▪◦\-]+", line))
        prefix_match = DISCOVERY_PREFIXES.match(line)
        if not prefix_match and not is_bullet:
            continue
        content = DISCOVERY_PREFIXES.sub("", line, count=1) if prefix_match else line
        for candidate in re.split(r",|;|\s+and\s+|\s+or\s+", content, flags=re.IGNORECASE):
            candidate = re.sub(r"\([^)]*\)", "", candidate)
            candidate = re.sub(r"[^A-Za-z0-9+#./ -]", " ", candidate).strip(" .:-")
            words = candidate.split()
            if not words or len(words) > 5 or len(candidate) > 50:
                continue
            if words[0].lower() in DISCOVERY_ACTIONS:
                candidate = " ".join(words[1:]).strip()
                words = candidate.split()
            if not candidate or words[0].lower() in DISCOVERY_ACTIONS:
                continue
            if all(word.lower() in DISCOVERY_STOP_WORDS for word in words):
                continue
            if any(word.lower() in {"strong", "excellent", "preferred", "required", "ability"} for word in words):
                continue
            if candidate.lower() not in {item.lower() for item in candidates}:
                candidates.append(candidate)
    return candidates


def extract_skills_structured(text):
    if not text or text == "N/A":
        return {}

    structured = {}
    for category, skills in SKILL_CATALOG.items():
        matches = {}
        for skill, aliases in skills.items():
            evidence = next(
                (alias for alias in aliases if re.search(_skill_pattern(alias), text, re.IGNORECASE)),
                None,
            )
            if evidence:
                matches[skill] = evidence
        if matches:
            structured[category] = matches

    known_skills = {
        skill.lower()
        for skills in structured.values()
        for skill in skills
    }
    discovered = {
        candidate: candidate
        for candidate in _discover_skill_candidates(text)
        if candidate.lower() not in known_skills
    }
    if discovered:
        structured["discovered_skills"] = discovered
    return structured


def extract_skills(text):
    structured = extract_skills_structured(text)
    found = [skill for skills in structured.values() for skill in skills]
    return ", ".join(found) if found else "Not Specified"


def extract_experience_years(text):
    if not text or text == "N/A":
        return "Not Specified", "Not Specified"

    normalized_text = str(text).replace("–", "-").replace("—", "-")
    number = r"\d+(?:\.\d+)?"
    patterns = [
        rf"({number})\s*(?:to|-)\s*({number})\s*(?:years?|yrs?)",
        rf"(?:at least|minimum|min)\s*({number})\s*(?:years?|yrs?)",
        rf"({number})\s*\+\s*(?:years?|yrs?)",
        rf"({number})\s*(?:years?|yrs?)\s+of\s+experience",
        rf"experience\s*[:=-]\s*({number})\s*(?:years?|yrs?)",
    ]

    candidate_context = re.compile(
        r"\b(?:experience|experienced|candidate|role|position|developer|analyst|"
        r"engineer|consultant|professional|working|employment|years?\s+in)\b",
        re.IGNORECASE,
    )
    company_context = re.compile(
        r"\b(?:company|companies|founded|established|company history|years?\s+in\s+business|"
        r"operating|serving|organization|employees|revenue|industry)\b",
        re.IGNORECASE,
    )
    company_age_context = re.compile(
        rf"\b(?:with|over|more\s+than|has|have)\s+{number}\s+years?\s+of\s+experience\b",
        re.IGNORECASE,
    )
    sentences = re.split(r"\r?\n+|(?<=[.!?])\s+", normalized_text)

    for sentence in sentences:
        if (
            not candidate_context.search(sentence)
            or company_context.search(sentence)
            or company_age_context.search(sentence)
        ):
            continue
        for pattern in patterns:
            match = re.search(pattern, sentence, re.IGNORECASE)
            if not match:
                continue
            values = match.groups()
            if len(values) == 2:
                return values[0], values[1]
            return values[0], f"{values[0]}+"

    return "Not Specified", "Not Specified"


# ==============================
# EXPLICIT DEGREE PATTERNS
# ==============================

DEGREE_PATTERNS = {
    "B.E/B.Tech": [
        r"\bB\.\s*E\.?\b",
        r"\bB\.?\s*Tech\.?\b",
        r"\bBachelor\s+of\s+Engineering\b",
        r"\bBachelor\s+of\s+Technology\b",
    ],
    "B.Sc": [
        r"\bB\.?\s*Sc\.?\b",
        r"\bBachelor\s+of\s+Science\b",
        r"\bBS\b",
    ],
    "BCA": [
        r"\bBCA\b",
        r"\bBachelor\s+of\s+Computer\s+Applications\b",
    ],
    "B.Com": [
        r"\bB\.?\s*Com\.?\b",
        r"\bBachelor\s+of\s+Commerce\b",
    ],
    "BBA": [
        r"\bBBA\b",
        r"\bBachelor\s+of\s+Business\s+Administration\b",
    ],
    "M.E/M.Tech": [
        r"\bM\.\s*E\.?\b",
        r"\bM\.?\s*Tech\.?\b",
        r"\bMaster\s+of\s+Engineering\b",
        r"\bMaster\s+of\s+Technology\b",
    ],
    "M.Sc": [
        r"\bM\.?\s*Sc\.?\b",
        r"\bMaster\s+of\s+Science\b",
        r"\bMS\b",
    ],
    "MCA": [
        r"\bMCA\b",
        r"\bMaster\s+of\s+Computer\s+Applications\b",
    ],
    "MBA": [
        r"\bMBA\b",
        r"\bMaster\s+of\s+Business\s+Administration\b",
    ],
    "PhD": [
        r"\bPh\.?\s*D\.?\b",
        r"\bPhD\b",
        r"\bDoctorate\b",
    ],
    "Diploma": [
        r"\bDiploma\b",
        r"\bEngineering\s+Diploma\b",
    ],
    "Any Bachelor's Degree": [
        r"\bBachelor'?s\s+or\s+Master'?s\s+degree\b",
        r"\bBachelor'?s\s+or\s+associate\s+degree\b",
        r"\bBachelor(?:'s)?\s+or\s+associate\s+degree\b",
        r"\bBachelor(?:'s)?\s+degree\b",
        r"\bBachelor'?s\s+degree\b",
        r"\bBachelor'?s\s+qualification\b",
        r"\bAny\s+recognized\s+Bachelor'?s\s+degree\b",
    ],
    "Any Master's Degree": [
        r"\bMaster(?:'s)?\s+degree\b",
        r"\bMaster'?s\s+degree\b",
        r"\bMaster'?s\s+qualification\b",
        r"\bAny\s+recognized\s+Master'?s\s+degree\b",
    ],
}


# ==============================
# EXPLICIT SPECIALIZATION PATTERNS
# ==============================

SPECIALIZATION_PATTERNS = [
    ("AI/ML", [
        r"\bAI\s*/\s*ML\b",
        r"\b(?:AI|ML)\s*(?:engineer|developer|scientist|specialist|role|team|model|pipeline|architect)\b",
        r"\b(?:artificial\s+intelligence|machine\s+learning|deep\s+learning|computer\s+vision|natural\s+language\s+processing|generative\s+AI|LLM|large\s+language\s+model)\b",
        r"\b(?:artificial\s+intelligence|machine\s+learning|deep\s+learning|computer\s+vision|natural\s+language\s+processing|generative\s+AI|LLM)\s+(?:engineer|developer|scientist|specialist|role|team)\b",
        r"\b(?:PyTorch|TensorFlow|scikit-learn|Keras|Hugging\s+Face|LangChain|OpenCV|transformers)\b",
    ]),
    ("Data Science", [
        r"\bdata\s+scientist\b",
        r"\bdata\s+science\b",
        r"\banalytics\b",
        r"\bstatistical\s+analysis\b",
        r"\bexperimental\s+design\b",
        r"\bpredictive\s+modeling\b",
        r"\bforecasting\b",
        r"\bpower\s+bi\b",
        r"\bpython\s+and\s+sql\b",
        r"\bpython\s*[,\)]?\s*and\s*sql\b",
        r"\bSQL\s+and\s+Python\b",
    ]),
    ("Data Engineering", [
        r"\bdata engineering\b",
        r"\bdata engineer\b",
        r"\betl\b",
        r"\bdata pipelines\b",
        r"\bdbt\b",
        r"\bAzure\s+Data\s+Factory\b",
        r"\bKusto\b",
        r"\bdata\s+warehouse\b",
        r"\bstreaming\s+data\b",
    ]),
    ("IoT", [
        r"\bInternet\s+of\s+Things\b",
        r"\bIoT\b",
        r"\bIOT\b",
        r"\bembedded\s+systems\b",
        r"\bsmart\s+devices\b",
        r"\bsensor\s+networks\b",
        r"\bindustrial\s+IoT\b",
        r"\bedge\s+computing\b",
        r"\bdevice\s+integration\b",
    ]),
    ("Software Engineering", [
        r"\bsoftware engineering\b",
        r"\bsoftware engineer\b",
        r"\bfull stack\b",
        r"\bbackend\b",
        r"\bfrontend\b",
        r"\bJavaScript\b",
        r"\bPython\b",
        r"\bAPI\s+development\b",
        r"\bweb\s+development\b",
    ]),
    ("Computer Science", [
        r"\bcomputer science\b",
        r"\bCS\b",
        r"\bsoftware development\b",
        r"\balgorithm\b",
        r"\bdata structures\b",
        r"\bcomputer\s+applications\b",
    ]),
    ("Cyber Security", [
        r"\bcyber security\b",
        r"\bsecurity engineering\b",
        r"\bcybersecurity\b",
        r"\bnetwork security\b",
        r"\binformation\s+security\b",
    ]),
    ("Electrical Engineering", [
        r"\belectrical engineering\b",
        r"\belectronics\b",
        r"\bpower systems\b",
        r"\bcontrol systems\b",
        r"\bembedded\s+hardware\b",
    ]),
    ("Mechanical Engineering", [
        r"\bmechanical engineering\b",
        r"\bmanufacturing\b",
        r"\bindustrial engineering\b",
        r"\bproduction\s+engineering\b",
    ]),
    ("Finance", [
        r"\bfinance\b",
        r"\bfinancial\b",
        r"\bfinancial\s+services\b",
        r"\bfinancial\s+data\b",
        r"\binvestment\s+management\b",
        r"\binvestment\s+industry\b",
    ]),
    ("Business Administration", [
        r"\bbusiness administration\b",
        r"\bMBA\b",
        r"\boperations\b",
        r"\bstrategy\b",
        r"\bfinance\s+analyst\b",
    ]),
]


# ==============================
# HELPER FUNCTIONS
# ==============================

def extract_degree_text(job_description):
    if not job_description or not job_description.strip():
        return ""

    normalized_description = job_description.replace("’", "'").replace("‘", "'")
    sentences = re.split(r"\r?\n+|(?<=[.!?])\s+", normalized_description)
    degree_pattern = re.compile(
        r"\b(?:degree\b(?!-)|qualification|education|bachelor(?:'s)?(?=\s+(?:degree|in|of|or))|master(?:'s)?(?=\s+(?:degree|in|of|or))|phd|doctorate|"
        r"undergraduate|postgraduate|academic|major|field of study)\b",
        re.IGNORECASE,
    )
    return " ".join(
        sentence.strip()
        for sentence in sentences
        if sentence.strip() and degree_pattern.search(sentence)
    )


def detect_explicit_degree(job_description):
    if not job_description or not job_description.strip():
        return []

    normalized_description = extract_degree_text(job_description)
    found = []
    for degree, patterns in DEGREE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized_description, re.IGNORECASE):
                found.append(degree)
                break
    return list(dict.fromkeys(found))


GENERIC_AI_EXCLUDES = [
    "ai tools",
    "use ai tools",
    "ai-assisted",
    "artificial intelligence (ai) tools",
    "we may use artificial intelligence (ai) tools",
    "ai included",
    "ai tool",
    "ai-powered",
    "ai-driven",
]


def extract_specialization_text(job_description):
    if not job_description or not job_description.strip():
        return ""

    sentences = re.split(r"\r?\n+|(?<=[.!?])\s+", job_description)
    degree_pattern = re.compile(
        r"\b(?:degree|qualification|education|bachelor|master|phd|doctorate|"
        r"undergraduate|postgraduate|academic|major|field of study)\b",
        re.IGNORECASE,
    )
    return " ".join(sentence.strip() for sentence in sentences if sentence.strip() and not degree_pattern.search(sentence))


def detect_explicit_specialization(job_description):
    if not job_description or not job_description.strip():
        return []

    cleaned = extract_specialization_text(job_description).lower()
    for phrase in GENERIC_AI_EXCLUDES:
        cleaned = cleaned.replace(phrase, " ")

    if re.search(r"\blooking\s+for\s+(?:a\s+)?data\s+analyst\b", cleaned):
        return ["Data Analyst"]

    if re.search(
        r"\b(?:python|java|software|backend|full[- ]stack)\s+developer\b|\bsoftware\s+engineer\b",
        cleaned,
    ):
        return ["Software Engineering"]

    if re.search(r"\bdata\s+engineering\b|\bdata\s+engineer\b", cleaned):
        return ["Data Engineering"]

    if re.search(r"\bresearch\s+analyst\b", cleaned) and re.search(
        r"\b(?:business\s+)?operations?\b|\bdata\s+analysis\b|\bdata\s+modeling\b",
        cleaned,
    ):
        return ["Business Analytics"]

    if re.search(
        r"\bdata\s+pipelines?\b|\b(?:PySpark|Spark\s+SQL)\b|\bdata\s+warehous(?:e|ing)\b|\bELT\b",
        cleaned,
        re.IGNORECASE,
    ):
        return ["Data Engineering"]

    scores = []
    for idx, (specialization, patterns) in enumerate(SPECIALIZATION_PATTERNS):
        score = 0
        for pattern in patterns:
            if re.search(pattern, cleaned, re.IGNORECASE):
                score += 1
        if score > 0:
            scores.append((specialization, score, idx))

    if not scores:
        return []

    scores.sort(key=lambda item: (-item[1], item[2]))
    return [specialization for specialization, _, _ in scores]


# ==============================
# DEGREE PREDICTION
# ==============================

def predict_degree(job_description):
    if not job_description or not job_description.strip():
        return "Not Specified"

    explicit = detect_explicit_degree(job_description)
    if explicit:
        return " / ".join(explicit)

    degree_text = extract_degree_text(job_description)
    if degree_text and re.search(r"\bdegree\s+in\b", degree_text, re.IGNORECASE):
        return "Not Specified"

    if degree_model is not None and degree_vectorizer is not None:
        try:
            if not degree_text:
                return "Not Specified"
            text_vector = degree_vectorizer.transform([degree_text])
            probabilities = degree_model.predict_proba(text_vector)[0]
            best_index = probabilities.argmax()
            predicted_degree = str(degree_model.classes_[best_index])
            confidence = probabilities[best_index] * 100
            if confidence >= 60:
                return predicted_degree
        except Exception as error:
            print(f"[ML Prediction Error] Degree inference failed: {error}")
            pass

    return "Not Specified"


# ==============================
# SPECIALIZATION PREDICTION
# ==============================

def predict_specialization(job_description):
    if not job_description or not job_description.strip():
        return "Not Specified"

    explicit = detect_explicit_specialization(job_description)
    if explicit:
        return explicit[0]

    if specialization_model is not None and specialization_vectorizer is not None:
        try:
            cleaned_description = extract_specialization_text(job_description)
            text_vector = specialization_vectorizer.transform([cleaned_description])
            probabilities = specialization_model.predict_proba(text_vector)[0]
            best_index = probabilities.argmax()
            predicted_specialization = str(specialization_model.classes_[best_index])
            confidence = probabilities[best_index] * 100
            if confidence >= 60:
                return predicted_specialization
        except Exception as error:
            print(f"[ML Prediction Error] Specialization inference failed: {error}")
            pass

    return "Not Specified"


# ==============================
# COMPLETE JOB PREDICTION
# ==============================

def predict_job_details(job_description):
    degree = predict_degree(job_description)
    specialization = predict_specialization(job_description)

    return {
        "predicted_degree": degree,
        "predicted_specialization": specialization,
    }