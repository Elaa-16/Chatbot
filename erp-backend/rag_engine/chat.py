import logging
import json
import os
import re as _re
import requests
import unicodedata
from collections import Counter

def strip_accents(s: str) -> str:
    if not isinstance(s, str): return ""
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
from datetime import date as _date

from groq import Groq
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Config
API_BASE_URL = "http://localhost:8000"
GROQ_MODEL   = "llama-3.3-70b-versatile"

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

embeddings = OllamaEmbeddings(model="mxbai-embed-large")

vector_store = Chroma(
    collection_name="erp_apis",
    embedding_function=embeddings,
    persist_directory=r"C:\Users\msi\Chatbot\erp-backend\rag_engine\erp_chroma_db"
)
api_retriever = vector_store.as_retriever(
    search_kwargs={"k": 14, "filter": {"category": "api"}}
)
doc_retriever = vector_store.as_retriever(
    search_kwargs={"k": 25, "filter": {"category": {
        "$in": ["policy", "procedure", "glossaire", "project_report",
                "kpi_analysis", "employee_guide", "equipment_guide",
                "supplier_info", "internal_communication"]
    }}}
)


# ═══════════════════════════════════════════════════════════════════════════════
# GROQ CALLER — replaces OllamaLLM chains
# ═══════════════════════════════════════════════════════════════════════════════
def _call_groq(prompt: str, json_mode: bool = False, temperature: float = 0.0) -> str:
    kwargs = {
        "model":       GROQ_MODEL,
        "messages":    [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens":  4096,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    try:
        response = groq_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error("Groq API error: %s", e)
        return "{}" if json_mode else ""


# ── Allowed endpoints per role
ROLE_ALLOWED_ENDPOINTS = {
    "ceo": [
        "/projects", "/kpis", "/tasks", "/tasks/by-manager", "/employees",
        "/leave-requests", "/issues", "/timesheets", "/equipment", "/suppliers",
        "/purchase-orders", "/notifications", "/stats/summary", "/stats/tasks", "/stats/by-manager"
    ],
    "manager": [
        "/projects", "/tasks", "/tasks/by-manager", "/employees",
        "/leave-requests", "/issues", "/timesheets", "/notifications",
        "/stats/tasks", "/kpis", "/suppliers", "/purchase-orders"
    ],
    "rh": ["/leave-requests", "/employees", "/notifications"],
    "employee": ["/tasks", "/leave-requests", "/timesheets", "/notifications", "/kpis"],
}

_ROLE_SCOPE_MSG = {
    "employee": (
        "Cette information n'est pas accessible avec votre role.\n\n"
        "En tant qu'employe, vous pouvez consulter :\n"
        "  - Vos taches assignees\n  - Vos conges et leur statut\n"
        "  - Vos feuilles de temps\n  - Vos notifications\n  - Les KPIs de vos projets"
    ),
    "rh": (
        "Cette information n'est pas accessible avec votre role.\n\n"
        "En tant que RH, vous pouvez consulter :\n"
        "  - La liste des employes\n  - Les conges et absences\n  - Les notifications"
    ),
    "manager": (
        "Cette information n'est pas accessible avec votre role.\n\n"
        "En tant que manager, vous pouvez consulter :\n"
        "  - Vos projets et KPIs\n  - Les taches de votre equipe\n"
        "  - Les conges de votre equipe\n  - Les incidents sur vos projets\n"
        "  - Les feuilles de temps\n  - Les notifications"
    ),
}

# ═══════════════════════════════════════════════════════════════════════════════
# HTTP API CALLER
# ═══════════════════════════════════════════════════════════════════════════════
_REQUEST_CACHE: dict = {}


def _cache_key(endpoint: str, params: dict) -> tuple:
    clean = {k: v for k, v in params.items() if v not in (None, "", False) and k != "active_today"}
    return (endpoint, tuple(sorted(clean.items())))


def call_api(endpoint: str, params: dict, token: str) -> list | dict:
    if endpoint in ("/tasks/by-manager", "/stats/by-manager", "/stats/tasks"):
        return _compute_virtual_endpoint(endpoint, token)

    url     = f"{API_BASE_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {token}"}
    clean_params = {k: v for k, v in params.items() if v not in (None, "", False) and k != "active_today"}

    _ck = _cache_key(endpoint, params)
    if len(clean_params) <= 2 and _ck in _REQUEST_CACHE:
        return _REQUEST_CACHE[_ck]

    try:
        resp = requests.get(url, params=clean_params, headers=headers, timeout=15)
        logger.info("API %s %s -> %d", endpoint, clean_params, resp.status_code)
        if resp.status_code == 200:
            data = resp.json()
            if len(clean_params) <= 2:
                _REQUEST_CACHE[_ck] = data
            return data
        elif resp.status_code in (401, 403):
            return []
        elif resp.status_code == 404:
            return []
        else:
            logger.error("API %s -> %d : %s", endpoint, resp.status_code, resp.text[:200])
            return []
    except requests.exceptions.ConnectionError:
        logger.error("Cannot reach %s", API_BASE_URL)
        return []
    except Exception as e:
        logger.error("call_api %s : %s", endpoint, e)
        return []


def _compute_virtual_endpoint(endpoint: str, token: str) -> list:
    headers = {"Authorization": f"Bearer {token}"}

    if endpoint == "/stats/tasks":
        try:
            r = requests.get(f"{API_BASE_URL}/tasks", headers=headers, timeout=15)
            tasks = r.json() if r.status_code == 200 else []
        except Exception:
            return []
        sc = Counter(t.get("status", "") for t in tasks)
        pc = Counter(t.get("priority", "") for t in tasks)
        return [{"total_tasks": len(tasks), "todo": sc.get("Todo", 0),
                 "in_progress": sc.get("In Progress", 0), "done": sc.get("Done", 0),
                 "blocked": sc.get("Blocked", 0), "critical": pc.get("Critical", 0),
                 "high": pc.get("High", 0)}]

    try:
        tasks     = call_api("/tasks",     {}, token)
        employees = call_api("/employees", {}, token)
    except Exception:
        return []

    managers   = {e["employee_id"]: e for e in employees if e.get("role") == "manager"}
    emp_to_mgr: dict = {}
    for mgr in managers.values():
        sup = mgr.get("supervised_employees") or ""
        for eid in [x.strip() for x in sup.replace(";", ",").split(",") if x.strip()]:
            emp_to_mgr[eid] = mgr["employee_id"]

    mgr_tasks: dict = {mid: [] for mid in managers}
    for t in tasks:
        aid = t.get("assigned_to", "")
        mid = emp_to_mgr.get(aid) or (aid if aid in managers else None)
        if mid:
            mgr_tasks[mid].append(t)

    result = []
    for mid, mgr in managers.items():
        tlist    = mgr_tasks.get(mid, [])
        sc       = Counter(t.get("status", "")   for t in tlist)
        pc       = Counter(t.get("priority", "") for t in tlist)
        done_n   = sc.get("Done", 0)
        total    = len(tlist)
        done_pct = round(done_n * 100 / total) if total > 0 else 0
        result.append({
            "manager_id": mid,
            "manager_name": f"{mgr.get('first_name','')} {mgr.get('last_name','')}".strip(),
            "department": mgr.get("department", ""),
            "total_tasks": total, "blocked": sc.get("Blocked", 0),
            "blocked_tasks": sc.get("Blocked", 0), "todo": sc.get("Todo", 0),
            "in_progress": sc.get("In Progress", 0), "done": done_n,
            "done_tasks": done_n, "done_pct": done_pct,
            "critical_tasks": pc.get("Critical", 0),
            "open_critical": sum(1 for t in tlist if t.get("priority") == "Critical" and t.get("status") != "Done"),
            "high_tasks": pc.get("High", 0),
            "total_projects": len({t.get("project_id") for t in tlist if t.get("project_id")}),
        })

    result.sort(key=lambda r: (-(r["blocked"]), -(r["critical_tasks"])))
    if any(r["blocked"] > 0 for r in result):
        result = [r for r in result if r["blocked"] > 0]
    return result[:20]


# ═══════════════════════════════════════════════════════════════════════════════
# SANITIZE FILTERS
# ═══════════════════════════════════════════════════════════════════════════════
def sanitize_filters(filters) -> dict:
    if not isinstance(filters, dict):
        return {}
    clean = {}
    for k, v in filters.items():
        if isinstance(v, list):
            if v:
                clean[k] = v[0]
        elif isinstance(v, bool):
            clean[k] = v
        elif v is not None and v != "":
            clean[k] = v
    return clean


def _rerank_doc_chunks(chunks: list, question: str, top_k: int = 5) -> list:
    if not chunks:
        return []
    q_lower = question.lower()
    # Extract keywords from question for reranking
    keywords = [w for w in q_lower.split() if len(w) > 3
                and w not in {"quel","quels","quelle","quelles","est","sont","pour",
                              "dans","avec","cette","politique","quelle","comment",
                              "nous","vous","les","des","une","que","qui"}]
    if not keywords:
        return chunks[:top_k]

    def score(chunk):
        text = chunk.page_content.lower()
        return sum(1 for kw in keywords if kw in text)

    # Sort by keyword relevance, keep top_k
    ranked = sorted(chunks, key=score, reverse=True)
    return ranked[:top_k]


# ═══════════════════════════════════════════════════════════════════════════════
# GLOSSAIRE
# ═══════════════════════════════════════════════════════════════════════════════
_DEFINITION_PATTERNS = [
    "c'est quoi", "cest quoi", "qu'est-ce que", "quest ce que",
    "definition", "définition", "explique", "signifie", "que veut dire",
]
_ERP_DEFINITIONS = {
    "spi": "**SPI** (Schedule Performance Index) — SPI = EV/PV. SPI=1 dans les temps, >1 avance, <1 retard.",
    "cpi": "**CPI** (Cost Performance Index) — CPI = EV/AC. CPI=1 dans le budget, >1 sous budget, <1 hors budget.",
    "kpi": "**KPI** (Key Performance Indicator) — indicateur cle de performance. KPIs ERP : SPI, CPI, budget_variance_percentage, schedule_variance_days, quality_score, risk_level.",
    "ev":  "**EV** (Earned Value) : valeur budgetaire du travail accompli a date.",
    "pv":  "**PV** (Planned Value) : valeur budgetaire du travail prevu a date.",
    "ac":  "**AC** (Actual Cost) : cout reellement depense.",
    "erp": "**ERP** (Enterprise Resource Planning) : logiciel de gestion integre. Ici, systeme de gestion des projets BTP.",
    "hse": "**HSE** (Hygiene, Securite, Environnement) : departement responsable de la securite sur les chantiers.",
    "epi": "**EPI** (Equipements de Protection Individuelle) : casque, chaussures de securite, gilet, gants, lunettes, harnais. Port obligatoire sur tous les chantiers.",
    "btp": "**BTP** (Batiment et Travaux Publics) : secteur de la construction.",
    "moa": "**MOA** (Maitre d'Ouvrage) : entite qui commande et finance le projet.",
    "moe": "**MOE** (Maitre d'Oeuvre) : entite chargee de la conception et du suivi des travaux.",
    "ao":  "**AO** (Appel d'Offres) : procedure par laquelle le maitre d'ouvrage sollicite des offres pour la realisation de travaux.",
    "bpe": "**BPE** (Beton Pret a l'Emploi) : beton fabrique en centrale et livre sur chantier.",
    "tf":  "**TF** (Taux de Frequence) = Accidents x 1 000 000 / Heures travaillees.",
    "tg":  "**TG** (Taux de Gravite) = Jours perdus x 1 000 / Heures travaillees.",
}

def is_definition_question(q: str) -> bool:
    return any(p in strip_accents(q.lower()) for p in _DEFINITION_PATTERNS)

def handle_definition_question(q: str) -> str | None:
    q_l = strip_accents(q.lower())
    q_words = _re.findall(r"[a-z]+", q_l)
    for key, answer in _ERP_DEFINITIONS.items():
        if key in q_words:
            return answer
    for key, answer in _ERP_DEFINITIONS.items():
        if len(key) > 3 and key in q_l:
            return answer
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# QUESTIONS PROCEDURALES
# ═══════════════════════════════════════════════════════════════════════════════
_PROCEDURAL_PATTERNS = [
    "procedure", "procédure", "processus", "comment fonctionne", "comment se passe",
    "comment faire", "quelle est la regle", "quelle est la politique", "politique de",
    "reglement", "règlement", "etapes", "étapes", "qui approuve", "qui valide",
    "delai de", "délai de", "comment calculer", "conditions pour", "dans quel cas",
    "comment soumettre", "comment deposer", "comment demander", "comment creer",
    "comment faire une demande", "comment poser", "soumettre une demande",
    "faire une demande de", "demande de conge", "demander un conge",
    "quel est le processus", "quelle est la procedure",
    "combien de jours de preavis", "qui doit approuver",
    "quelles sont les conditions", "quelles sont les regles",
    "quels sont les types", "quels documents",
]

def is_procedural_question(q: str) -> bool:
    q_l = strip_accents(q.lower())
    if not any(p in q_l for p in _PROCEDURAL_PATTERNS):
        return False
    _DATA_INTENT = [
        "montre", "affiche", "liste des", "statut de", "etat de",
        "mon statut", "ma demande", "mes demandes", "voir ma", "voir mes",
        "est-ce que ma", "a ete approuvee", "a ete refusee",
    ]
    return not any(w in q_l for w in _DATA_INTENT)


# ═══════════════════════════════════════════════════════════════════════════════
# MEETING / C.R. QUESTION CLASSIFIER
# ═══════════════════════════════════════════════════════════════════════════════
_MEETING_PATTERNS = [
    "reunion", "réunion", "compte rendu", "cr ", "notes de secretaire", "notes de secrétaire",
    "discut", "meeting"
]

def is_meeting_question(q: str) -> bool:
    q_l = strip_accents(q.lower())
    return any(p in q_l for p in _MEETING_PATTERNS)# ═══════════════════════════════════════════════════════════════════════════════
# POLICY QUESTION CLASSIFIER (v30)
# ═══════════════════════════════════════════════════════════════════════════════
_POLICY_PATTERNS = [
    r"\bcombien de jours\b", r"\bdroit (a|au|aux)\b",
    r"\bduree (du|de la|des) conge", r"\bconge (annuel|maladie|maternite|paternite|exceptionnel|sans solde)\b",
    r"\bpreavis\b", r"\bque se passe.t.il si\b", r"\bqui approuve\b",
    r"\bsolde de conge\b", r"\breport.? (de|des) conge",
    r"\bepi\b", r"\bequipement.? de protection\b", r"\baccident.? sur chantier\b",
    r"\bformation securite\b", r"\bharnais\b", r"\bcertificat medical\b",
    r"\btaux de frequence\b", r"\btaux de gravite\b",
    r"\bhoraires (de travail|du bureau|chantier)\b",
    r"\bmajoration\b", r"\bsanction\b", r"\bavertissement\b",
    r"\bprime.? (de fin|chantier|annuel)\b", r"\bmise a pied\b", r"\blicenciement\b",
    r"\bheures supplementaires\b", r"\bpointage\b",
    r"\bprocessus d.achat\b", r"\bcombien de devis\b",
    r"\bdelai de paiement\b", r"\bdelai.? de resolution\b",
    r"\bonboarding\b", r"\bperiode d.essai\b",
    r"\bmaintenance preventive\b", r"\ben cas de panne\b",
    r"\bque se passe.t.il\b",
    r"\bque risque\b",
    r"\bdepasser .{0,10} solde\b",
    r"\bconsequence.? (d.une|en cas)\b",
]
_re_policy = _re.compile("|".join(_POLICY_PATTERNS), _re.IGNORECASE)

_POLICY_DATA_OVERRIDE = [
    "montre", "affiche", "liste des", "donne moi", "quels sont les",
    "statut de", "ma demande", "mes demandes",
    "actuellement", "en ce moment", "aujourd'hui", "maintenant",
    "me restent", "il me reste", "jours restants", "jours me restent",
    "a pris", "a pose", "cette annee", "au total", "en tout",
    # NOTE: "mon solde" removed — "depasse mon solde" is a policy question
]

# Questions that look like policy but are actually about personal live data
_POLICY_LIVE_DATA = [
    "mon solde de conge",     # -> balance check -> #H6
    "combien me reste",       # -> balance check -> #H6
]

def is_policy_question(q: str) -> bool:
    q_l = strip_accents(q.lower())
    if "[employee_id=" in q:
        return False
    if any(w in q_l for w in _POLICY_DATA_OVERRIDE):
        return False
    return bool(_re_policy.search(q_l))


# ═══════════════════════════════════════════════════════════════════════════════
# LEAVE BALANCE HANDLER (v30)
# ═══════════════════════════════════════════════════════════════════════════════
_LEAVE_BALANCE_PATTERNS = [
    r"\bme restent\b", r"\bil me reste\b", r"\bjours restants\b",
    r"\bjours me restent\b", r"\bmon solde de cong[ee]\b",
]
_re_leave_balance = _re.compile("|".join(_LEAVE_BALANCE_PATTERNS), _re.IGNORECASE)
_LEAVE_ENTITLEMENTS = {"Annual": 35, "Sick": 30, "Maternity": 60, "Paternity": 3, "Exceptional": 5, "Unpaid": 30}
_DEFAULT_ANNUAL_ENTITLEMENT = 35


def is_leave_balance_question(q: str) -> bool:
    q_l = strip_accents(q.lower())
    return any(w in q_l for w in ["cong", "absence", "solde", "jours"]) and bool(_re_leave_balance.search(q_l))


def _handle_leave_balance(user_id: str, token: str, user_name: str = "") -> str:
    leave_data = call_api("/leave-requests", {"employee_id": user_id}, token)
    if not isinstance(leave_data, list):
        leave_data = []
    approved = [r for r in leave_data if r.get("status", "").lower() == "approved"]
    pending  = [r for r in leave_data if r.get("status", "").lower() == "pending"]
    taken_by_type: dict = {}
    for r in approved:
        ltype = r.get("leave_type", "Annual")
        taken_by_type[ltype] = taken_by_type.get(ltype, 0) + (r.get("total_days", 0) or 0)
    annual_taken   = taken_by_type.get("Annual", 0)
    annual_pending = sum(r.get("total_days", 0) or 0 for r in pending if r.get("leave_type") == "Annual")
    annual_remaining = _DEFAULT_ANNUAL_ENTITLEMENT - annual_taken
    # Resolve name from cache if no leave records found
    emp_name = (approved[0].get("employee_name", "") if approved else
                pending[0].get("employee_name", "") if pending else "")
    if not emp_name:
        for e in _EMPLOYEE_CACHE:
            if e["id"] == user_id:
                emp_name = e["full_name"]
                break
    if not emp_name:
        emp_name = user_name if user_name else user_id
    lines = [
        f"**Solde de congés — {emp_name}**", "",
        f"📋 Congé annuel (droit : {_DEFAULT_ANNUAL_ENTITLEMENT}j selon politique RH)",
        f"  • Pris (approuvés)   : {annual_taken}j",
    ]
    if annual_pending > 0:
        lines.append(f"  • En attente         : {annual_pending}j")
    lines.append(f"  • **Solde restant    : {annual_remaining}j** ✅")
    other = {k: v for k, v in taken_by_type.items() if k != "Annual" and v > 0}
    if other:
        lines += ["", "Autres conges pris :"]
        for lt, d in other.items():
            ent = _LEAVE_ENTITLEMENTS.get(lt, "--")
            lines.append(f"  - {lt} : {d}j pris" + (f" / {ent}j autorises" if isinstance(ent, int) else ""))
    if not approved and not pending:
        lines = [
            f"**Solde de congés — {emp_name}**", "",
            f"Vous n'avez pris aucun congé cette année.",
            f"",
            f"✅ Solde disponible : **{_DEFAULT_ANNUAL_ENTITLEMENT} jours** de congé annuel",
        ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# RAG-ONLY CALL FOR POLICY QUESTIONS (v30)
# ═══════════════════════════════════════════════════════════════════════════════
def _ask_llm_rag_only(question: str, user_id: str = "", token: str = "") -> str:
    raw_chunks  = doc_retriever.invoke(question)
    proc_chunks = _rerank_doc_chunks(raw_chunks, question, top_k=6)
    print(f"DEBUG RAG: raw_chunks={len(raw_chunks)} proc_chunks={len(proc_chunks)}")
    for i, ch in enumerate(proc_chunks):
        print(f"DEBUG RAG chunk[{i}]: file={ch.metadata.get('filename','?')} cat={ch.metadata.get('category','?')}")
        print(f"  preview: {ch.page_content[:150]}")
    logger.info("RAG policy: %d chunks retrieved", len(proc_chunks))
    doc_ctx = "\n\n".join(
        f"[{ch.metadata.get('category', '')} -- {ch.metadata.get('filename', 'doc')}]\n{ch.page_content}"
        for ch in proc_chunks
    )
    print(f"DEBUG RAG doc_ctx length: {len(doc_ctx)} chars")
    if not doc_ctx.strip():
        print("DEBUG RAG: NO CHUNKS FOUND — ChromaDB may be empty!")
        logger.warning("RAG: NO CHUNKS — vector store empty or mismatch")
        return "Je n'ai pas trouve de documentation sur ce sujet dans les politiques internes."
    prompt     = RAG_DOC_TEMPLATE.format(doc_context=doc_ctx, question=question)
    rag_answer = clean_answer(_call_groq(prompt))
    _balance_kws = ["me restent", "mon solde", "il me reste", "jours restants"]
    if user_id and token and any(kw in question.lower() for kw in _balance_kws):
        try:
            leave_data = call_api("/leave-requests", {"employee_id": user_id}, token)
            if leave_data and isinstance(leave_data, list):
                approved  = [r for r in leave_data if r.get("status", "").lower() == "approved"]
                taken     = sum(r.get("total_days", 0) or 0 for r in approved)
                remaining = 35 - taken
                rag_answer += (f"\n\n**Votre solde personnel (donnees live) :**\n"
                               f"- Jours pris : {taken}j\n- Solde restant : **{remaining}j**")
        except Exception as e:
            logger.warning("_ask_llm_rag_only: live enrichment failed: %s", e)
    return rag_answer


# ═══════════════════════════════════════════════════════════════════════════════
# PLANNER FALLBACK RULES
# ═══════════════════════════════════════════════════════════════════════════════
_DEPARTMENT_ALIASES = {
    "finance": "Finance", "projet": "Projects", "projects": "Projects",
    "operations": "Operations", "ressources humaines": "Human Resources",
    "rh": "Human Resources", "informatique": "IT", "it": "IT",
    "direction": "Executive", "executive": "Executive",
}
_STATUS_ALIASES = {
    "bloque": "Blocked", "bloqué": "Blocked", "en cours": "In Progress",
    "a faire": "Todo", "todo": "Todo", "termine": "Done", "done": "Done",
    "planning": "Planning", "complete": "Completed", "completed": "Completed",
    "ouvert": "Open", "open": "Open", "resolu": "Resolved",
    "approuve": "Approved", "en attente": "Pending", "pending": "Pending",
    "rejete": "Rejected", "disponible": "Available", "maintenance": "Maintenance",
    "utilise": "In Use",
}
_PRIORITY_ALIASES = {
    "critique": "Critical", "critical": "Critical",
    "haute": "High", "high": "High", "moyenne": "Medium", "medium": "Medium",
    "basse": "Low", "low": "Low", "faible": "Low",
}
_SEVERITY_ALIASES = _PRIORITY_ALIASES.copy()
_CATEGORY_ALIASES = {
    "securite": "Safety", "safety": "Safety", "qualite": "Quality", "quality": "Quality",
    "delai": "Delay", "delay": "Delay", "budget": "Budget",
    "technique": "Technical", "technical": "Technical", "autre": "Other", "other": "Other",
}


def _extract_filters_from_question(q_lower: str, endpoint: str) -> dict:
    filters = {}
    if endpoint == "/employees":
        for alias, dept in _DEPARTMENT_ALIASES.items():
            if alias in q_lower:
                filters["department"] = dept
                break
        for rk, rv in [("manager","manager"),("ceo","ceo"),("employ","employee"),("rh","rh")]:
            if rk in q_lower and "department" not in filters:
                filters["role"] = rv
                break
    if endpoint == "/kpis":
        if any(w in q_lower for w in ["retard", "delayed", "delai", "schedule"]):
            filters["delayed"] = True
        if any(w in q_lower for w in ["risque", "risk"]):
            filters["risk_level"] = "High"
    if endpoint in ("/tasks", "/projects", "/issues", "/leave-requests", "/equipment"):
        for alias, val in _STATUS_ALIASES.items():
            if alias in q_lower:
                filters["status"] = val
                break
    if endpoint == "/tasks":
        for alias, val in _PRIORITY_ALIASES.items():
            if alias in q_lower:
                filters["priority"] = val
                break
    if endpoint == "/suppliers":
        if any(w in q_lower for w in ["meilleures notes", "meilleure note", "top", "mieux note", "note", "rating"]):
            filters["sort_by_rating"] = True
        if any(w in q_lower for w in ["materiau", "materiaux", "material"]):
            filters["category"] = "Materials"
        elif any(w in q_lower for w in ["equipement", "equipment", "engin"]):
            filters["category"] = "Equipment"
        elif any(w in q_lower for w in ["service"]):
            filters["category"] = "Services"
        if any(w in q_lower for w in ["actif", "active", "actifs"]):
            filters["status"] = "Active"
        elif any(w in q_lower for w in ["inactif", "inactive"]):
            filters["status"] = "Inactive"

    if endpoint == "/equipment":
        status_map = {
            "disponible": "Available", "available": "Available",
            "en cours": "In Use", "utilise": "In Use", "in use": "In Use",
            "maintenance": "Maintenance",
        }
        for alias, val in status_map.items():
            if alias in q_lower:
                filters["status"] = val
                break

    if endpoint == "/issues":
        for alias, val in _SEVERITY_ALIASES.items():
            if alias in q_lower:
                filters["severity"] = val
                break
        for alias, val in _CATEGORY_ALIASES.items():
            if alias in q_lower:
                filters["category"] = val
                break
    if endpoint == "/leave-requests":
        if any(kw in q_lower for kw in ["maintenant", "aujourd", "en ce moment", "actuellement"]):
            filters["active_today"] = True
    return filters


_FALLBACK_RULES = [
    (["employe", "personnel", "salarie", "staff"],  "/employees"),
    (["retard", "delayed", "kpi", "indicateur"],    "/kpis"),
    (["projet", "chantier"],                        "/projects"),
    (["tache", "task"],                             "/tasks"),
    (["conge", "absence", "absent"],                "/leave-requests"),
    (["incident", "issue", "probleme"],             "/issues"),
    (["kpi", "indicateur"],                         "/kpis"),
    (["equipement", "materiel"],                    "/equipment"),
    (["fournisseur", "supplier", "fournisseurs"],   "/suppliers"),
    (["commande", "purchase", "bon de commande", "bdc"], "/purchase-orders"),
    (["resume", "synthese", "statistique", "stat"], "/stats/summary"),
    (["client", "clients"],                         "/projects"),
]


def _apply_fallback_plan(q_lower: str, role_allowed: list) -> list:
    for keywords, endpoint in _FALLBACK_RULES:
        if endpoint not in role_allowed:
            continue
        if any(kw in q_lower for kw in keywords):
            return [{"endpoint": endpoint, "filters": _extract_filters_from_question(q_lower, endpoint)}]
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════
RAG_DOC_TEMPLATE = """Tu es un assistant RH interne pour une entreprise de construction tunisienne.
Tu reponds en francais, de maniere claire et structuree.
Tu reponds UNIQUEMENT a partir des DOCUMENTS fournis ci-dessous.
Si l information exacte n est pas dans les documents, dis : "Je n ai pas trouve cette information dans les politiques internes."
Ne mentionne jamais les noms de fichiers ou les sources.
Commence directement par la reponse, sans introduction.
Utilise des tirets ou des numeros pour structurer si necessaire.

DOCUMENTS:
{doc_context}

Question: {question}

Reponse:"""

PLANNER_TEMPLATE = """Tu es un planificateur de requetes pour un ERP de construction.
Tu dois repondre UNIQUEMENT avec du JSON brut. Pas de texte. Pas de Bonjour. Juste le JSON.

Endpoints disponibles: {available_endpoints}

VALEURS EXACTES DANS LA BASE DE DONNEES:
- Projects status: "In Progress", "Completed", "Planning"
- Tasks status: "Todo", "In Progress", "Done", "Blocked"
- Tasks priority: "Critical", "High", "Medium", "Low"
- Issues severity: "Critical", "High", "Medium", "Low"
- Issues status: "Open", "In Progress", "Resolved", "Closed"
- Issues category: "Safety", "Quality", "Delay", "Budget", "Technical", "Other"
- Leave status: "Approved", "Rejected", "Pending"
- Equipment status: "Available", "In Use", "Maintenance"
- Employee roles: "ceo", "manager", "employee", "rh"
- Employee departments: "Finance", "Projects", "Operations", "Human Resources", "IT", "Executive"

REGLES DE MAPPING:
- liste employes, tous les employes, personnel → /employees avec {}
- employes d un departement → /employees avec {"department": "NomExact"}
- projets en retard, retard, delai → /kpis avec {"delayed": true}
- projets a risque eleve → /kpis avec {"risk_level": "High"}
- IMPORTANT: pour /kpis le risque max est "High", jamais "Critical"
- taches critiques → /tasks avec {"priority": "Critical"}
- taches critiques non terminees → /tasks avec {"priority": "Critical"}
- taches bloquees → /tasks avec {"status": "Blocked"}
- taches en cours → /tasks avec {"status": "In Progress"}
- mes taches → /tasks avec {"status": "In Progress"}
- taches bloquees par manager → /tasks/by-manager avec {}
- performance des managers → /tasks/by-manager avec {}
- employes en conge → /leave-requests avec {"status": "Approved"}
- employes en conge maintenant → /leave-requests avec {"status": "Approved", "active_today": true}
- si question contient [active_today=true] → ajouter "active_today": true
- conges en attente → /leave-requests avec {"status": "Pending"}
- statut de ma demande de conge → /leave-requests avec {"employee_id": "{user_id}"}
- tous les conges → /leave-requests avec {}
- incidents critiques → /issues avec {"severity": "Critical"}
- incidents ouverts → /issues avec {"status": "Open"}
- projets en cours → /projects avec {"status": "In Progress"}
- equipements disponibles → /equipment avec {"status": "Available"}
- equipements en cours → /equipment avec {"status": "In Use"}
- equipements en maintenance → /equipment avec {"status": "Maintenance"}
- equipements sur un projet → /equipment avec {"current_project_id": "<ID>"}
- tous les equipements → /equipment avec {}
- statistiques globales → /stats/summary avec {}
- kpis, performance projets → /kpis avec {}
- evolution kpi, tendance kpi, historique kpi, kpi sur X mois → /kpis avec {"history": true}
- evolution cpi, tendance spi, comment a evolue → /kpis avec {"history": true}
- liste clients, mes clients → /projects avec {}
- projets d un client X → /projects avec {"client_name": "<NomClient>"}

REGLE CRITIQUE — [employee_id=Exx] DANS LA QUESTION:
Si la question contient [employee_id=Exx, nom=Prenom Nom], tu DOIS adapter les endpoints au SUJET de la question :

- Question sur les CONGES, ABSENCES, JOURS → UNIQUEMENT /leave-requests avec {"employee_id": "Exx"}
- Question sur les TACHES, TRAVAUX → UNIQUEMENT /tasks avec {"assigned_to": "Exx"}
- Question sur les HEURES, TIMESHEET → UNIQUEMENT /timesheets avec {"employee_id": "Exx"}
- Question sur le PROFIL, INFORMATIONS GENERALES, tout sur cet employe → /employees + /leave-requests + /tasks + /timesheets
- Question sur la PERFORMANCE → /tasks avec {"assigned_to": "Exx"} + /timesheets avec {"employee_id": "Exx"}

NE JAMAIS appeler tous les endpoints si la question est specifique a un seul sujet.

SECURITE:
- role=employee: ajouter assigned_to="{user_id}" pour /tasks
- role=employee: ajouter employee_id="{user_id}" pour /leave-requests et /timesheets
- role=rh: utiliser UNIQUEMENT /leave-requests et /employees
- role=manager: NE JAMAIS ajouter assigned_to="{user_id}" aux filtres /tasks
- role=manager: NE JAMAIS ajouter employee_id="{user_id}" sauf si question explicite sur le manager

FORMAT STRICT:
- INTERDIT: liste dans les filtres
- INTERDIT: cle "params" — utiliser UNIQUEMENT "filters"
- INTERDIT: plus de 5 endpoints
- FORMAT: {"reasoning": "...", "endpoints": [...]}

REGLE EQUIPE MANAGER:
- mon equipe, mes employes → /employees avec {"supervised_by": "{user_id}"}
- conges de mon equipe → /leave-requests avec {"supervised_by": "{user_id}"}
- taches de mon equipe → /tasks avec {"supervised_by": "{user_id}"}

Role: {user_role} | ID: {user_id}
Question: {question}

JSON:"""

ANSWER_TEMPLATE = """Tu es un assistant ERP. Tu reponds en francais.
Tu affiches les donnees EXACTEMENT comme elles apparaissent dans DONNEES LIVE.

REGLES ABSOLUES:
R1. Si DONNEES LIVE contient un bloc "=== ... ===", le recopier MOT POUR MOT.
R2. Ne JAMAIS ajouter de phrase introductive, commentaire ou note.
R3. Ne JAMAIS ecrire "Notez que", "Note:", "Cependant".
R4. Ne JAMAIS terminer par une question ou offre d aide.
R5. Ne JAMAIS inventer de donnee absente de DONNEES LIVE.
R6. Si question analytique, texte court structure uniquement depuis DONNEES LIVE.
R7. Si DONNEES LIVE contient "Aucune donnee live" → reponds: "Aucune donnee disponible."
R8. INTERDIT d inventer des noms ou chiffres absents de DONNEES LIVE.
R9. COPIE INTEGRALE : recopier TOUTES les lignes du bloc ===.
R10. INTERDIT d ajouter du texte APRES le dernier bloc ===.

DONNEES LIVE:
{live_context}

CONNAISSANCES DOCUMENTAIRES:
{doc_context}

PROFIL: {user_name} | Role: {user_role}
Question: {question}

REPONSE:"""


# ═══════════════════════════════════════════════════════════════════════════════
# FORMAT HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _resolve_name(emp_id: str) -> str:
    for e in _EMPLOYEE_CACHE:
        if e["id"] == emp_id:
            return e["full_name"]
    return emp_id


def format_endpoint_data(endpoint: str, data: list | dict, filters: dict = {}) -> str:
    label = endpoint.strip("/").replace("/", "-").upper()
    items = data if isinstance(data, list) else [data]

    if endpoint == "/employees":
        if len(items) == 1:
            r = items[0]
            role_map = {"manager":"Manager","ceo":"CEO","rh":"RH","employee":"Employé"}
            role_label = role_map.get(r.get("role",""), r.get("role","").capitalize())
            return (f"=== PROFIL EMPLOYE ===\nNom        : {r.get('first_name','')} {r.get('last_name','')}\nPoste      : {r.get('position','')}\nDepartement: {r.get('department','')}\nRole       : {role_label}\n")
        lines = [f"{r.get('first_name','')} {r.get('last_name','')} -- {r.get('position','')} -- {r.get('department','')}" for r in items]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/tasks":
        lines = [
            f"- {r.get('task_id','')}: {r.get('title','')} | Statut: {r.get('status','')} | "
            f"Priorite: {r.get('priority','')} | Echeance: {r.get('due_date','')} | "
            f"Assigne a: {_resolve_name(r.get('assigned_to',''))} | Projet: {r.get('project_id','')}"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/projects":
        if filters.get("_client_view"):
            seen: set = set()
            cl = []
            for r in items:
                c = r.get("client_name", "")
                if not c or c in seen:
                    continue
                seen.add(c)
                cl.append(f"- {c} | Projet: {r.get('project_name','')} | Statut: {r.get('status','')} | Avancement: {r.get('completion_percentage','')}%")
            return f"=== CLIENTS ===\nResultats ({len(cl)}):\n" + "\n".join(cl) + "\n"
        lines = [
            f"- {r.get('project_id','')}: {r.get('project_name','')} | Client: {r.get('client_name','')} | "
            f"Statut: {r.get('status','')} | Avancement: {r.get('completion_percentage','')}% | "
            f"Budget: {r.get('budget','')} DT | Lieu: {r.get('location','')}"
            for r in items
        ]
        return f"=== PROJECTS ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/leave-requests":
        lines = [
            f"- {r.get('employee_name','')} | Type: {r.get('leave_type','')} | "
            f"Du: {r.get('start_date','')} au {r.get('end_date','')} | Jours: {r.get('total_days','')} | Statut: {r.get('status','')}"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/issues":
        lines = [
            f"- {r.get('issue_id','')}: {r.get('title','')} | Severite: {r.get('severity','')} | "
            f"Categorie: {r.get('category','')} | Statut: {r.get('status','')} | Projet: {r.get('project_id','')}"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/kpis":
        valid = [r for r in items if (r.get('project_name') or r.get('project_id'))
                 and not (r.get('cost_performance_index', 1) == 0 and r.get('schedule_performance_index', 1) == 0)]
        # Detect history mode: multiple rows for the same project
        pids = [r.get('project_id','') for r in valid]
        is_history = len(pids) != len(set(pids))
        if is_history:
            from collections import defaultdict as _dd
            by_proj = _dd(list)
            for r in valid:
                by_proj[r.get('project_name', r.get('project_id',''))].append(r)
            lines = []
            for pname, rows in by_proj.items():
                rows_sorted = sorted(rows, key=lambda x: x.get('kpi_date',''))
                lines.append(f"\n  [{pname}]")
                for r in rows_sorted:
                    lines.append(
                        f"  {r.get('kpi_date','')} | Retard: {r.get('schedule_variance_days','')}j | "
                        f"Budget: {r.get('budget_variance_percentage','')}% | "
                        f"CPI: {r.get('cost_performance_index','')} | "
                        f"SPI: {r.get('schedule_performance_index','')} | "
                        f"Risque: {r.get('risk_level','')}"
                    )
            return f"=== KPIS (historique) ===\nResultats ({len(valid)} entrees / {len(by_proj)} projets):\n" + "\n".join(lines) + "\n"
        # Normal mode: one row per project (latest)
        lines = [
            f"- {r.get('project_name', r.get('project_id',''))} | Retard: {r.get('schedule_variance_days','')}j | "
            f"Budget: {r.get('budget_variance_percentage','')}% | CPI: {r.get('cost_performance_index','')} | "
            f"SPI: {r.get('schedule_performance_index','')} | Risque: {r.get('risk_level','')}"
            for r in valid
        ]
        return f"=== {label} ===\nResultats ({len(valid)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/tasks/by-manager":
        lines = [
            f"- {r.get('manager_name','')} ({r.get('department','')}) | Total: {r.get('total_tasks',0)} | "
            f"Bloques: {r.get('blocked',0)} | Critiques: {r.get('critical_tasks',0)} | "
            f"En cours: {r.get('in_progress',0)} | Termines: {r.get('done',0)} | Avancement: {r.get('done_pct',0)}%"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/stats/by-manager":
        lines = [
            f"- {r.get('manager_name','')} ({r.get('department','')}) | Taches: {r.get('total_tasks',0)} | "
            f"Bloquees: {r.get('blocked_tasks',0)} | Critiques ouvertes: {r.get('open_critical',0)} | "
            f"Terminees: {r.get('done_tasks',0)} | Projets: {r.get('total_projects',0)}"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/timesheets":
        lines = [
            f"- {r.get('employee_id','')} | Projet: {r.get('project_id','')} | "
            f"Date: {r.get('work_date', r.get('date',''))} | Heures: {r.get('hours_worked','')}h | {r.get('task_description','')}"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/equipment":
        lines = [
            f"- {r.get('equipment_id','')}: {r.get('name','')} | Statut: {r.get('status','')} | "
            f"Categorie: {r.get('category','')} | Lieu: {r.get('location','')} | "
            f"Projet: {r.get('current_project_id') or 'N/A'} | "
            f"Prochaine maintenance: {r.get('next_maintenance') or 'N/A'}"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/suppliers":
        # Sort by rating descending if rating filter is implied
        sorted_items = sorted(items, key=lambda r: r.get('rating', 0) or 0, reverse=True)
        lines = [
            f"- {r.get('supplier_name','')} | Categorie: {r.get('category','')} | "
            f"Statut: {r.get('status','')} | Note: {'⭐' * (r.get('rating') or 0)} ({r.get('rating','')}/5) | "
            f"Ville: {r.get('city','')} | Contact: {r.get('contact_person','')}"
            for r in sorted_items
        ]
        return f"=== {label} ===\nResultats ({len(sorted_items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/purchase-orders":
        lines = [
            f"- {r.get('po_id','')} | Projet: {r.get('project_id','')} | Fournisseur: {r.get('supplier_id','')} | "
            f"Montant: {r.get('total_amount',''):,} DT | Statut: {r.get('status','')} | "
            f"Livraison: {r.get('delivery_date','')} | {r.get('items','')[:50]}"
            for r in items
        ]
        total = sum(r.get('total_amount', 0) or 0 for r in items)
        header = f"=== PURCHASE-ORDERS ===\nResultats ({len(items)}) | Total: {total:,.0f} DT:\n"
        return header + "\n".join(lines) + "\n"

    elif endpoint == "/notifications":
        lines = [f"- [{r.get('created_date','')}] {r.get('title','')}: {r.get('message','')} ({'Lu' if r.get('is_read') else 'Non lu'})" for r in items]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/stats/summary":
        r = items[0] if items else {}
        return (f"=== {label} ===\nProjets total: {r.get('total_projects','')} | "
                f"Budget: {r.get('total_budget','')} DT | "
                f"Cout reel: {r.get('total_actual_cost','')} DT | "
                f"Avancement moy: {r.get('avg_completion', r.get('avg_completion_pct',''))}%\n")

    elif endpoint == "/stats/tasks":
        r = items[0] if items else {}
        return (f"=== {label} ===\nTotal: {r.get('total_tasks','')} | A faire: {r.get('todo','')} | "
                f"En cours: {r.get('in_progress','')} | Terminees: {r.get('done','')} | "
                f"Bloquees: {r.get('blocked','')} | Critiques: {r.get('critical','')}\n")

    else:
        lines = ["- " + " | ".join(f"{k}: {v}" for k, v in r.items() if v is not None and k != "password_hash") for r in items[:20]]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"


# ═══════════════════════════════════════════════════════════════════════════════
# PLAN PARSER
# ═══════════════════════════════════════════════════════════════════════════════
def normalize_plan(parsed) -> dict:
    def clean_item(item):
        if not isinstance(item, dict):
            return None
        # Groq sometimes returns "url" or "path" instead of "endpoint"
        ep = item.get("endpoint") or item.get("url") or item.get("path") or ""
        if not ep:
            return None
        # Normalize: strip base URL if present
        if ep.startswith("http"):
            from urllib.parse import urlparse
            ep = urlparse(ep).path
        return {"endpoint": ep, "filters": sanitize_filters(item.get("filters") or item.get("params") or {})}

    if isinstance(parsed, dict):
        if "endpoints" in parsed and isinstance(parsed["endpoints"], list):
            clean = [i for i in [clean_item(x) for x in parsed["endpoints"]] if i]
            return {"endpoints": clean, "reasoning": parsed.get("reasoning", "")}
        if "endpoint" in parsed:
            item = clean_item(parsed)
            if item:
                return {"endpoints": [item], "reasoning": "normalized"}
    if isinstance(parsed, list):
        clean = [i for i in [clean_item(x) for x in parsed if isinstance(x, dict)] if i]
        return {"endpoints": clean, "reasoning": "normalized"}
    return {"endpoints": [], "reasoning": "unknown format"}


def parse_llm_plan(raw: str) -> dict:
    raw = str(raw).strip()
    for attempt in [
        lambda r: json.loads(r),
        lambda r: json.loads(_re.sub(r"\s*```\s*$", "", _re.sub(r"^```(?:json)?\s*", "", r, flags=_re.MULTILINE), flags=_re.MULTILINE).strip()),
        lambda r: json.loads(r[r.find("{"):r.rfind("}")+1]),
    ]:
        try:
            return normalize_plan(attempt(raw))
        except Exception:
            pass
    for src in [raw, raw[raw.find("{"):raw.rfind("}")+1] if "{" in raw else ""]:
        try:
            fixed = src + "]" * max(0, src.count("[") - src.count("]")) + "}" * max(0, src.count("{") - src.count("}"))
            return normalize_plan(json.loads(fixed))
        except Exception:
            pass
    return {"endpoints": [], "reasoning": "parse error"}


# ═══════════════════════════════════════════════════════════════════════════════
# ANSWER POST-PROCESSOR
# ═══════════════════════════════════════════════════════════════════════════════
_LEAK_LINE_PREFIXES = (
    "je vais repondre", "en fonction des regles", "puisque la question", "puisque vous",
    "voici ma reponse", "notez que", "note :", "note:", "il est important",
    "cependant,", "cependant ", "je suppose que", "les employes disponibles sont",
    "puis-je vous", "n'hesitez pas", "si vous avez", "bien cordialement", "cordialement",
    "les projets en retard sont", "voici la liste", "voici les employes",
    "en resume", "pour resumer", "il y a donc", "au total,", "ainsi,",
    "puisque les donnees", "remarque :", "je suis desole",
    "la reponse est", "il y a", "je vois que", "pour repondre",
    "le manager", "ainsi, le", "donc, le", "en conclusion",
    "selon les donnees", "les resultats montrent",
)


def _remove_duplicate_blocks(text: str) -> str:
    pattern   = _re.compile(r"(=== [^=\n]+ ===)", _re.MULTILINE)
    positions = [(m.start(), m.group(1)) for m in pattern.finditer(text)]
    if len(positions) <= 1:
        return text
    blocks = []
    for i, (start, label) in enumerate(positions):
        end = positions[i+1][0] if i+1 < len(positions) else len(text)
        blocks.append((label.strip(), start, end, text[start:end]))

    def dl(content):
        return sum(1 for l in content.splitlines() if l.startswith("- ") or (l and not l.startswith("===")))

    seen: dict = {}
    keep = []
    for idx, (label, s, e, content) in enumerate(blocks):
        if label not in seen:
            seen[label] = (idx, dl(content))
            keep.append(idx)
        else:
            pi, pl = seen[label]
            cl = dl(content)
            if cl > pl:
                keep[keep.index(pi)] = idx
                seen[label] = (idx, cl)
    if len(keep) == len(blocks):
        return text
    return "\n\n".join(blocks[i][3].rstrip() for i in sorted(keep))


def clean_answer(text: str) -> str:
    if "===" in text:
        m = _re.compile(r"(=== [^=\n]+ ===\nResultats \(\d+\):)", _re.MULTILINE).search(text)
        text = text[m.start():] if m else text[text.find("==="):]

    lines   = text.splitlines()
    cleaned = []
    skip    = False
    for line in lines:
        low = line.strip().lower()
        if any(low.startswith(p) for p in _LEAK_LINE_PREFIXES):
            skip = True
            continue
        if skip and line.startswith("==="):
            skip = False
        if not skip:
            cleaned.append(line)

    result = "\n".join(cleaned)
    result = _remove_duplicate_blocks(result)
    result = _re.sub(r"(?im)^(reponse\s*:|donnees\s+live\s*:)", "", result)
    result = _re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE CACHE
# ═══════════════════════════════════════════════════════════════════════════════
_EMPLOYEE_CACHE: list[dict] = []


def load_employee_cache(token: str = "") -> None:
    global _EMPLOYEE_CACHE
    if not token:
        return
    try:
        resp = requests.get(f"{API_BASE_URL}/employees",
                            headers={"Authorization": f"Bearer {token}"}, timeout=15)
        if resp.status_code != 200:
            return
        _EMPLOYEE_CACHE = []
        for r in resp.json():
            fn, ln = r.get("first_name", ""), r.get("last_name", "")
            full   = f"{fn} {ln}".strip()
            full_l = full.lower()
            tris   = {full_l[i:i+3] for i in range(len(full_l)-2)} if len(full_l) > 2 else set()
            _EMPLOYEE_CACHE.append({
                "id": r["employee_id"], "full_name": full, "full_lower": full_l,
                "first": fn.lower(), "last": ln.lower(),
                "initials": f"{fn[0]}. {ln}".lower() if fn else "",
                "position": (r.get("position") or "").lower(),
                "department": (r.get("department") or "").lower(),
                "trigrams": tris,
            })
        logger.info("Employee cache loaded: %d employees", len(_EMPLOYEE_CACHE))
    except Exception as e:
        logger.warning("Could not load employee cache: %s", e)


def _trigram_score(query: str, candidate: dict) -> float:
    q = query.lower()
    if len(q) < 3:
        return 0.0
    q_tris = {q[i:i+3] for i in range(len(q)-2)}
    if not q_tris or not candidate["trigrams"]:
        return 0.0
    return len(q_tris & candidate["trigrams"]) / max(len(q_tris), len(candidate["trigrams"]))


def resolve_employee_name(name: str, threshold: float = 0.45):
    if not _EMPLOYEE_CACHE:
        return None, None
    n = name.strip().lower()
    if not n:
        return None, None
    for e in _EMPLOYEE_CACHE:
        if n == e["full_lower"]:
            return e["id"], e["full_name"]
    m = [e for e in _EMPLOYEE_CACHE if e["initials"] and n == e["initials"]]
    if len(m) == 1:
        return m[0]["id"], m[0]["full_name"]
    m = [e for e in _EMPLOYEE_CACHE if n == e["first"] or n == e["last"]]
    if len(m) == 1:
        return m[0]["id"], m[0]["full_name"]
    if len(m) > 1:
        return "AMBIGUOUS", ", ".join(f"{e['full_name']} ({e['id']})" for e in m)
    m = [e for e in _EMPLOYEE_CACHE if n in e["full_lower"] or e["full_lower"] in n]
    if len(m) == 1:
        return m[0]["id"], m[0]["full_name"]
    if len(m) > 1:
        return "AMBIGUOUS", ", ".join(f"{e['full_name']} ({e['id']})" for e in m)
    scored = sorted([(e, _trigram_score(n, e)) for e in _EMPLOYEE_CACHE], key=lambda x: x[1], reverse=True)
    if scored and scored[0][1] >= threshold:
        best = [e for e, s in scored if s >= threshold]
        if not (len(best) > 1 and scored[1][1] / scored[0][1] > 0.85):
            return scored[0][0]["id"], scored[0][0]["full_name"]
    return None, None


# ═══════════════════════════════════════════════════════════════════════════════
# MANAGER SCOPE
# ═══════════════════════════════════════════════════════════════════════════════
def _get_supervised_employees(manager_id: str, token: str) -> set:
    try:
        resp = requests.get(f"{API_BASE_URL}/employees", params={"employee_id": manager_id},
                            headers={"Authorization": f"Bearer {token}"}, timeout=15)
        if resp.status_code != 200:
            return {manager_id}
        data = resp.json()
        mgr  = data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else {})
        ids  = {x.strip() for x in (mgr.get("supervised_employees", "") or "").replace(";", ",").split(",") if x.strip()}
        ids.add(manager_id)
        return ids
    except Exception as e:
        logger.warning("_get_supervised_employees(%s): %s", manager_id, e)
        return {manager_id}


# ═══════════════════════════════════════════════════════════════════════════════
# PREPROCESS
# ═══════════════════════════════════════════════════════════════════════════════
_NOW_WORDS          = ["en ce moment", "maintenant", "aujourd'hui", "a present", "ce jour", "now", "today"]
_NOW_WORDS_LEAVE_ONLY = ["actuellement"]
_FORMAT_REQUESTS    = ["tableau", "table", "en liste", "details", "resume", "graphique", "chart"]
_SUBJECT_INDICATORS = ["qui", "quels", "quelles", "quel", "quelle", "combien", "liste", "donne", "montre", "affiche"]
_FOLLOWUP_LEAVE     = ["en ce moment", "maintenant", "actuellement", "aujourd'hui", "ce jour", "now", "today"]
_FOLLOWUP_EXPAND    = {
    "conge":    "Quels employes sont en conge en ce moment ? [active_today=true]",
    "absent":   "Quels employes sont absents en ce moment ? [active_today=true]",
    "projet":   "Quels projets sont en cours en ce moment ?",
    "tache":    "Quelles taches sont en cours en ce moment ?",
    "incident": "Quels incidents sont ouverts en ce moment ?",
}


def preprocess_question(question: str, last_exchange=None):
    q       = question.strip()
    q_lower = strip_accents(q.lower())
    words   = q.split()

    if last_exchange and len(words) <= 6:
        if any(fr in q_lower for fr in _FORMAT_REQUESTS):
            prev_q = last_exchange.get("user", "").strip()
            if prev_q:
                return f"{prev_q} ({q})", None

    if last_exchange and 1 <= len(words) <= 4:
        has_subject = any(s in q_lower for s in _SUBJECT_INDICATORS)
        has_verb    = any(v in q_lower for v in ["est","sont","a","ont","combien","quels","quel","?"])
        if not has_subject and not has_verb:
            prev_q = last_exchange.get("user", "").strip()
            if prev_q and prev_q.lower() not in q_lower:
                q = f"{prev_q} -- {q}"
                q_lower = q.lower()
                words   = q.split()

    if any(fw in q_lower for fw in _FOLLOWUP_LEAVE) and len(words) <= 4:
        for kw, expanded in _FOLLOWUP_EXPAND.items():
            if kw in q_lower:
                return expanded, None
        return "Quels employes sont en conge en ce moment ? [active_today=true]", None

    _leave_ctx = any(w in q_lower for w in ["conge", "absent", "absence", "leave"])
    if (any(nw in q_lower for nw in _NOW_WORDS) or (any(nw in q_lower for nw in _NOW_WORDS_LEAVE_ONLY) and _leave_ctx)) and "[active_today" not in q:
        q += " [active_today=true]"
        q_lower = q.lower()

    VERB_IND = ["est","sont","a","ont","quels","quel","combien","donne","montre","liste","quelles","comment","?"]
    if 1 <= len(words) <= 4 and not any(v in q_lower for v in VERB_IND):
        emp_id, full_name = resolve_employee_name(q)
        if emp_id == "AMBIGUOUS":
            return f"Plusieurs employes correspondent a '{q}' : {full_name}. Precisez le nom complet.", None
        if emp_id:
            return (f"Donne-moi le profil complet de {full_name} (employee_id={emp_id}) : "
                    f"ses conges, ses taches en cours et ses informations generales."), emp_id

    resolved_id = resolved_name = None
    for n in [3, 2]:
        for i in range(len(words) - n + 1):
            candidate = " ".join(words[i:i+n])
            if len(candidate) < 4 or not any(w[0].isupper() for w in candidate.split() if w):
                continue
            emp_id, full_name = resolve_employee_name(candidate)
            if emp_id and emp_id != "AMBIGUOUS":
                resolved_id, resolved_name = emp_id, full_name
                break
        if resolved_id:
            break

    if not resolved_id:
        return q, None
    return f"{q} [employee_id={resolved_id}, nom={resolved_name}]", resolved_id


# ═══════════════════════════════════════════════════════════════════════════════
# LLM REFUSAL DETECTION (v28)
# ═══════════════════════════════════════════════════════════════════════════════
_REFUSAL_PHRASES = (
    "je suis incapable", "je ne peux pas", "je n'ai pas acces",
    "il m'est impossible", "je ne suis pas en mesure",
    "donnees non disponibles", "je n'ai aucune information",
    "impossible de recuperer", "je ne dispose pas",
    "cette information n'est pas disponible",
)

def _is_llm_refusal(answer: str, live_context: str) -> bool:
    return (any(p in answer.lower() for p in _REFUSAL_PHRASES)
            and "===" not in answer
            and "===" in live_context
            and "Resultats (" in live_context)


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICAL SUMMARY GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════
def _generate_summary(question: str, live_context: str, q_lower: str, token: str = "") -> str:
    """
    Generates a short 1-2 sentence summary before the data blocks.
    Only for analytical/listing questions — not for profile or bilan queries.
    """
    # For profile queries — generate a short contextual intro
    if "=== PROFIL EMPLOYE ===" in live_context:
        # Count tasks if present
        task_match = _re.search(r"=== TASKS ===\nResultats \((\d+)\)", live_context)
        leave_match = _re.search(r"=== LEAVE-REQUESTS ===\nResultats \((\d+)\)", live_context)
        name_match = _re.search(r"Nom\s+:\s+(.+)", live_context)
        role_match = _re.search(r"Role ERP\s+:\s+(.+)", live_context)
        name = name_match.group(1).strip() if name_match else "cet employé"
        role = role_match.group(1).strip() if role_match else ""
        role_label = {"manager": "Manager", "ceo": "CEO", "rh": "RH", "employee": "Employé"}.get(role, role)
        parts = [f"Voici le profil complet de **{name}** ({role_label})."]
        if task_match:
            n = int(task_match.group(1))
            if role == "manager":
                parts.append(f"**{n} tâche{'s' if n>1 else ''}** en cours dans son équipe.")
            else:
                parts.append(f"**{n} tâche{'s' if n>1 else ''}** assignée{'s' if n>1 else ''}.")
        if leave_match:
            n = int(leave_match.group(1))
            parts.append(f"**{n} demande{'s' if n>1 else ''} de congé** enregistrée{'s' if n>1 else ''}.")
        return " ".join(parts)

    # Extract count and label from first block
    count_match = _re.search(r"Resultats \((\d+)\)", live_context)
    count = int(count_match.group(1)) if count_match else None

    # Don't add summary for bilan or zero results
    if count is None:
        return ""
    if count == 0:
        return ""

    label_match = _re.search(r"=== ([^=\n]+) ===", live_context)
    label = label_match.group(1).strip() if label_match else ""

    # ── KPIs (delayed projects) ───────────────────────────────────────────────
    if "KPIS" in label:
        if "retard" in q_lower or "delayed" in q_lower:
            # If cross-query (incidents in question), don't use this path — handled above
            if "incident" in q_lower or "croise" in label.lower():
                pass  # handled by croise block above
            else:
                # Find most delayed project
                delays = _re.findall(r"Retard: (\d+)j", live_context)
                max_delay = max(int(d) for d in delays) if delays else 0
                name_match = _re.search(r"- ([^|]+) \| Retard: " + str(max_delay), live_context)
                top_name = name_match.group(1).strip() if name_match else ""
                msg = f"**{count} projet{'s' if count > 1 else ''} en retard** sur l'ensemble du portefeuille."
                if top_name and max_delay:
                    msg += f" Le plus critique : **{top_name}** avec **{max_delay} jours** de retard."
                    msg += f"\n\n💡 **Suggestion proactive :** Il serait judicieux de planifier d'urgence une réunion avec le chef de projet de **{top_name}** pour analyser les blocages et redresser la situation."
                return msg
        if "croise" in label.lower() or "incidents" in q_lower:
            # Determine severity filter from question
            if "critical" in q_lower and "high" in q_lower:
                sev_label = "Critical ou High"
            elif "critical" in q_lower or "critique" in q_lower:
                sev_label = "Critical"
            elif "high" in q_lower or "élevé" in q_lower or "eleve" in q_lower:
                sev_label = "High"
            else:
                sev_label = "actifs"
            msg = (f"**{count} projet{'s' if count > 1 else ''}** {'sont' if count > 1 else 'est'} "
                   f"à la fois **en retard** et affecté{'s' if count > 1 else ''} par des **incidents {sev_label}**. "
                   f"{'Ces projets présentent' if count > 1 else 'Ce projet présente'} un niveau de risque élevé nécessitant une attention immédiate.")
            return msg
        return f"**{count} projet{'s' if count > 1 else ''}** correspondent à votre recherche KPI."

    # ── Tasks ─────────────────────────────────────────────────────────────────
    if "TASKS" in label and "BY-MANAGER" not in label:
        blocked = live_context.count("Statut: Blocked")
        todo    = live_context.count("Statut: Todo")
        inprog  = live_context.count("Statut: In Progress")
        if "bloqué" in q_lower or "bloque" in q_lower:
            msg = f"**{count} tâche{'s' if count > 1 else ''} bloquée{'s' if count > 1 else ''}** détectée{'s' if count > 1 else ''} — chacune nécessite une action immédiate."
        elif "critique" in q_lower or "critical" in q_lower:
            msg = f"**{count} tâche{'s' if count > 1 else ''} critique{'s' if count > 1 else ''} non terminée{'s' if count > 1 else ''}**."
            if blocked:
                msg += f" Dont **{blocked} bloquée{'s' if blocked > 1 else ''}** nécessitant une intervention urgente."
        else:
            msg = f"**{count} tâche{'s' if count > 1 else ''}** correspondent à votre recherche."
            
        # Smart prioritization for daily briefing / "what to start with"
        if any(w in q_lower for w in ["commencer", "priorit", "briefing", "que dois", "urgent"]) and token:
            import re as re2
            all_tasks = re2.findall(r"- (T\d+):\s*(.*?)\s*\|\s*Statut:\s*([^|]+?)\s*\|\s*Priorite:\s*([^|]+?)\s*\|.*?Projet:\s*(P\d+)", live_context)
            
            if all_tasks:
                try:
                    kpis = call_api("/kpis", {}, token)
                    delayed_pids = {r.get("project_id", "") for r in kpis if (r.get("schedule_variance_days") or 0) > 0}
                    high_risk_pids = {r.get("project_id", "") for r in kpis if r.get("risk_level") in ("High", "Critical")}
                    priority_pids = delayed_pids | high_risk_pids

                    best_task = None
                    best_score = -1

                    for tid, title, status, priority, pid in all_tasks:
                        status = status.strip()
                        priority = priority.strip()
                        
                        score = 0
                        if status == "Blocked": score += 100
                        elif status == "In Progress": score += 10
                        elif status == "Todo": score += 5
                        elif status == "Done": continue
                        
                        if priority == "Critical": score += 50
                        elif priority == "High": score += 30
                        elif priority == "Medium": score += 10
                        
                        if pid in priority_pids: score += 200
                        
                        if score > best_score:
                            best_score = score
                            best_task = (tid, title.strip(), pid, status, pid in priority_pids)
                            
                    if best_task:
                        tid, title, pid, status, is_priority_proj = best_task
                        
                        if status == "Blocked":
                            if is_priority_proj:
                                msg += f"\n\n💡 **Suggestion proactive :** Je vous conseille de commencer par débloquer la tâche **{tid}** ({title}) sur le projet **{pid}**. Ce projet est actuellement en retard ou à risque, cette tâche est donc doublement critique."
                            else:
                                msg += f"\n\n💡 **Suggestion proactive :** Vous devriez commencer par débloquer la tâche **{tid}** ({title}) pour permettre à l'équipe d'avancer."
                        else:
                            if is_priority_proj:
                                msg += f"\n\n💡 **Suggestion proactive :** Je vous recommande de traiter en priorité la tâche **{tid}** ({title}). Le projet **{pid}** est actuellement en retard ou à risque d'après les KPIs."
                            else:
                                msg += f"\n\n💡 **Suggestion proactive :** Vous pouvez commencer par la tâche **{tid}** ({title}) qui est la plus prioritaire parmi vos tâches."
                except Exception:
                    pass

        # Smart reassignment tool logic if there are blocked tasks
        elif blocked > 0 and token:
            try:
                # Find assignees from the live_context block
                assignees = _re.findall(r"Assigne a: ([^|]+) \|", live_context)
                assignées_cleansed = [a.strip() for a in set(assignees) if a.strip()]
                
                if assignées_cleansed:
                    # Check leaves for these assignees
                    leaves = call_api("/leave-requests", {"status": "Approved", "active_today": True}, token)
                    emps_on_leave = [r.get("employee_name", "").strip() for r in leaves if isinstance(r, dict)]
                    
                    # Intersect to find blocked tasks' assignees on leave
                    blocked_on_leave = [a for a in assignées_cleansed if any(a in name for name in emps_on_leave)]
                    
                    if blocked_on_leave:
                        msg += f"\n\n💡 **Suggestion proactive :** L'employé **{blocked_on_leave[0]}** a des tâches bloquées ALORS QU'IL EST ACTUELLEMENT EN CONGÉ. Il est fortement recommandé de réassigner ses tâches bloquées à un autre collaborateur disponible."
                    elif len(assignées_cleansed) == 1 and blocked > 2:
                        msg += f"\n\n💡 **Suggestion proactive :** L'employé **{assignées_cleansed[0]}** semble surchargé avec {blocked} tâches bloquées simultanément. Envisagez de réassigner certaines tâches à un collaborateur moins saturé."
            except Exception as e:
                pass
                
        return msg

    # ── Tasks by manager ──────────────────────────────────────────────────────
    if "TASKS-BY-MANAGER" in label or "MANAGERS" in label:
        # Cross-query: managers with blocked tasks AND delayed projects
        if "retard" in q_lower or "bloqu" in q_lower:
            blocks_found = _re.findall(r"- ([^(]+) \([^)]+\) \| Total: \d+ \| Bloques: (\d+)", live_context)
            if blocks_found and ("retard" in live_context or "Projets en retard" in live_context):
                top = max(blocks_found, key=lambda x: int(x[1]))
                return (f"**{count} manager{'s' if count > 1 else ''}** {'cumulent' if count > 1 else 'cumule'} "
                        f"des tâches bloquées ET des projets en retard. "
                        f"**{top[0].strip()}** est le plus impacté avec **{top[1]} tâches bloquées**.")
            if blocks_found:
                top = max(blocks_found, key=lambda x: int(x[1]))
                return f"**{top[0].strip()}** a le plus de tâches bloquées : **{top[1]}**."
        return f"Répartition des tâches pour **{count} manager{'s' if count > 1 else ''}**."

    # ── Employees ─────────────────────────────────────────────────────────────
    if "EMPLOYEES" in label and "BY-MANAGER" not in label:
        if "critique" in label.lower() or "conge" in label.lower():
            # Cross-query result
            return (f"**{count} employé{'s' if count > 1 else ''}** {'ont' if count > 1 else 'a'} simultanément "
                    f"des tâches critiques assignées ET {'sont' if count > 1 else 'est'} en congé approuvé. "
                    f"Attention : {'ces absences impactent' if count > 1 else 'cette absence impacte'} des tâches critiques.")
        if "conge" in q_lower or "congé" in q_lower or "absent" in q_lower:
            return f"**{count} employé{'s' if count > 1 else ''} en congé** en ce moment."
        if "equipe" in q_lower or "équipe" in q_lower:
            return f"Votre équipe compte **{count} membre{'s' if count > 1 else ''}**."
        return f"**{count} employé{'s' if count > 1 else ''}** trouvé{'s' if count > 1 else ''} dans le système."

    # ── Leave requests ────────────────────────────────────────────────────────
    if "LEAVE-REQUESTS" in label:
        pending  = live_context.count("Statut: Pending")
        approved = live_context.count("Statut: Approved")
        
        # Overlap and deadline check for a pending leave request (HR Assistant Tool)
        if token and pending > 0 and any(w in q_lower for w in ["attente", "pending", "analys", "que pense", "approuv"]):
            try:
                pending_matches = _re.findall(r"- ([^|]+) \| Type: ([^|]+) \| Du: ([^ ]+) au ([^ ]+) \| Jours: (\d+) \| Statut: Pending", live_context)
                if pending_matches and len(pending_matches) == 1:
                    emp_name, l_type, d_start, d_end, days = pending_matches[0]
                    emp_name = emp_name.strip()
                    
                    all_emps = call_api("/employees", {}, token)
                    emp = next((e for e in all_emps if f"{e.get('first_name','')} {e.get('last_name','')}".strip() == emp_name), None)
                    if emp:
                        eid = emp.get("employee_id")
                        tasks = call_api("/tasks", {"assigned_to": eid}, token)
                        critical_tasks = [t for t in tasks if t.get("status") not in ("Done", "Completed") and t.get("due_date", "9999") <= d_end and t.get("priority") in ("Critical", "High")]
                        
                        warning = ""
                        if critical_tasks:
                            warning += f"⚠️ **Tâches critiques :** {len(critical_tasks)} tâche(s) importante(s) arrive(nt) à échéance pendant ou avant ce congé (ex: {critical_tasks[0].get('title', '?')}).\n"
                            
                        team = [e.get("employee_id") for e in all_emps if e.get("department") == emp.get("department") and e.get("employee_id") != eid]
                        if team:
                            all_leaves = call_api("/leave-requests", {"status": "Approved"}, token)
                            overlaps = [r for r in all_leaves if str(r.get("employee_id")) in team and not (str(r.get("end_date","")) < d_start or str(r.get("start_date","9999")) > d_end)]
                            if overlaps:
                                warning += f"⚠️ **Effectifs :** {len(overlaps)} autre(s) membre(s) du département {emp.get('department')} {'sont' if len(overlaps)>1 else 'est'} déjà en congé sur cette même période."
                                
                        if warning:
                            analysis = f"**Analyse de la demande (HR Tool) :**\n{warning}\n💡 **Recommandation :** Il est conseillé de vérifier avec le manager avant d'approuver ou de demander une délégation des tâches urgentes."
                        else:
                            analysis = f"**Analyse de la demande (HR Tool) :**\n✅ Aucun conflit de planning détecté. Le département est couvert et aucune tâche critique n'est menacée."
                            
                        return analysis + "\n\n" + f"**{count} demande(s) en attente.**"
            except Exception:
                pass

        if "attente" in q_lower or "pending" in q_lower:
            return f"**{count} demande{'s' if count > 1 else ''} de congé en attente** d'approbation."
        if "ce moment" in q_lower or "active_today" in q_lower:
            return f"**{count} employé{'s' if count > 1 else ''}** actuellement en congé aujourd'hui."
        if pending and approved:
            return f"**{count} demande{'s' if count > 1 else ''} de congé** : {approved} approuvée{'s' if approved > 1 else ''}, {pending} en attente."
        return f"**{count} demande{'s' if count > 1 else ''} de congé** trouvée{'s' if count > 1 else ''}."

    # ── Issues ────────────────────────────────────────────────────────────────
    if "ISSUES" in label:
        critical = live_context.count("Severite: Critical")
        high     = live_context.count("Severite: High")
        if critical:
            return f"**{count} incident{'s' if count > 1 else ''}** dont **{critical} critique{'s' if critical > 1 else ''}** nécessitant une attention immédiate."
        return f"**{count} incident{'s' if count > 1 else ''}** actif{'s' if count > 1 else ''} détecté{'s' if count > 1 else ''}."

    # ── Projects ──────────────────────────────────────────────────────────────
    if "PROJECTS" in label or "CLIENTS" in label:
        label_word = "client" if "CLIENTS" in label else "projet"
        # If question asks for average advancement, compute it from the block
        if any(w in q_lower for w in ["avancement moyen", "moyenne", "avg", "moyen"]):
            pcts = _re.findall(r"Avancement: (\d+)%", live_context)
            if pcts:
                avg = round(sum(int(p) for p in pcts) / len(pcts), 1)
                return (f"**{count} projet{'s' if count > 1 else ''}** en cours — "
                        f"avancement moyen : **{avg}%**")
        return f"**{count} {label_word}{'s' if count > 1 else ''}** trouvé{'s' if count > 1 else ''}."

    # ── Equipment ─────────────────────────────────────────────────────────────
    if "EQUIPMENT" in label:
        return f"**{count} équipement{'s' if count > 1 else ''}** correspondent à votre recherche."

    # ── Stats ─────────────────────────────────────────────────────────────────
    if "STATS-SUMMARY" in label:
        # Extract key numbers from stats block
        proj_match   = _re.search(r"Projets total: (\d+)", live_context)
        avg_match    = _re.search(r"Avancement moy: ([\d.]+)%", live_context)
        budget_match = _re.search(r"Budget: ([\d.]+)", live_context)
        n_proj = proj_match.group(1) if proj_match else "?"
        avg    = avg_match.group(1) if avg_match else "?"
        # Count delayed from KPIs block if present
        delayed_count = len(_re.findall(r"Retard: [1-9]\d*j", live_context))
        msg = f"Portefeuille de **{n_proj} projets** — avancement moyen **{avg}%**."
        if delayed_count:
            msg += f" **{delayed_count} projets en retard** détectés."
        return msg
    if "STATS" in label:
        return ""  # Stats blocks are self-explanatory, no summary needed

    return ""



# ═══════════════════════════════════════════════════════════════════════════════
# #H7 — NUMERIC KPI FILTER
# Handles: CPI<1, SPI<0.9, budget>5%, retard>15j
# ═══════════════════════════════════════════════════════════════════════════════
_NUMERIC_KPI_PATTERNS = [
    r"cpi (inf[eé]rieur|inf|<|moins|en dessous).{0,10}[01]\.[0-9]",
    r"spi (inf[eé]rieur|inf|<|moins|en dessous).{0,10}[01]\.[0-9]",
    r"budget.{0,15}(d[eé]pass|sup[eé]rieur|>|plus de).{0,10}\d+\s*%",
    r"retard.{0,15}(sup[eé]rieur|plus de|>|d[eé]pass).{0,10}\d+\s*j",
    r"(d[eé]pass|sup[eé]rieur).{0,10}budget",
    r"combien de projets.{0,20}(budget|cpi|spi|retard)",
]
_re_numeric_kpi = _re.compile("|".join(_NUMERIC_KPI_PATTERNS), _re.IGNORECASE)

def _is_numeric_kpi_question(q: str) -> bool:
    return bool(_re_numeric_kpi.search(q))

def _handle_numeric_kpi(q_lower: str, token: str, user_id: str) -> str:
    # API now returns only the latest KPI per project — no dedup needed here
    kpis = call_api("/kpis", {}, token)
    if not isinstance(kpis, list) or not kpis:
        return "Impossible de récupérer les KPIs pour le moment."

    # Extract numeric threshold from question
    import re as re2
    threshold_match = re2.search(r"([01]\.[0-9]+|\d+)\s*(%|j|jours)?", q_lower)
    threshold = float(threshold_match.group(1)) if threshold_match else None
    unit = threshold_match.group(2) if threshold_match else ""

    results = []

    # Extract all numbers from question for multi-threshold support
    all_numbers = re2.findall(r"(\d+(?:\.\d+)?)\s*(%|j|jours)?", q_lower)

    # ── COMBINED CPI < X AND Retard > Y — must come FIRST ───────────────────
    if "cpi" in q_lower and any(w in q_lower for w in ["retard", "delai", "jours"]):
        cpi_th    = 1.0
        delay_th  = 15
        # Find CPI threshold (decimal like 0.9 or just 1)
        cpi_match = re2.search(r"cpi\s*[<>]?\s*([0-9]+(?:\.[0-9]+)?)", q_lower)
        if cpi_match: cpi_th = float(cpi_match.group(1))
        # Find delay threshold — look for number followed by j/jours to avoid partial matches
        delay_match = re2.search(r"(?:retard|delai)\D{0,25}(\d+)\s*(?:j|jours)", q_lower)
        if not delay_match:
            delay_match = re2.search(r"(?:retard|delai).{0,25}?(\d+)\s*(?:j|jours|$)", q_lower)
        if delay_match: delay_th = int(delay_match.group(1))
        results = [r for r in kpis
                   if r.get("cost_performance_index") and
                   float(r.get("cost_performance_index", 1)) < cpi_th
                   and int(r.get("schedule_variance_days", 0)) > delay_th]
        label = f"CPI < {cpi_th} ET Retard > {delay_th}j"

    # ── COMBINED SPI < X AND Retard > Y ─────────────────────────────────────
    elif "spi" in q_lower and any(w in q_lower for w in ["retard", "delai", "jours"]):
        spi_th    = 0.9
        delay_th  = 0
        # Match number right after the < or spi keyword — must include full decimal like 1.0
        spi_match = re2.search(r"spi\s*[<>]?\s*([0-9]+(?:\.[0-9]+)?)", q_lower)
        if spi_match: spi_th = float(spi_match.group(1))
        delay_match = re2.search(r"(?:retard|delai)\D{0,25}(\d+)\s*(?:j|jours|$)", q_lower)
        if not delay_match:
            delay_match = re2.search(r"(?:retard|delai).{0,25}?(\d+)\s*(?:j|jours|$)", q_lower)
        if delay_match: delay_th = int(delay_match.group(1))
        if delay_th > 0:
            results = [r for r in kpis
                       if r.get("schedule_performance_index") and
                       float(r.get("schedule_performance_index", 1)) < spi_th
                       and int(r.get("schedule_variance_days", 0)) > delay_th]
            label = f"SPI < {spi_th} ET Retard > {delay_th}j"
        else:
            results = [r for r in kpis if r.get("schedule_performance_index") and
                       float(r.get("schedule_performance_index", 1)) < spi_th]
            label = f"SPI < {spi_th}"

    # ── Single CPI filter ────────────────────────────────────────────────────
    elif "cpi" in q_lower:
        op = threshold if threshold else 1.0
        results = [r for r in kpis if r.get("cost_performance_index") and
                   float(r.get("cost_performance_index", 1)) < op]
        label = f"CPI < {op}"

    # ── Single SPI filter ────────────────────────────────────────────────────
    elif "spi" in q_lower:
        op = threshold if threshold else 0.9
        results = [r for r in kpis if r.get("schedule_performance_index") and
                   float(r.get("schedule_performance_index", 1)) < op]
        label = f"SPI < {op}"

    # Budget filter
    elif "budget" in q_lower and threshold:
        results = [r for r in kpis if r.get("budget_variance_percentage") and
                   float(r.get("budget_variance_percentage", 0)) > threshold]
        label = f"Budget Δ > {threshold}%"

    # Retard filter
    elif ("retard" in q_lower or "délai" in q_lower) and threshold:
        results = [r for r in kpis if r.get("schedule_variance_days") and
                   int(r.get("schedule_variance_days", 0)) > threshold]
        label = f"Retard > {int(threshold)}j"

    # Combined CPI<1 AND retard>X — must be checked BEFORE single CPI check
    elif "cpi" in q_lower and ("retard" in q_lower or "delai" in q_lower):
        delay_th = threshold if (threshold and unit in ("j","jours","")) else 15
        dm = re2.search(r"(?:retard|delai).{0,15}(\d+)", q_lower)
        if dm: delay_th = int(dm.group(1))
        results = [r for r in kpis
                   if float(r.get("cost_performance_index", 1)) < 1.0
                   and int(r.get("schedule_variance_days", 0)) > delay_th]
        label = f"CPI < 1.0 ET Retard > {delay_th}j"
    else:
        results = [r for r in kpis if float(r.get("cost_performance_index", 1)) < 1.0]
        label = "CPI < 1.0"

    results.sort(key=lambda r: float(r.get("cost_performance_index", 1)))
    count = len(results)

    if count == 0:
        # Generate an informative "good news" message
        if "SPI" in label:
            threshold_val = label.split("<")[1].strip() if "<" in label else "0.9"
            return (f"✅ Aucun projet n'a actuellement un SPI inférieur à {threshold_val}. "
                    f"Cela signifie qu'aucun projet n'est fortement en retard par rapport au planning prévu.")
        elif "CPI" in label and "Retard" not in label:
            threshold_val = label.split("<")[1].strip() if "<" in label else "1.0"
            return (f"✅ Aucun projet n'a actuellement un CPI inférieur à {threshold_val}. "
                    f"Tous les projets respectent leur budget prévu.")
        elif "Budget" in label:
            return (f"✅ Aucun projet ne dépasse le seuil budgétaire défini ({label}). "
                    f"Le portefeuille est globalement sous contrôle financier.")
        else:
            return f"✅ Aucun projet ne correspond au critère **{label}** — situation favorable."

    lines = [
        f"- {r.get('project_name', r.get('project_id',''))} | "
        f"Retard: {r.get('schedule_variance_days','')}j | "
        f"Budget: {r.get('budget_variance_percentage','')}% | "
        f"CPI: {r.get('cost_performance_index','')} | "
        f"SPI: {r.get('schedule_performance_index','')} | "
        f"Risque: {r.get('risk_level','')}"
        for r in results
    ]
    block = f"=== KPIS ===\nResultats ({count}):\n" + "\n".join(lines)
    summary = f"**{count} projet{'s' if count>1 else ''}** correspondent au critère **{label}**."
    return summary + "\n\n" + block


# ═══════════════════════════════════════════════════════════════════════════════
# #H8 — HYBRID POLICY + LIVE DATA
# ═══════════════════════════════════════════════════════════════════════════════
_HYBRID_POLICY_PATTERNS = [
    r"puis-?je (poser|prendre|demander).{0,20}cong[eé]",
    r"est.ce que je peux.{0,20}cong[eé]",
    r"(puis-?je|je peux).{0,30}cong[eé]",
    r"epuis[eé].{0,15}solde",
    r"épuis[eé].{0,15}solde",
    r"qui (a|ont).{0,20}(epuis|épuis).{0,15}(cong|solde)",
    r"\d+\s*jours?.{0,20}(maladie|sick).{0,30}(que se passe|que risque|conséquence)",
    r"(que se passe|que risque|conséquence).{0,30}\d+\s*jours?.{0,20}(maladie|sick)",
    r"employ[eé].{0,30}(bloqu|cong[eé]).{0,30}r[eè]glement",
    r"r[eè]glement.{0,30}(bloqu|cong[eé])",
]
_re_hybrid_policy = _re.compile("|".join(_HYBRID_POLICY_PATTERNS), _re.IGNORECASE)

def _is_hybrid_policy_live(q: str) -> bool:
    q_l = strip_accents(q.lower())
    if "[employee_id=" in q:
        return False
    return bool(_re_hybrid_policy.search(q_l))

def _handle_hybrid_policy_live(question: str, q_lower: str, user_id: str,
                                user_role: str, token: str) -> str:
    # Get RAG answer first
    raw_chunks  = doc_retriever.invoke(question)
    proc_chunks = _rerank_doc_chunks(raw_chunks, question, top_k=6)
    doc_ctx = "\n\n".join(
        f"[{ch.metadata.get('category','')} -- {ch.metadata.get('filename','doc')}]\n{ch.page_content}"
        for ch in proc_chunks
    )

    # Case 1: "puis-je poser congé?" — check employee's tasks
    if any(p in q_lower for p in ["puis-je", "je peux", "est-ce que je peux"]) and "cong" in q_lower:
        tasks_data = call_api("/tasks", {"assigned_to": user_id}, token)
        critical_blocked = [t for t in tasks_data
                            if t.get("priority") == "Critical"
                            and t.get("status") in ("Todo","In Progress","Blocked")]
        leave_data  = call_api("/leave-requests", {"employee_id": user_id}, token)
        approved    = [r for r in leave_data if r.get("status","").lower() == "approved"]
        taken       = sum(r.get("total_days",0) or 0 for r in approved)
        remaining   = 35 - taken

        policy_prompt = RAG_DOC_TEMPLATE.format(doc_context=doc_ctx, question=question)
        policy_answer = clean_answer(_call_groq(policy_prompt))

        live_summary = f"\n\n**Votre situation actuelle :**\n"
        live_summary += f"• Solde de congé restant : **{remaining}j** (sur 35j)\n"
        if critical_blocked:
            live_summary += (f"• ⚠️ Vous avez **{len(critical_blocked)} tâche(s) critique(s)** "
                            f"non terminées : {', '.join(t.get('title','?')[:30] for t in critical_blocked[:3])}\n")
            live_summary += "• Selon le règlement, vous ne pouvez pas partir en congé sans arrangement préalable."
        else:
            live_summary += "• ✅ Aucune tâche critique bloquante — vous pouvez soumettre une demande."

        return policy_answer + live_summary

    # Case 2: "quels employés ont épuisé leur solde?"
    if any(p in q_lower for p in ["epuise", "épuisé", "epuis", "épuis"]) and "solde" in q_lower:
        all_leaves = call_api("/leave-requests", {}, token)
        all_emps   = call_api("/employees", {}, token)
        from collections import defaultdict
        taken_by_emp: dict = defaultdict(int)
        for r in all_leaves:
            if r.get("status","").lower() == "approved" and r.get("leave_type") == "Annual":
                eid = r.get("employee_id","")
                taken_by_emp[eid] += r.get("total_days",0) or 0

        exhausted = [(e, taken_by_emp.get(e["employee_id"],0))
                     for e in all_emps
                     if taken_by_emp.get(e["employee_id"],0) >= 35]
        near      = [(e, taken_by_emp.get(e["employee_id"],0))
                     for e in all_emps
                     if 28 <= taken_by_emp.get(e["employee_id"],0) < 35]

        lines = []
        for emp, taken in sorted(exhausted, key=lambda x: -x[1]):
            name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
            lines.append(f"- {name} | Pris: {taken}j / 35j | **Solde: 0j**")

        if not lines:
            summary = "✅ Aucun employé n'a épuisé son solde de congé annuel."
            if near:
                summary += f"\n\n⚠️ **{len(near)} employé(s) proche(s) de l'épuisement** (≥28j pris) :"
                for emp, taken in near:
                    name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
                    summary += f"\n- {name} : {taken}j pris, {35-taken}j restants"
            return summary

        block = f"=== EMPLOYEES ===\nResultats ({len(exhausted)}):\n" + "\n".join(lines)
        return f"**{len(exhausted)} employé(s)** ont épuisé leur solde annuel (35j).\n\n" + block

    # Case 3: "28 jours maladie + 3 de plus" or "employé bloqué + congé — règlement"
    import re as re2
    days_match = re2.search(r"(\d+)\s*jours?.{0,20}(maladie|sick)", q_lower)
    if days_match:
        days_taken = int(days_match.group(1))
        remaining_sick = 30 - days_taken
        policy_prompt = RAG_DOC_TEMPLATE.format(doc_context=doc_ctx, question=question)
        policy_answer = clean_answer(_call_groq(policy_prompt))
        live_note = (f"\n\n**Calcul basé sur votre politique interne :**\n"
                     f"• Jours maladie déjà pris : **{days_taken}j**\n"
                     f"• Solde restant : **{max(0, remaining_sick)}j**\n")
        if days_taken >= 30:
            live_note += "• ⚠️ **Solde épuisé** — le dossier doit être transmis à la CNSS."
        elif days_taken + 3 > 30:
            over = (days_taken + 3) - 30
            live_note += f"• ⚠️ Prendre 3j de plus dépasserait le solde de **{over}j** — transmission CNSS requise."
        return policy_answer + live_note

    # Generic hybrid: RAG answer enriched with live context
    policy_prompt = RAG_DOC_TEMPLATE.format(doc_context=doc_ctx, question=question)
    return clean_answer(_call_groq(policy_prompt))


# ═══════════════════════════════════════════════════════════════════════════════
# #H9 — CROSS SUPPLIERS + HIGH-RISK KPIs
# ═══════════════════════════════════════════════════════════════════════════════
def _is_cross_suppliers_kpis(q: str) -> bool:
    q_l = strip_accents(q.lower())
    return (any(w in q_l for w in ["fournisseur", "supplier", "fournisseurs"])
            and any(w in q_l for w in ["risque", "risk", "retard", "kpi", "actif"]))

def _handle_cross_suppliers_kpis(token: str) -> str:
    kpis      = call_api("/kpis", {}, token)
    suppliers = call_api("/suppliers", {}, token)
    projects  = call_api("/projects", {}, token)

    # Get high-risk project IDs
    seen: dict = {}
    for r in kpis:
        pid = r.get("project_id","")
        if pid and r.get("risk_level") in ("High","Critical"):
            seen[pid] = r

    high_risk_pids = set(seen.keys())
    logger.info("High-risk projects: %s", high_risk_pids)

    # Find active suppliers (status=Active or Available)
    active_suppliers = [s for s in suppliers
                        if s.get("status","").lower() in ("active","approved","actif","approuvé","approuve")]

    count = len(active_suppliers)
    if not active_suppliers:
        return (f"**{len(high_risk_pids)} projets à risque élevé** identifiés.\n\n"
                "Aucun fournisseur actif trouvé dans la base de données.")

    lines = [
        f"- {s.get('supplier_name','')} | Catégorie: {s.get('category','')} | "
        f"Note: {s.get('rating','')} | Ville: {s.get('city','')}"
        for s in active_suppliers[:15]
    ]
    block = f"=== SUPPLIERS ===\nResultats ({count}):\n" + "\n".join(lines)
    summary = (f"**{len(high_risk_pids)} projets à risque élevé** sont actifs. "
               f"**{count} fournisseur{'s' if count>1 else ''}** sont actuellement actifs dans le système.")
    return summary + "\n\n" + block


# ═══════════════════════════════════════════════════════════════════════════════
# #H10 — PREDICTIVE / RISK ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
_PREDICTIVE_PATTERNS = [
    r"risque.{0,20}(financier|budgetaire|budget)",
    r"risque.{0,20}retard",
    r"tendance.{0,20}(continue|actuelle)",
    r"si.{0,20}tendance",
    r"projets?.{0,20}risqu",
    r"plus grand risque",
    r"risque le plus.{0,10}(eleve|grand|critique|important)",
    r"vont.{0,20}(depasser|exceder|rater)",
    r"probabilite.{0,20}(retard|echec)",
    r"alerte.{0,20}(budget|retard|risque)",
    r"prevision.{0,20}(retard|budget|cout)",
]
_re_predictive = _re.compile("|".join(_PREDICTIVE_PATTERNS), _re.IGNORECASE)

def _is_predictive_question(q: str) -> bool:
    return bool(_re_predictive.search(strip_accents(q.lower())))

def _handle_predictive(q_lower: str, token: str, user_id: str) -> str:
    kpis   = call_api("/kpis", {}, token)
    tasks  = call_api("/tasks", {}, token)

    if not isinstance(kpis, list):
        return "Impossible de récupérer les données KPI."

    # API already returns the latest KPI per project — no dedup needed

    # ── Financial risk: CPI trending below 1 AND budget already exceeded ────
    if any(w in q_lower for w in ["financier", "budget", "cout", "coût"]):
        at_risk = []
        for r in kpis:
            cpi    = float(r.get("cost_performance_index", 1) or 1)
            budget = float(r.get("budget_variance_percentage", 0) or 0)
            spi    = float(r.get("schedule_performance_index", 1) or 1)
            risk   = r.get("risk_level", "Low")

            # Score: lower CPI + positive budget variance + low SPI = higher financial risk
            if cpi < 1.0 and budget > 0:
                score = round((1 - cpi) * 100 + budget, 1)
                at_risk.append({**r, "_risk_score": score})

        at_risk.sort(key=lambda x: -x["_risk_score"])

        if not at_risk:
            return ("✅ Aucun projet ne présente de risque financier majeur actuellement. "
                    "Tous les projets ont un CPI ≥ 1.0 ou un budget sous contrôle.")

        top8 = at_risk[:8]
        lines = [
            f"- {r.get('project_name', r.get('project_id',''))} | "
            f"Retard: {r.get('schedule_variance_days','')}j | "
            f"Budget: {r.get('budget_variance_percentage','')}% | "
            f"CPI: {r.get('cost_performance_index','')} | "
            f"SPI: {r.get('schedule_performance_index','')} | "
            f"Risque: {r.get('risk_level','')}"
            for r in top8
        ]
        block = f"=== KPIS ===\nResultats ({len(top8)}):\n" + "\n".join(lines)
        summary = (f"**{len(at_risk)} projet{'s' if len(at_risk)>1 else ''}** "
                   f"présentent un risque financier élevé — CPI sous 1.0 avec dépassement budgétaire actif. "
                   f"**{at_risk[0].get('project_name','')}** est le plus exposé "
                   f"(score de risque : {at_risk[0]['_risk_score']}).")
        return summary + "\n\n" + block

    # ── Schedule risk: SPI declining + blocked tasks on project ─────────────
    else:
        # Projects likely to miss deadline: SPI < 1 AND have blocked critical tasks
        blocked_by_project: dict = {}
        for t in tasks:
            if t.get("status") == "Blocked" and t.get("priority") in ("Critical", "High"):
                pid = t.get("project_id", "")
                if pid:
                    blocked_by_project.setdefault(pid, []).append(t)

        at_risk = []
        for r in kpis:
            pid = r.get("project_id", "")
            spi = float(r.get("schedule_performance_index", 1) or 1)
            delay = int(r.get("schedule_variance_days", 0) or 0)
            blocked = blocked_by_project.get(pid, [])

            if spi < 1.0 and (delay > 0 or blocked):
                score = round((1 - spi) * 100 + len(blocked) * 5 + max(0, delay) * 0.5, 1)
                at_risk.append({**r, "_blocked_count": len(blocked), "_risk_score": score})

        at_risk.sort(key=lambda x: -x["_risk_score"])

        if not at_risk:
            return ("✅ Aucun projet ne présente de risque de retard critique si la tendance actuelle continue. "
                    "Les SPI sont globalement satisfaisants.")

        top8 = at_risk[:8]
        lines = [
            f"- {r.get('project_name', r.get('project_id',''))} | "
            f"Retard: {r.get('schedule_variance_days','')}j | "
            f"Budget: {r.get('budget_variance_percentage','')}% | "
            f"CPI: {r.get('cost_performance_index','')} | "
            f"SPI: {r.get('schedule_performance_index','')} | "
            f"Risque: {r.get('risk_level','')}"
            for r in top8
        ]
        block = f"=== KPIS ===\nResultats ({len(top8)}):\n" + "\n".join(lines)
        summary = (f"**{len(at_risk)} projet{'s' if len(at_risk)>1 else ''}** risquent de prendre "
                   f"davantage de retard si la tendance actuelle continue. "
                   f"**{at_risk[0].get('project_name','')}** présente le score de risque le plus élevé "
                   f"(SPI {at_risk[0].get('schedule_performance_index','')} + "
                   f"{at_risk[0]['_blocked_count']} tâche(s) bloquée(s)).")
        return summary + "\n\n" + block


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def answer_question(
    question: str,
    user_role: str,
    user_id: str,
    user_name: str,
    token: str = "",
    last_exchange=None,
) -> str:
    global _REQUEST_CACHE
    _REQUEST_CACHE = {}

    if token and not _EMPLOYEE_CACHE:
        load_employee_cache(token)

    if question.strip().lower() in {"fichier", "file", "document", "piece jointe", "attachment"}:
        return ("J'ai bien recu votre fichier. Je ne peux pas lire directement les fichiers joints.\n\n"
                "Copiez-collez le texte du fichier dans le chat si vous souhaitez que je l'analyse.")

    # Step 0 : Preprocess
    question, _resolved_id = preprocess_question(question, last_exchange=last_exchange)
    logger.info("Processed question: %s (resolved_id=%s)", question, _resolved_id)
    q_lower = strip_accents(question.lower())

    # Security: manager accessing unknown employee
    # NOTE: stoplist must include project/KPI-related capitalized words to avoid false positives
    _RBAC_STOPWORDS = {
        "liste","montre","donne","affiche","quels","quelles","quel","quelle",
        "combien","comment","qui","les","des","mes","mon","nos","tout","tous",
        "toutes","avec","pour","dans","sur","par","son","ses","leur","leurs",
        # Project / KPI terms that start with uppercase
        "projets","projet","spi","cpi","kpi","budget","retard","taux","score",
        "risque","incidents","incident","taches","employes","equipe","equipes",
        "fournisseurs","fournisseur","engins","equipements","equipement",
        "centre","pont","parc","hotel","usine","station","complexe","residence",
        "mosque","mosquee","hopital","entrepot","immeuble","ecole",
    }
    if user_role == "manager" and _resolved_id is None:
        _name_words = [w for w in question.split()
                       if len(w) > 2 and w[0].isupper() and w.isalpha()
                       and w.lower() not in _RBAC_STOPWORDS]
        if len(_name_words) >= 2 and any(kw in q_lower for kw in ["conge","tache","profil","absent","jours","heures"])\
                and not any(kw in q_lower for kw in ["spi","cpi","kpi","budget","retard","projet"]):
            return "Acces refuse : cet employe n'appartient pas a votre equipe."

    # Security: employee accessing other employee
    if user_role == "employee":
        if _resolved_id and _resolved_id != user_id:
            return "Accès refusé : vous n'êtes pas autorisé à consulter les informations d'autres employés."
        if _resolved_id is None:
            _name_words = [w for w in question.split()
                           if len(w) > 2 and w[0].isupper() and w.isalpha()
                           and w.lower() not in _RBAC_STOPWORDS]
            if len(_name_words) >= 2 and any(kw in q_lower for kw in ["conge","tache","profil","absent","jours","heures"])\
                    and not any(kw in q_lower for kw in ["spi","cpi","kpi","budget","retard","projet"]):
                return "Accès refusé : vous n'êtes pas autorisé à consulter les informations d'autres employés."

    # #H2 Glossaire — with optional live data enrichment
    if is_definition_question(q_lower):
        defn = handle_definition_question(q_lower)
        if defn:
            # Check if question ALSO asks for live data (hybrid glossaire+live)
            has_live_intent = any(w in q_lower for w in
                ["quels projets", "liste", "montre", "affiche", "inferieur", "supérieur",
                 "inf", "<", ">", "moins de", "plus de", "projets ont"])
            if has_live_intent and _is_numeric_kpi_question(q_lower):
                kpi_answer = _handle_numeric_kpi(q_lower, token, user_id)
                return defn + "\n\n---\n\n" + kpi_answer
            return defn
        else:
            # Terme non dans le dict hardcodé → RAG fallback
            logger.info("PATH: #H2 definition → RAG fallback")
            _stop = {"c", "est", "quoi", "qu", "que", "ce", "cest", "quest",
                     "definition", "explique", "signifie", "veut", "dire"}
            _kw = [w for w in _re.findall(r"[a-z\u00e0-\u00ff]+", q_lower)
                   if w not in _stop and len(w) > 2]
            # Fetch ALL glossaire chunks directly (no semantic filter)
            _raw = vector_store.get(
                where={"category": "glossaire"},
                include=["documents", "metadatas"]
            )
            from langchain_core.documents import Document as _Doc
            all_glossaire = [
                _Doc(page_content=d, metadata=m)
                for d, m in zip(_raw.get("documents", []), _raw.get("metadatas", []))
            ]
            # Score by keyword match
            all_glossaire.sort(
                key=lambda c: sum(1 for kw in _kw if kw in c.page_content.lower()),
                reverse=True
            )
            proc_chunks = all_glossaire[:6]
            logger.info("H2 glossaire chunks: %d, top: %r",
                        len(all_glossaire), proc_chunks[0].page_content[:60] if proc_chunks else "")
            doc_ctx = "\n\n".join(c.page_content for c in proc_chunks)
            if doc_ctx.strip():
                return clean_answer(_call_groq(RAG_DOC_TEMPLATE.format(
                    doc_context=doc_ctx, question=question)))
            
    # #H6 Leave balance
    if is_leave_balance_question(q_lower):
        logger.info("PATH: #H6 leave balance")
        return _handle_leave_balance(user_id=user_id, token=token, user_name=user_name)

    # ── #H7: Numeric KPI filter (CPI<1 AND retard>X, budget>X%) ─────────────
    if _is_numeric_kpi_question(q_lower):
        logger.info("PATH: #H7 numeric KPI filter")
        return _handle_numeric_kpi(q_lower, token, user_id)

    # ── #H8: Hybrid policy+live (can I take leave? employee exhausted?) ──────
    if _is_hybrid_policy_live(q_lower):
        logger.info("PATH: #H8 hybrid policy+live")
        return _handle_hybrid_policy_live(question, q_lower, user_id, user_role, token)

    # ── #H9: Cross suppliers+kpis ────────────────────────────────────────────
    if _is_cross_suppliers_kpis(q_lower):
        logger.info("PATH: #H9 cross suppliers+kpis")
        return _handle_cross_suppliers_kpis(token)

    # ── #H10: Predictive / risk questions ───────────────────────────────────
    if _is_predictive_question(q_lower):
        logger.info("PATH: #H10 predictive/risk analysis")
        return _handle_predictive(q_lower, token, user_id)

    # ── #H11: Meeting notes / CR ─────────────────────────────────────────────
    if is_meeting_question(q_lower):
        logger.info("PATH: #H11 meeting notes → RAG only")
        raw_chunks  = doc_retriever.invoke(question)
        proc_chunks = _rerank_doc_chunks(raw_chunks, question, top_k=6)
        doc_ctx = "\n\n".join(
            f"[{ch.metadata.get('category','')} -- {ch.metadata.get('filename','doc')}]\n{ch.page_content}"
            for ch in proc_chunks
        )
        if not doc_ctx.strip():
            return "Je n'ai pas trouve de notes de reunion sur ce sujet."
        
        # Override the RAG template to be slightly more open for meeting notes
        cr_prompt = f"""Tu es un assistant ERP. Un utilisateur te pose une question sur une reunion.
Reponds en t'appuyant STRICTEMENT sur les notes de secretaire ci-dessous.
Si l'information n'y figure pas, dis-le clairement. Ne cite pas les noms de fichiers.

DOCUMENTS:
{doc_ctx}

Question: {question}
Reponse:"""
        return clean_answer(_call_groq(cr_prompt))

    # #H5 Policy → RAG only
    logger.info("PATH CHECK: is_policy=%s is_procedural=%s is_definition=%s",
                is_policy_question(q_lower), is_procedural_question(q_lower), is_definition_question(q_lower))
    if is_policy_question(q_lower):
        logger.info("PATH: #H5 policy → RAG only")
        return _ask_llm_rag_only(question, user_id=user_id, token=token)

    # #H4 Procedural → RAG only
    if is_procedural_question(q_lower):
        logger.info("PATH: #H4 procedural → RAG only")
        raw_chunks  = doc_retriever.invoke(question)
        proc_chunks = raw_chunks[:6]
        logger.info("H4 RAG: %d chunks retrieved", len(proc_chunks))
        for i, ch in enumerate(proc_chunks):
            logger.info("  chunk[%d]: file=%s | %r", i,
                        ch.metadata.get("filename","?"), ch.page_content[:100])
        doc_ctx = "\n\n".join(
            f"[{ch.metadata.get('category','')} -- {ch.metadata.get('filename','doc')}]\n{ch.page_content}"
            for ch in proc_chunks
        )
        logger.info("H4 doc_ctx: %d chars", len(doc_ctx))
        if not doc_ctx.strip():
            return "Je n'ai pas trouve de documentation sur ce sujet."
        return clean_answer(_call_groq(RAG_DOC_TEMPLATE.format(doc_context=doc_ctx, question=question)))

    # Step 1 : Retrieve
    api_docs      = api_retriever.invoke(question)
    doc_chunks    = doc_retriever.invoke(question)
    role_allowed  = ROLE_ALLOWED_ENDPOINTS.get(user_role, [])
    raw_endpoints = [d.metadata.get("endpoint") for d in api_docs
                     if d.metadata.get("endpoint") and d.metadata["endpoint"] in role_allowed]
    available_endpoints = list(dict.fromkeys(raw_endpoints))
    for ep in role_allowed:
        if ep not in available_endpoints:
            available_endpoints.append(ep)
    logger.info("Available endpoints (role=%s): %s", user_role, available_endpoints)
    logger.info("Doc chunks retrieved: %d", len(doc_chunks))

    # Step 2 : Planner via Groq
    planner_prompt = (PLANNER_TEMPLATE
        .replace("{available_endpoints}", str(available_endpoints))
        .replace("{user_role}", user_role)
        .replace("{user_id}", user_id)
        .replace("{question}", question)
    )
    plan_raw = _call_groq(planner_prompt, json_mode=True)
    logger.info("GROQ RAW PLAN: %s", repr(plan_raw[:500]))
    plan = parse_llm_plan(plan_raw)
    logger.info("Plan: %s", plan.get("endpoints", []))

    if not plan.get("endpoints"):
        fallback = _apply_fallback_plan(q_lower, role_allowed)
        if fallback:
            plan["endpoints"] = fallback

    # ── POST-PLAN FIXES (applied BEFORE deduplication) ──────────────────────

    # Fix 1: replace /projects with /kpis when delayed filter is present
    # Also clean any invalid filters from /kpis (it only supports delayed and risk_level)
    for item in plan.get("endpoints", []):
        if item.get("endpoint") == "/projects" and item.get("filters", {}).get("delayed"):
            item["endpoint"] = "/kpis"
            logger.info("POST-PLAN: /projects delayed → replaced with /kpis")
        if item.get("endpoint") == "/kpis":
            valid = {k: v for k, v in item.get("filters", {}).items()
                     if k in ("delayed", "risk_level")}
            item["filters"] = valid

    # Fix 2: for critical tasks, remove status filter (fetch all, filter later)
    for item in plan.get("endpoints", []):
        if item.get("endpoint") == "/tasks":
            f = item.get("filters", {})
            if f.get("priority") == "Critical" and "status" in f:
                f.pop("status")

    # Fix 3: cross KPI+issues → remove /projects and dedup /issues
    _plan_eps = [i.get('endpoint','') for i in plan.get('endpoints',[])]
    if '/kpis' in _plan_eps and '/issues' in _plan_eps:
        plan['endpoints'] = [i for i in plan['endpoints'] if i.get('endpoint') != '/projects']
        issues_items = [i for i in plan['endpoints'] if i.get('endpoint') == '/issues']
        if len(issues_items) > 1:
            filtered = [i for i in issues_items if i.get('filters',{}).get('severity')]
            keep = filtered if filtered else issues_items[:1]
            plan['endpoints'] = [i for i in plan['endpoints'] if i.get('endpoint') != '/issues'] + keep
        logger.info('POST-PLAN cross KPI+issues: plan cleaned → %s', [i.get('endpoint') for i in plan['endpoints']])

    # ── DEDUPLICATION (after all post-plan fixes) ────────────────────────────
    seen_keys, deduped = set(), []
    for item in plan.get("endpoints", []):
        ep = item.get("endpoint", "")
        if not ep:
            continue
        clean_f = sanitize_filters(item.get("filters", {}))
        item["filters"] = clean_f
        key = (ep, json.dumps(clean_f, sort_keys=True))
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(item)
    plan["endpoints"] = deduped[:6]

    # Post-plan fixes for suppliers (after dedup, these don't affect dedup)
    _TOP_SUPPLIER_KWS = [
        "meilleure note", "meilleures notes", "mieux note", "mieux noté",
        "mieux notés", "top fournisseur", "meilleur fournisseur",
        "meilleurs fournisseurs", "note la plus", "les mieux", "les meilleurs",
    ]
    for item in plan.get("endpoints", []):
        if item.get("endpoint") == "/suppliers":
            if any(kw in q_lower for kw in _TOP_SUPPLIER_KWS):
                item["filters"]["sort_by_rating"] = True
                item["_row_limit"] = 5
                logger.info("POST-PLAN: /suppliers → sort_by_rating=True, row_limit=5")

    # Row limits
    _ANALYTICAL = ["quel","quels","meilleur","pire","top","plus","moins","combien","comparer","retard","bloque","critique","risque"]
    _LISTING    = ["liste","tous","toutes","affiche","montre","donne","complet"]
    is_analytical = any(w in q_lower for w in _ANALYTICAL)
    is_listing    = any(w in q_lower for w in _LISTING)
    n_ep = len(plan["endpoints"])
    BUDGET = 60
    per_ep = max(5, BUDGET // max(n_ep, 1)) if is_analytical else (25 if is_listing and n_ep == 1 else max(8, BUDGET // max(n_ep, 1)))

    _ALWAYS_FULL   = {"/stats/summary", "/stats/tasks", "/stats/by-manager", "/tasks/by-manager", "/notifications"}
    _is_cross = any(w in q_lower for w in ["et ont", "ayant", "avec des incidents", "ont des incidents"])
    for item in plan["endpoints"]:
        ep = item.get("endpoint","")
        if ep not in _ALWAYS_FULL:
            if "_row_limit" not in item:
                item["_row_limit"] = per_ep
        if ep == "/kpis":
            item["_row_limit"] = min(item.get("_row_limit", per_ep), 25 if _is_cross else 15)

    # Manager scope
    _supervised_ids: set | None = None
    if user_role == "manager":
        _supervised_ids = _get_supervised_employees(user_id, token)

    if user_role == "manager" and _resolved_id is None:
        for item in plan.get("endpoints", []):
            f = item.get("filters", {})
            if item.get("endpoint") == "/tasks" and f.get("assigned_to") == user_id:
                f.pop("assigned_to")
            if item.get("endpoint") in ("/leave-requests", "/timesheets", "/employees") and f.get("employee_id") == user_id:
                if not any(w in q_lower for w in ["moi","mes conge","mon conge","ma fiche","mes heures","mon profil"]):
                    f.pop("employee_id")

    if user_role == "manager" and _supervised_ids is not None:
        for item in plan.get("endpoints", []):
            f = item.get("filters", {})
            if "supervised_by" in f:
                f.pop("supervised_by")
                item["_team_filter"] = True

    if any(w in q_lower for w in ["client", "clients", "mes clients"]):
        for item in plan.get("endpoints", []):
            if item.get("endpoint") == "/projects":
                item["filters"]["_client_view"] = True

    # ═══════════════════════════════════════════════════════════════════════════
    # Step 3 : Execute
    # ═══════════════════════════════════════════════════════════════════════════
    live_parts = []
    for item in plan.get("endpoints", []):
        endpoint = item.get("endpoint", "")
        if not endpoint or endpoint not in role_allowed:
            continue

        filters = sanitize_filters(item.get("filters", {}))

        if endpoint in ("/leave-requests", "/tasks", "/timesheets", "/employees"):
            id_key  = "assigned_to" if endpoint == "/tasks" else "employee_id"
            raw_eid = filters.get("employee_id","") or filters.get("assigned_to","")
            if raw_eid and not str(raw_eid).startswith("E"):
                eid, _ = resolve_employee_name(str(raw_eid))
                filters.pop("employee_id", None)
                filters.pop("assigned_to", None)
                if eid and eid != "AMBIGUOUS":
                    filters[id_key] = eid
            elif not raw_eid and _resolved_id:
                filters[id_key] = _resolved_id

        if user_role == "employee":
            id_key     = "assigned_to" if endpoint == "/tasks" else "employee_id"
            queried_id = filters.get(id_key) or filters.get("employee_id") or filters.get("assigned_to")
            if queried_id and queried_id != user_id:
                live_parts.append(f"=== ACCES REFUSE ===\nNon autorise a consulter l'employe {queried_id}.\n")
                continue

        if user_role == "manager" and _supervised_ids is not None:
            id_key     = "assigned_to" if endpoint == "/tasks" else "employee_id"
            queried_id = filters.get(id_key) or filters.get("employee_id") or filters.get("assigned_to")
            if queried_id and queried_id != user_id and queried_id not in _supervised_ids:
                live_parts.append(f"=== ACCES REFUSE ===\nNon autorise a consulter l'employe {queried_id}.\n")
                continue

        active_today   = filters.pop("active_today", False)
        delayed_filter = filters.pop("delayed", None)
        client_view    = filters.pop("_client_view", False)
        sort_by_rating = filters.pop("sort_by_rating", False)
        history_filter = filters.pop("history", False)
        requested_risk = filters.get("risk_level", None)

        # Pass history=true to API when trend/evolution is requested
        if endpoint == "/kpis" and history_filter:
            filters["history"] = True

        data = call_api(endpoint, filters, token)

        if endpoint == "/suppliers" and sort_by_rating and isinstance(data, list):
            data = sorted(data, key=lambda r: r.get("rating", 0) or 0, reverse=True)
            top_n = item.get("_row_limit", 5)
            data  = data[:top_n]
            logger.info("SUPPLIERS: sorted by rating, top %d returned", top_n)

        if item.get("_team_filter") and user_role == "manager" and _supervised_ids is not None:
            team_ids  = _supervised_ids - {user_id}
            id_key_tf = "assigned_to" if endpoint == "/tasks" else "employee_id"
            if isinstance(data, list):
                data = [r for r in data if r.get(id_key_tf, "") in team_ids]

        if endpoint == "/kpis" and isinstance(data, list):
            # API already returns the latest KPI per project — just filter and sort
            if delayed_filter:
                data = [r for r in data if (r.get("schedule_variance_days") or 0) > 0]
            data.sort(key=lambda r: -(r.get("schedule_variance_days") or 0) if (delayed_filter or requested_risk)
                      else -abs(r.get("schedule_variance_days") or 0))

        if active_today and isinstance(data, list):
            today = _date.today().isoformat()
            data  = [r for r in data if r.get("status","").lower() == "approved"
                     and r.get("start_date","") <= today <= r.get("end_date","9999")]

        if endpoint == "/tasks" and "non termin" in q_lower and isinstance(data, list):
            data = [r for r in data if r.get("status", "") != "Done"]

        row_limit = item.get("_row_limit")
        if row_limit and isinstance(data, list):
            data = data[:row_limit]

        _BILAN = ["combien de jours","nombre de jours","total","bilan","a pris","ont pris"]
        if endpoint == "/leave-requests" and _resolved_id and any(w in q_lower for w in _BILAN):
            data = call_api(endpoint, {k: v for k, v in filters.items() if k != "status"}, token)

        if endpoint == "/leave-requests" and _resolved_id and any(w in q_lower for w in _BILAN):
            if isinstance(data, list):
                approved = [r for r in data if r.get("status","").lower() == "approved"]
                pending  = [r for r in data if r.get("status","").lower() == "pending"]
                tot_a    = sum(r.get("total_days",0) or 0 for r in approved)
                tot_p    = sum(r.get("total_days",0) or 0 for r in pending)
                emp_name = data[0].get("employee_name", _resolved_id) if data else _resolved_id
                if not data:
                    live_parts.append(f"=== LEAVE-REQUESTS ===\nResultats (0): Aucun conge pour {emp_name}.\n")
                    continue
                block   = format_endpoint_data("/leave-requests", approved + pending, {})
                summary = f"Bilan {emp_name} : {tot_a}j approuves" + (f" | {tot_p}j en attente" if pending else "")
                live_parts.append(block.replace("=== LEAVE-REQUESTS ===", f"=== LEAVE-REQUESTS ===\n{summary}"))
                continue

        # For profile query: if /tasks returns 0, check if person is a manager
        # and fetch their supervised team's tasks instead
        if not data and _resolved_id and endpoint == "/tasks":
            supervised = _get_supervised_employees(_resolved_id, token)
            if len(supervised) > 1:  # has team members
                all_tasks = call_api("/tasks", {}, token)
                team_ids  = supervised - {_resolved_id}
                team_tasks = [t for t in all_tasks if t.get("assigned_to","") in team_ids]
                if team_tasks:
                    data = team_tasks[:15]
                    logger.info("Manager profile: fetched %d team tasks for %s", len(data), _resolved_id)

        if data:
            if client_view:
                filters["_client_view"] = True
            live_parts.append(format_endpoint_data(endpoint, data, filters))
        else:
            # For profile queries (resolved_id set), skip empty blocks — they add noise
            if _resolved_id:
                logger.info("Skipping empty block for %s (profile query)", endpoint)
                continue
            lbl = endpoint.strip("/").replace("/", "-").upper()
            live_parts.append(f"=== {lbl} ===\nResultats (0): Aucun resultat pour filtres: {filters}\n")

    if any(w in q_lower for w in ["tache", "task"]):
        live_parts = [p for p in live_parts if p.startswith("=== TASKS")] + \
                     [p for p in live_parts if not p.startswith("=== TASKS")]
    live_context = "\n".join(live_parts) if live_parts else "Aucune donnee live -- question documentaire."

    # ── Cross-queries ─────────────────────────────────────────────────────────
    _is_cross_kpi_issue = (
        any(w in q_lower for w in [
            "et ont", "ayant", "avec des incidents", "ont des incidents", "retard et",
            "et ont des", "incidents critical", "incidents critiques", "incidents high",
            "critical ou high", "critiques ou high", "critical ou hauts"
        ])
        and any(w in q_lower for w in ["incident", "issue", "probleme", "problème"])
    ) or (
        "retard" in q_lower
        and any(w in q_lower for w in ["incident", "issue"])
        and any(w in q_lower for w in ["critical", "critique", "high", "elev"])
    )
    if _is_cross_kpi_issue:
        # Remove /projects block — it's noise when doing cross KPI+issues query
        live_parts = [p for p in live_parts if not p.startswith("=== PROJECTS")]
        kpi_raw = _REQUEST_CACHE.get(_cache_key("/kpis", {})) or call_api("/kpis", {}, token)
        kpi_raw = [r for r in kpi_raw if (r.get("schedule_variance_days") or 0) > 0]
        seen_p: dict = {}
        for r in kpi_raw:
            pid = r.get("project_id","")
            if pid not in seen_p or r.get("schedule_variance_days",0) > seen_p[pid].get("schedule_variance_days",0):
                seen_p[pid] = r
        kpi_raw = sorted(seen_p.values(), key=lambda r: -(r.get("schedule_variance_days") or 0))
        iss_filters: dict = {}
        if any(w in q_lower for w in ["critical", "critique", "critiques"]) and not any(w in q_lower for w in ["high", "elev"]):
            iss_filters["severity"] = "Critical"
        elif any(w in q_lower for w in ["high", "elev"]) and not any(w in q_lower for w in ["critical", "critique"]):
            iss_filters["severity"] = "High"
        _iss_ck = _cache_key("/issues", iss_filters)
        if _iss_ck in _REQUEST_CACHE:
            iss_raw = _REQUEST_CACHE[_iss_ck]
        else:
            iss_all = _REQUEST_CACHE.get(_cache_key("/issues", {}))
            if iss_all:
                sev = iss_filters.get("severity")
                iss_raw = [r for r in iss_all if r.get("severity") == sev] if sev else iss_all
            else:
                iss_raw = call_api("/issues", iss_filters, token)
        if kpi_raw and iss_raw:
            iss_pids = {r.get("project_id","") for r in iss_raw if r.get("project_id")}
            crossed  = [r for r in kpi_raw if r.get("project_id","") in iss_pids]
            if crossed:
                cb = format_endpoint_data("/kpis", crossed, {}).replace("=== KPIS ===", "=== KPIS (croise avec incidents) ===")
                live_context = "\n".join([p for p in live_parts if not p.startswith("=== KPIS") and not p.startswith("=== ISSUES")] + [cb])

    _is_cross_mgr_delayed = (
        any(w in q_lower for w in [
            "taches bloquees", "tâches bloquées", "bloquees", "bloquées",
            "taches bloqu", "bloqu"
        ])
        and any(w in q_lower for w in [
            "projets en retard", "retard", "delayed"
        ])
        and any(w in q_lower for w in [
            "manager", "managers", "responsable", "chef", "qui"
        ])
    )
    if _is_cross_mgr_delayed:
        all_tasks_mgr = call_api("/tasks", {}, token)
        delayed_pids  = {r.get("project_id","") for r in call_api("/kpis", {}, token)
                         if (r.get("schedule_variance_days") or 0) > 0 and r.get("project_id")}
        mgr_data = _compute_virtual_endpoint("/tasks/by-manager", token)
        all_emps = call_api("/employees", {}, token)
        mgr_map  = {e["employee_id"]: e for e in all_emps if e.get("role") == "manager"}
        emp_mgr: dict = {}
        for mid, mgr in mgr_map.items():
            for eid in [x.strip() for x in (mgr.get("supervised_employees") or "").replace(";",",").split(",") if x.strip()]:
                emp_mgr[eid] = mid
        mgr_delayed: dict = {}
        for t in all_tasks_mgr:
            mid = emp_mgr.get(t.get("assigned_to","")) or (t.get("assigned_to","") if t.get("assigned_to","") in mgr_map else None)
            if mid and t.get("project_id","") in delayed_pids:
                mgr_delayed.setdefault(mid, set()).add(t["project_id"])
        crossed_mgrs = [r for r in (mgr_data if isinstance(mgr_data, list) else [])
                        if r.get("blocked", 0) > 0 and r.get("manager_id","") in mgr_delayed]
        lines_mgr = [
            f"- {r.get('manager_name','')} ({r.get('department','')}) | Total: {r.get('total_tasks',0)} | "
            f"Bloques: {r.get('blocked',0)} | Critiques: {r.get('critical_tasks',0)} | "
            f"Projets en retard: {len(mgr_delayed.get(r.get('manager_id',''),set()))} | Avancement: {r.get('done_pct',0)}%"
            for r in crossed_mgrs
        ]
        live_context = (
            f"=== MANAGERS (bloques + projets en retard) ===\nResultats ({len(crossed_mgrs)}):\n" + "\n".join(lines_mgr)
            if lines_mgr else
            "=== MANAGERS (bloques + projets en retard) ===\nResultats (0): Aucun manager concerne.\n"
        )

    _is_cross_emp_leave = (
        any(w in q_lower for w in [
            "taches critiques", "tâches critiques", "tache critique", "tâche critique",
            "taches critiques assignees", "tâches critiques assignées"
        ])
        and any(w in q_lower for w in [
            "en conge", "en congé", "conge approuve", "congé approuvé",
            "absent", "absence", "sont en conge", "sont en congé"
        ])
    )
    if _is_cross_emp_leave:
        today    = _date.today().isoformat()
        crit_tasks = call_api("/tasks", {"priority": "Critical"}, token)
        crit_ids   = {r.get("assigned_to","") for r in crit_tasks if r.get("assigned_to")}
        all_leaves = call_api("/leave-requests", {"status": "Approved"}, token)
        on_leave   = [r for r in all_leaves if r.get("start_date","") <= today <= r.get("end_date","9999")]
        leave_ids  = {r.get("employee_id","") for r in on_leave if r.get("employee_id")}
        both_ids   = crit_ids & leave_ids
        if both_ids:
            all_emps   = call_api("/employees", {}, token)
            matched    = [e for e in all_emps if e.get("employee_id","") in both_ids]
            lines = []
            for emp in matched:
                eid  = emp.get("employee_id","")
                name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
                emp_tasks   = [t for t in crit_tasks if t.get("assigned_to") == eid]
                task_titles = ", ".join(t.get("title","?") for t in emp_tasks[:3])
                emp_leave   = next((l for l in on_leave if l.get("employee_id") == eid), None)
                leave_info  = (f"{emp_leave.get('leave_type','')} du {emp_leave.get('start_date','')} "
                               f"au {emp_leave.get('end_date','')} ({emp_leave.get('total_days','')}j)") if emp_leave else ""
                lines.append(f"- {name} | Dept: {emp.get('department','')} | Poste: {emp.get('position','')} | "
                             f"Taches critiques: {len(emp_tasks)} ({task_titles}) | Conge: {leave_info}")
            live_context = (f"=== EMPLOYEES (taches critiques + en conge) ===\nResultats ({len(matched)}):\n" + "\n".join(lines)
                            if lines else "=== EMPLOYEES (taches critiques + en conge) ===\nResultats (0): Aucun employe concerne.\n")
        else:
            live_context = "=== EMPLOYEES (taches critiques + en conge) ===\nResultats (0): Aucun employe concerne.\n"

    if "=== ACCES REFUSE ===" in live_context:
        return ("Je n'ai pas pu identifier cet employe avec certitude. Precisez le nom complet."
                if _resolved_id is None else
                "Acces refuse : vous pouvez uniquement acceder aux donnees de votre propre equipe.")

    _DATA_WORDS = ["employe","tache","projet","conge","liste","tous","toutes","affiche","montre","donne",
                   "incident","equipement","fournisseur","kpi","statistique","client","clients"]
    if live_context == "Aucune donnee live -- question documentaire." and any(w in q_lower for w in _DATA_WORDS):
        planned_eps = [item.get("endpoint","") for item in plan.get("endpoints",[])]
        if [ep for ep in planned_eps if ep not in role_allowed]:
            return _ROLE_SCOPE_MSG.get(user_role, "Cette information n'est pas accessible avec votre role.")
        return ("Je suis votre assistant ERP BTP.\n\nCette demande est hors de mon perimetre.\n\n"
                "Je peux vous aider sur : projets, KPIs, employes, taches, conges, incidents, equipements, fournisseurs.")

    # Step 4 : Doc context
    doc_context = "\n\n".join(
        f"[{ch.metadata.get('category','')} -- {ch.metadata.get('filename','doc')}]\n{ch.page_content}"
        for ch in _rerank_doc_chunks(doc_chunks, question, top_k=3)
    ) or "Aucune documentation pertinente."

    # Step 5 : Return live data directly with analytical summary prefix
    _EMPTY = {"aucune donnee disponible.", "aucune donnee disponible pour cette requete.", ""}
    if "=== " in live_context and "Resultats (" in live_context:
        logger.info("Step 5: live data detected → generating summary + blocks")
        blocks = _re.findall(r"=== [^=\n]+ ===\n(?:.*\n)*?Resultats \(\d+\):.*?(?=\n=== |$)", live_context, _re.DOTALL)
        raw_data = "\n\n".join(b.strip() for b in blocks) if blocks else live_context.strip()
        raw_data = _re.sub(r'\[employee_id=E\d+[^\]]*\]', '', raw_data).strip()

        # Generate a short analytical sentence before the data blocks
        summary = _generate_summary(question, live_context, q_lower, token)
        if summary:
            answer = summary + "\n\n" + raw_data
        else:
            answer = raw_data
        return answer

    # Step 5b : LLM answer from doc context
    result = _call_groq(ANSWER_TEMPLATE.format(
        question=question, live_context=live_context,
        doc_context=doc_context, user_role=user_role, user_name=user_name,
    ))
    answer = clean_answer(result)
    answer = _re.sub(r'\[employee_id=E\d+[^\]]*\]', '', answer).strip()

    _live_labels   = set(_re.findall(r"=== ([^=\n]+ ===)", live_context))
    _answer_labels = set(_re.findall(r"=== ([^=\n]+ ===)", answer))
    _hallucinated  = _answer_labels - _live_labels - {"ACCES REFUSE ==="}

    _answer_useless = (
        not answer or answer.strip().lower() in _EMPTY
        or ("aucune" in answer.lower() and "===" not in answer)
        or bool(_hallucinated) or _is_llm_refusal(answer, live_context)
    )

    if _answer_useless and "=== " in live_context and "Resultats (" in live_context:
        blocks = _re.findall(r"=== [^=\n]+ ===\nResultats \(\d+\):.*?(?=\n=== |$)", live_context, _re.DOTALL)
        answer = "\n\n".join(b.strip() for b in blocks) if blocks else live_context.strip()

    if not answer or answer.strip().lower() in _EMPTY:
        answer = ("Je suis votre assistant ERP BTP.\n\nJe n'ai pas pu recuperer cette information.\n\n"
                  "Je peux vous aider sur :\n  - Projets & KPIs\n  - Employes & equipes\n"
                  "  - Taches & incidents\n  - Conges & absences\n  - Equipements & fournisseurs\n  - Procedures internes")

    logger.info("=== RAW ANSWER ===\n%s\n==================", repr(answer))
    return answer
