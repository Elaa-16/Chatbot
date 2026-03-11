"""
Construction ERP RAG Engine v30
================================
Fixes vs v29:
  - Fix 7 (v30): is_policy_question() classifier — intercepts policy/rule questions
                 (congé duration, EPI rules, salary, sanctions, etc.) BEFORE the planner
                 so they never reach /leave-requests or other endpoints.
  - Fix 8 (v30): _ask_llm_rag_only() — dedicated RAG-only LLM call for policy questions,
                 uses rag_doc_chain with reranked doc chunks (same as #H4 procedural path).
  All previous fixes (v28, v29) preserved unchanged.
"""

import logging
import json
import re as _re
import requests
from collections import Counter
from datetime import date as _date

from langchain_ollama import OllamaEmbeddings
from langchain_ollama.llms import OllamaLLM
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE_URL   = "http://localhost:8000"
OLLAMA_TIMEOUT = 60

embeddings    = OllamaEmbeddings(model="mxbai-embed-large")
planner_model = OllamaLLM(model="llama3.1:8b", timeout=OLLAMA_TIMEOUT, format="json")
answer_model  = OllamaLLM(model="llama3.1:8b", timeout=OLLAMA_TIMEOUT)

vector_store = Chroma(
    collection_name="erp_apis",
    embedding_function=embeddings,
    persist_directory=r"C:\Users\msi\Chatbot\erp-backend\rag_engine\erp_chroma_db"
)
api_retriever = vector_store.as_retriever(
    search_kwargs={"k": 14, "filter": {"category": "api"}}
)
doc_retriever = vector_store.as_retriever(
    search_kwargs={"k": 8, "filter": {"category": {
        "$in": ["policy", "procedure", "glossaire", "project_report",
                "kpi_analysis", "employee_guide", "equipment_guide",
                "supplier_info", "internal_communication"]
    }}}
)

# ── Allowed endpoints per role ────────────────────────────────────────────────
ROLE_ALLOWED_ENDPOINTS = {
    "ceo": [
        "/projects", "/kpis", "/tasks", "/tasks/by-manager", "/employees",
        "/leave-requests", "/issues", "/timesheets", "/equipment", "/suppliers",
        "/notifications", "/stats/summary", "/stats/tasks", "/stats/by-manager"
    ],
    "manager": [
        "/projects", "/tasks", "/tasks/by-manager", "/employees",
        "/leave-requests", "/issues", "/timesheets", "/notifications",
        "/stats/tasks", "/kpis"
    ],
    "rh": ["/leave-requests", "/employees", "/notifications"],
    "employee": ["/tasks", "/leave-requests", "/timesheets", "/notifications", "/kpis"],
}

# ═══════════════════════════════════════════════════════════════════════════════
# HTTP API CALLER
# ═══════════════════════════════════════════════════════════════════════════════
_REQUEST_CACHE: dict = {}


def _cache_key(endpoint: str, params: dict) -> tuple:
    clean = {k: v for k, v in params.items()
             if v not in (None, "", False) and k != "active_today"}
    return (endpoint, tuple(sorted(clean.items())))


def call_api(endpoint: str, params: dict, token: str) -> list | dict:
    if endpoint in ("/tasks/by-manager", "/stats/by-manager", "/stats/tasks"):
        return _compute_virtual_endpoint(endpoint, token)

    url     = f"{API_BASE_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {token}"}

    clean_params = {k: v for k, v in params.items()
                    if v not in (None, "", False) and k != "active_today"}

    _ck = _cache_key(endpoint, params)
    if len(clean_params) <= 2 and _ck in _REQUEST_CACHE:
        logger.info("API %s %s → CACHE HIT (%d items)",
                    endpoint, clean_params, len(_REQUEST_CACHE[_ck]))
        return _REQUEST_CACHE[_ck]

    try:
        resp = requests.get(url, params=clean_params, headers=headers, timeout=15)
        logger.info("API %s %s → %d", endpoint, clean_params, resp.status_code)

        if resp.status_code == 200:
            data = resp.json()
            logger.info("API %s → %s items",
                        endpoint, len(data) if isinstance(data, list) else "1")
            if len(clean_params) <= 2:
                _REQUEST_CACHE[_ck] = data
            return data
        elif resp.status_code in (401, 403):
            logger.warning("API %s → %d (accès refusé)", endpoint, resp.status_code)
            return []
        elif resp.status_code == 404:
            return []
        else:
            logger.error("API %s → %d : %s", endpoint, resp.status_code, resp.text[:200])
            return []
    except requests.exceptions.ConnectionError:
        logger.error("Impossible de contacter %s — FastAPI est-il démarré ?", API_BASE_URL)
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
        return [{
            "total_tasks": len(tasks),
            "todo":        sc.get("Todo", 0),
            "in_progress": sc.get("In Progress", 0),
            "done":        sc.get("Done", 0),
            "blocked":     sc.get("Blocked", 0),
            "critical":    pc.get("Critical", 0),
            "high":        pc.get("High", 0),
        }]

    try:
        token_from_headers = headers.get("Authorization","").replace("Bearer ","")
        tasks     = call_api("/tasks",     {}, token_from_headers)
        employees = call_api("/employees", {}, token_from_headers)
    except Exception:
        return []

    managers = {e["employee_id"]: e for e in employees if e.get("role") == "manager"}

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
        tlist  = mgr_tasks.get(mid, [])
        sc     = Counter(t.get("status", "")   for t in tlist)
        pc     = Counter(t.get("priority", "") for t in tlist)
        done_n = sc.get("Done", 0)
        total  = len(tlist)
        done_pct = round(done_n * 100 / total) if total > 0 else 0
        result.append({
            "manager_id":    mid,
            "manager_name":  f"{mgr.get('first_name','')} {mgr.get('last_name','')}".strip(),
            "department":    mgr.get("department", ""),
            "total_tasks":   total,
            "blocked":       sc.get("Blocked", 0),
            "blocked_tasks": sc.get("Blocked", 0),
            "todo":          sc.get("Todo", 0),
            "in_progress":   sc.get("In Progress", 0),
            "done":          done_n,
            "done_tasks":    done_n,
            "done_pct":      done_pct,
            "critical_tasks":pc.get("Critical", 0),
            "open_critical": sum(1 for t in tlist
                                 if t.get("priority") == "Critical"
                                 and t.get("status") != "Done"),
            "high_tasks":    pc.get("High", 0),
            "total_projects":len({t.get("project_id") for t in tlist
                                   if t.get("project_id")}),
        })

    result.sort(key=lambda r: (-(r["blocked"]), -(r["critical_tasks"])))

    has_any_blocked = any(r["blocked"] > 0 for r in result)
    if has_any_blocked:
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
                logger.warning("sanitize_filters: '%s' liste → garde premier '%s'", k, v[0])
                clean[k] = v[0]
        elif isinstance(v, bool):
            clean[k] = v
        elif v is not None and v != "":
            clean[k] = v
    return clean






def _rerank_doc_chunks(chunks: list, question: str, top_k: int = 5) -> list:
    # Pure vector search — pas de keyword matching
    return chunks[:top_k]
    



# ═══════════════════════════════════════════════════════════════════════════════
# GLOSSAIRE
# ═══════════════════════════════════════════════════════════════════════════════
_DEFINITION_PATTERNS = [
    "c'est quoi", "cest quoi", "qu'est-ce que", "quest ce que",
    "définition", "definition", "explique", "signifie", "que veut dire",
]
_ERP_DEFINITIONS = {
    "spi": (
        "**SPI** (Schedule Performance Index) — indicateur de planning.\n\n"
        "**Formule :** SPI = Valeur Acquise (EV) / Valeur Planifiée (PV)\n\n"
        "• SPI = 1.0 → dans les temps\n• SPI > 1.0 → en **avance**\n"
        "• SPI < 1.0 → en **retard**"
    ),
    "cpi": (
        "**CPI** (Cost Performance Index) — indicateur budgétaire.\n\n"
        "**Formule :** CPI = Valeur Acquise (EV) / Coût Réel (AC)\n\n"
        "• CPI = 1.0 → dans le budget\n• CPI > 1.0 → sous budget\n"
        "• CPI < 1.0 → hors budget"
    ),
    "kpi": (
        "**KPI** (Key Performance Indicator) — indicateur clé de performance.\n\n"
        "Dans cet ERP, les KPIs incluent : SPI, CPI, budget_variance_percentage, "
        "schedule_variance_days, quality_score, risk_level."
    ),
    "ev": "**EV** (Earned Value) : valeur budgétaire du travail réellement accompli à date.",
    "pv": "**PV** (Planned Value) : valeur budgétaire du travail prévu à date.",
    "ac": "**AC** (Actual Cost) : coût réellement dépensé.",
    # BTP acronyms (Fix from session)
    "ao": (
        "**AO** (Appel d'Offres) — procédure par laquelle le maître d'ouvrage sollicite "
        "des offres de plusieurs entreprises pour la réalisation de travaux.\n\n"
        "• **AO ouvert** : toute entreprise peut soumissionner\n"
        "• **AO restreint** : seules les entreprises présélectionnées sont invitées"
    ),
    "moa": "**MOA** (Maître d'Ouvrage) : entité qui commande et finance le projet.",
    "moe": "**MOE** (Maître d'Œuvre) : entité chargée de la conception et du suivi des travaux.",
    "dce": "**DCE** (Dossier de Consultation des Entreprises) : documents remis aux candidats lors d'un AO.",
    "dpgf": "**DPGF** (Décomposition du Prix Global et Forfaitaire) : document de chiffrage détaillé.",
    "cctp": "**CCTP** (Cahier des Clauses Techniques Particulières) : exigences techniques du marché.",
    "bpu": "**BPU** (Bordereau des Prix Unitaires) : liste des prix unitaires proposés.",
    "dqs": "**DQS** (Démarche Qualité et Sécurité) : procédures qualité et sécurité chantier.",
    "ppsps": "**PPSPS** (Plan Particulier de Sécurité et de Protection de la Santé) : document obligatoire sécurité chantier.",
    "piq": "**PIQ** (Plan d'Inspection et Qualité) : contrôles qualité à réaliser.",
    "erp": "**ERP** (Enterprise Resource Planning) : logiciel de gestion intégré. Ici, système de gestion des projets BTP.",
    "hse": "**HSE** (Hygiène, Sécurité, Environnement) : département responsable de la sécurité sur les chantiers.",
    "epi": "**EPI** (Équipements de Protection Individuelle) : casque, chaussures de sécurité, gilet, gants, lunettes, harnais. Port obligatoire sur tous les chantiers.",
    "bpe": "**BPE** (Béton Prêt à l'Emploi) : béton fabriqué en centrale et livré sur chantier par camion toupie.",
    "btp": "**BTP** (Bâtiment et Travaux Publics) : secteur de la construction.",
    "drh": "**DRH** (Directeur des Ressources Humaines) : responsable du département RH.",
    "cfo": "**CFO** (Chief Financial Officer) : Directeur Financier.",
    "tf":  "**TF** (Taux de Fréquence) = Accidents × 1 000 000 / Heures travaillées.",
    "tg":  "**TG** (Taux de Gravité) = Jours perdus × 1 000 / Heures travaillées.",
}

def is_definition_question(q: str) -> bool:
    return any(p in q.lower() for p in _DEFINITION_PATTERNS)

def handle_definition_question(q: str) -> str | None:
    q_l = q.lower()
    # Word-boundary matching: check if key appears as a standalone word
    q_words = _re.findall(r"[a-zàâçéèêëîïôùûü]+", q_l)
    for key, answer in _ERP_DEFINITIONS.items():
        if key in q_words:
            return answer
    # Fallback: substring match for keys longer than 3 chars
    for key, answer in _ERP_DEFINITIONS.items():
        if len(key) > 3 and key in q_l:
            return answer
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# QUESTIONS PROCÉDURALES
# ═══════════════════════════════════════════════════════════════════════════════
_PROCEDURAL_PATTERNS = [
    "procédure", "procedure", "processus", "comment fonctionne", "comment se passe",
    "comment faire", "quelle est la règle", "quelle est la politique", "politique de",
    "règlement", "reglement", "étapes", "etapes", "qui approuve", "qui valide",
    "délai de", "delai de", "comment calculer", "conditions pour", "dans quel cas",
    "comment soumettre", "comment deposer", "comment déposer", "comment demander",
    "comment créer", "comment creer", "comment faire une demande", "comment poser",
    "comment postuler", "comment effectuer", "soumettre une demande",
    "déposer une demande", "deposer une demande", "faire une demande de",
    "demande de conge", "demande de congé", "demander un conge", "demander un congé",
    "quel est le délai", "quel est le delai", "quel est le processus",
    "quelle est la procédure", "quelle est la procedure",
    "combien de jours de preavis", "combien de jours de préavis",
    "qui doit approuver", "comment est calculé", "comment est calcule",
    "quelles sont les conditions", "quelles sont les règles", "quelles sont les regles",
    "quels sont les types", "quels documents", "quelles pièces", "quelles pieces",
]

def is_procedural_question(q: str) -> bool:
    q_l = q.lower()
    if not any(p in q_l for p in _PROCEDURAL_PATTERNS):
        return False
    _DATA_INTENT = [
        "montre", "affiche", "donne moi la liste", "liste des", "combien d'",
        "statut de", "état de", "mon statut", "ma demande", "mes demandes",
        "quel est le statut", "quelle est l'état", "voir ma", "voir mes",
        "est-ce que ma", "est ce que ma", "a été approuvée", "a ete approuvee",
        "a été refusée", "a ete refusee", "est approuvée", "est refusée",
    ]
    if any(w in q_l for w in _DATA_INTENT):
        return False
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# FIX 7 (v30) — POLICY QUESTION CLASSIFIER
# Intercepts questions asking about rules/durations/policies BEFORE the planner.
# These questions should NEVER reach /leave-requests or any other API endpoint.
# ═══════════════════════════════════════════════════════════════════════════════
_POLICY_PATTERNS = [
    # Congés — durées et règles
    r"\bcombien de jours\b",
    r"\bdroit (à|au|aux)\b",
    r"\bdurée (du|de la|des) congé",
    r"\bcongé (annuel|maladie|maternité|maternite|paternité|paternite|exceptionnel|sans solde)\b",
    r"\bpréavis\b", r"\bpreavis\b",
    r"\bque se passe.t.il si\b",
    r"\bsont.ils reportés\b", r"\bsont.ils reportes\b",
    r"\bqui approuve\b",
    r"\bsolde de congé\b", r"\bsolde de conge\b",
    r"\breport.? (de|des) congé", r"\breport.? (de|des) conge",
    # Sécurité chantier
    r"\bepi\b",
    r"\béquipement.? de protection\b", r"\bequipement.? de protection\b",
    r"\baccident.? sur chantier\b",
    r"\bvitesse (limite|maximale)\b",
    r"\bformation sécurité\b", r"\bformation securite\b",
    r"\bharnais\b",
    r"\bcertificat médical\b", r"\bcertificat medical\b",
    r"\bnuméro.? d'urgence\b", r"\bnumero.? d.urgence\b",
    r"\btaux de fréquence\b", r"\btaux de frequence\b",
    r"\btaux de gravité\b", r"\btaux de gravite\b",
    # Règlement intérieur
    r"\bhoraires (de travail|du bureau|chantier)\b",
    r"\bmajoration\b",
    r"\bsanction\b", r"\bavertissement\b",
    r"\bavantages? sociaux\b",
    r"\bprime.? (de fin|chantier|annuel)\b",
    r"\bmise à pied\b", r"\bmise a pied\b",
    r"\blicenciement\b",
    r"\bcode vestimentaire\b",
    r"\bheures supplémentaires\b", r"\bheures supplementaires\b",
    r"\bpointage\b",
    # Achats / fournisseurs
    r"\bseuil.? d.approbation\b",
    r"\bréférencer? (un|le|nouveau) fournisseur\b",
    r"\breferencer? (un|le|nouveau) fournisseur\b",
    r"\bdélai de paiement\b", r"\bdelai de paiement\b",
    r"\bcombien de devis\b",
    r"\bprocessus d.achat\b",
    # Incidents / qualité
    r"\bcatégories? d.incident\b", r"\bcategories? d.incident\b",
    r"\bdélai.? de résolution\b", r"\bdelai.? de resolution\b",
    r"\broot cause\b", r"\banalyse des causes\b",
    # Onboarding / intégration
    r"\bpremier jour\b",
    r"\bonboarding\b",
    r"\bpériode d.essai\b", r"\bperiode d.essai\b",
    r"\baccès.? erp\b", r"\bacces.? erp\b",
    r"\brôle.? (employé|manager|ceo)\b", r"\brole.? (employe|manager|ceo)\b",
    # Équipements
    r"\bstatuts.? (des|d.un) équipement\b", r"\bstatuts.? (des|d.un) equipement\b",
    r"\bmaintenance préventive\b", r"\bmaintenance preventive\b",
    r"\ben cas de panne\b",
]

_re_policy = _re.compile("|".join(_POLICY_PATTERNS), _re.IGNORECASE)

# These phrases signal the question is about LIVE DATA, not policy →
# even if a policy pattern matched, don't intercept
_POLICY_DATA_OVERRIDE = [
    "montre", "affiche", "liste des", "donne moi", "quels sont les",
    "combien d'employés", "combien d employes",
    "qui est", "quel employé", "quel employe",
    "statut de", "ma demande", "mes demandes", "mon solde",
    "actuellement", "en ce moment", "aujourd'hui", "maintenant",
    "est-ce que", "est ce que",
]


def is_policy_question(q: str) -> bool:
    """
    Returns True if the question asks about a company policy, rule, or procedure
    (duration, approval rules, safety requirements, etc.) rather than live data.
    These questions should be answered from RAG documents only, never from API endpoints.
    """
    q_l = q.lower()
    # If the question clearly wants live data, don't intercept
    if any(w in q_l for w in _POLICY_DATA_OVERRIDE):
        return False
    return bool(_re_policy.search(q_l))


# ═══════════════════════════════════════════════════════════════════════════════
# FIX 8 (v30) — RAG-ONLY LLM CALL FOR POLICY QUESTIONS
# ═══════════════════════════════════════════════════════════════════════════════
def _ask_llm_rag_only(question: str) -> str:
    """
    Answers a policy/rule question using ONLY RAG document chunks.
    No API calls are made. Uses the same doc_retriever + _rerank_doc_chunks
    pipeline as the #H4 procedural path, then calls rag_doc_chain.
    """
    logger.info("Policy question → RAG only (no API calls)")
    raw_chunks   = doc_retriever.invoke(question)
    proc_chunks  = _rerank_doc_chunks(raw_chunks, question, top_k=6)
    for i, ch in enumerate(proc_chunks):
        logger.info("Policy chunk[%d]: file=%s preview=%r",
                    i, ch.metadata.get("filename", "?"), ch.page_content[:80])
    doc_ctx = "\n\n".join(
        f"[{ch.metadata.get('category', '')} — {ch.metadata.get('filename', 'doc')}]\n"
        f"{ch.page_content}"
        for ch in proc_chunks
    )
    if not doc_ctx.strip():
        return "Je n'ai pas trouvé de documentation sur ce sujet dans les politiques internes."
    result = rag_doc_chain.invoke({"question": question, "doc_context": doc_ctx})
    return clean_answer(str(result))


# ═══════════════════════════════════════════════════════════════════════════════
# PLANNER FALLBACK RULES
# ═══════════════════════════════════════════════════════════════════════════════
_KNOWN_DEPARTMENTS = [
    "Finance", "Projects", "Operations", "Human Resources", "IT", "Executive"
]
_DEPARTMENT_ALIASES = {
    "finance":            "Finance",
    "projet":             "Projects",
    "projects":           "Projects",
    "operations":         "Operations",
    "opérations":         "Operations",
    "ressources humaines":"Human Resources",
    "rh":                 "Human Resources",
    "informatique":       "IT",
    "it":                 "IT",
    "direction":          "Executive",
    "executive":          "Executive",
}
_STATUS_ALIASES = {
    "bloqué": "Blocked", "bloquee": "Blocked", "bloque": "Blocked",
    "en cours": "In Progress", "en_cours": "In Progress",
    "à faire": "Todo", "a faire": "Todo", "todo": "Todo",
    "terminé": "Done", "termine": "Done", "done": "Done",
    "planification": "Planning", "planning": "Planning",
    "complété": "Completed", "complete": "Completed", "completed": "Completed",
    "ouvert": "Open", "open": "Open",
    "résolu": "Resolved", "resolu": "Resolved",
    "fermé": "Closed", "ferme": "Closed",
    "approuvé": "Approved", "approuve": "Approved",
    "en attente": "Pending", "pending": "Pending",
    "rejeté": "Rejected", "rejete": "Rejected",
    "disponible": "Available",
    "maintenance": "Maintenance",
    "utilisé": "In Use", "utilise": "In Use",
}
_PRIORITY_ALIASES = {
    "critique": "Critical", "critical": "Critical",
    "haute": "High", "high": "High", "élevée": "High", "elevee": "High",
    "moyenne": "Medium", "medium": "Medium",
    "basse": "Low", "low": "Low", "faible": "Low",
}
_SEVERITY_ALIASES = _PRIORITY_ALIASES.copy()
_CATEGORY_ALIASES = {
    "sécurité": "Safety", "securite": "Safety", "safety": "Safety",
    "qualité": "Quality", "qualite": "Quality", "quality": "Quality",
    "délai": "Delay", "delai": "Delay", "delay": "Delay",
    "budget": "Budget",
    "technique": "Technical", "technical": "Technical",
    "autre": "Other", "other": "Other",
}


def _extract_filters_from_question(q_lower: str, endpoint: str) -> dict:
    filters = {}
    if endpoint == "/employees":
        for alias, dept in _DEPARTMENT_ALIASES.items():
            if alias in q_lower:
                filters["department"] = dept
                logger.info("Fallback filter: department=%s", dept)
                break
        for role_kw, role_val in [("manager","manager"), ("ceo","ceo"),
                                   ("employé","employee"), ("rh","rh")]:
            if role_kw in q_lower and "department" not in filters:
                filters["role"] = role_val
                break
    if endpoint in ("/tasks", "/projects", "/issues", "/leave-requests", "/equipment"):
        for alias, val in _STATUS_ALIASES.items():
            if alias in q_lower:
                filters["status"] = val
                logger.info("Fallback filter: status=%s", val)
                break
    if endpoint == "/tasks":
        for alias, val in _PRIORITY_ALIASES.items():
            if alias in q_lower:
                filters["priority"] = val
                logger.info("Fallback filter: priority=%s", val)
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
        _now_kws = ["maintenant", "aujourd'hui", "aujourd hui", "en ce moment",
                    "actuellement", "active_today"]
        if any(kw in q_lower for kw in _now_kws):
            filters["active_today"] = True
    return filters


_FALLBACK_RULES = [
    (["employe", "employé", "personnel", "salarie", "salarié", "staff"],  "/employees"),
    (["projet", "chantier"],                                               "/projects"),
    (["tache", "tâche", "task"],                                           "/tasks"),
    (["conge", "congé", "absence", "absent"],                              "/leave-requests"),
    (["incident", "issue", "probleme", "problème"],                        "/issues"),
    (["kpi", "indicateur"],                                                "/kpis"),
    (["equipement", "équipement", "materiel", "matériel"],                 "/equipment"),
    (["fournisseur", "supplier"],                                          "/suppliers"),
    (["resume", "résumé", "synthese", "synthèse", "statistique", "stat"], "/stats/summary"),
    (["client", "clients"],                                                "/projects"),
]


def _apply_fallback_plan(q_lower: str, role_allowed: list) -> list:
    for keywords, endpoint in _FALLBACK_RULES:
        if endpoint not in role_allowed:
            continue
        if any(kw in q_lower for kw in keywords):
            filters = _extract_filters_from_question(q_lower, endpoint)
            logger.info("Fallback déterministe → %s filters=%s (mots: %s)",
                        endpoint, filters,
                        [kw for kw in keywords if kw in q_lower])
            return [{"endpoint": endpoint, "filters": filters}]
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════
RAG_DOC_TEMPLATE = """Tu es un assistant interne. Tu reponds en francais.
Reponds UNIQUEMENT a partir des documents fournis.
Si l'information n'est pas dans les documents, dis-le clairement.
Commence directement par la reponse.
INTERDIT d'expliquer pourquoi un document n'est pas pertinent. Ne mentionne jamais les sources.

DOCUMENTS:
{doc_context}

Question: {question}

Reponse:"""
PLANNER_TEMPLATE = """Tu es un planificateur de requetes pour un ERP de construction.
Tu dois repondre UNIQUEMENT avec du JSON brut. Pas de texte. Pas de Bonjour. Pas d'explication. JUSTE le JSON.

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
- liste employes, tous les employes, personnel, liste de tous les employes, affiche employes → /employees avec {{}}
- employes d un departement → /employees avec {{"department": "NomExact"}}
- projets en retard, retard, delai, schedule → /kpis avec {{"delayed": true}}
- projets a risque eleve → /kpis avec {{"risk_level": "High"}}
- projets a risque critique, risque le plus critique → /kpis avec {{"risk_level": "High"}}
- IMPORTANT: pour /kpis le risque max est "High", jamais "Critical"
- taches critiques → /tasks avec {{"priority": "Critical"}}
- taches critiques non terminees, taches non terminees, taches a faire → /tasks avec {{"priority": "Critical", "status": "Todo"}}
- taches critiques en cours → /tasks avec {{"priority": "Critical", "status": "In Progress"}}
- taches critiques bloquees → /tasks avec {{"priority": "Critical", "status": "Blocked"}}
- taches critiques (sans precision) → /tasks avec {{"priority": "Critical"}}
- taches bloquees → /tasks avec {{"status": "Blocked"}}
- taches a faire, non terminees → /tasks avec {{"status": "Todo"}}
- taches en cours → /tasks avec {{"status": "In Progress"}}
- mes taches → /tasks avec {{"status": "In Progress"}}
- taches bloquees par manager, quel manager a le plus de taches bloquees → /tasks/by-manager avec {{}}
- performance des managers, comparaison managers → /tasks/by-manager avec {{}}
- statistiques managers, manager le moins performant → /stats/by-manager avec {{}}
- employes en conge, absents → /leave-requests avec {{"status": "Approved"}}
- employes en conge EN CE MOMENT, maintenant, aujourd'hui → /leave-requests avec {{"status": "Approved", "active_today": true}}
- si question contient [active_today=true] → ajouter "active_today": true aux filtres
- conges en attente → /leave-requests avec {{"status": "Pending"}}
- statut de ma demande de conge, quel est le statut, ma demande → /leave-requests avec {{"employee_id": "{user_id}"}}
- conges d un employe specifique → /leave-requests avec {{"employee_id": "<ID_EXACT>"}}
- tous les conges, liste des conges → /leave-requests avec {{}}
- incidents critiques → /issues avec {{"severity": "Critical"}}
- incidents ouverts → /issues avec {{"status": "Open"}}
- incidents par categorie securite → /issues avec {{"category": "Safety"}}
- projets en cours → /projects avec {{"status": "In Progress"}}
- projets termines → /projects avec {{"status": "Completed"}}
- equipements disponibles → /equipment avec {{"status": "Available"}}
- equipements en maintenance → /equipment avec {{"status": "Maintenance"}}
- statistiques globales, resume → /stats/summary avec {{}}
- statistiques taches globales → /stats/tasks avec {{}}
- kpis, performance projets, indicateurs → /kpis avec {{}}
- question sur politique, procedure, definition, regle → endpoints vide []
- liste clients, mes clients, liste de mes clients, tous les clients → /projects avec {{}}
- projets d un client specifique, client X → /projects avec {{"client_name": "<NomClient>"}}
- quel client, quels clients, clients actifs → /projects avec {{"status": "In Progress"}}

REGLE CRITIQUE — [employee_id=Exx] DANS LA QUESTION:
Si la question contient un tag [employee_id=Exx, nom=Prenom Nom], tu DOIS:
  1. Extraire l ID exact (ex: E003) depuis le tag
  2. /employees avec {{"employee_id": "E003"}}
  3. /leave-requests avec {{"employee_id": "E003"}}
  4. /tasks avec {{"assigned_to": "E003"}}   ← tasks utilise assigned_to
  5. /timesheets avec {{"employee_id": "E003"}}
  NE JAMAIS appeler /employees sans filtre si un [employee_id=Exx] est present

SECURITE:
- role=employee UNIQUEMENT: ajouter assigned_to="{user_id}" pour /tasks
- role=employee UNIQUEMENT: ajouter employee_id="{user_id}" pour /leave-requests et /timesheets
- role=rh: utiliser UNIQUEMENT /leave-requests et /employees
- role=manager: NE JAMAIS ajouter assigned_to="{user_id}" aux filtres /tasks — le scope equipe est gere automatiquement par le systeme
- role=manager: NE JAMAIS ajouter employee_id="{user_id}" aux filtres sauf si la question porte explicitement sur le manager lui-meme

FORMAT STRICT:
- INTERDIT: liste/array dans les filtres — UN SEUL statut par endpoint
- INTERDIT: cle "params" — utiliser UNIQUEMENT "filters"
- INTERDIT: plus de 5 endpoints
- FORMAT: {{"reasoning": "explication courte", "endpoints": [...]}}
- La cle "reasoning" DOIT etre en PREMIER dans le JSON
- REPONSE = JSON PUR uniquement

REGLE EQUIPE MANAGER (CRITIQUE):
- mon equipe, membres de mon equipe, qui je supervise, mes employes, mon team → /employees avec {{"supervised_by": "{user_id}"}}
- conges de mon equipe, absences de mon equipe → /leave-requests avec {{"supervised_by": "{user_id}"}}
- taches de mon equipe, taches de mes employes → /tasks avec {{"supervised_by": "{user_id}"}}
- INTERDIT ABSOLU : Ne JAMAIS utiliser department comme filtre pour "mon equipe" ou "mes employes"
- Le departement n est PAS l equipe — une equipe = les employes directement supervises
- supervised_by est un filtre virtuel traite par le systeme, pas par la base de donnees

EXEMPLES (imite exactement ce format):

Question: "Quelles sont les tâches critiques non terminées ?"
JSON: {{"reasoning": "Taches Critical avec status Todo uniquement", "endpoints": [{{"endpoint": "/tasks", "filters": {{"priority": "Critical", "status": "Todo"}}}}]}}

Question: "Quels sont les projets en retard ?"
JSON: {{"reasoning": "La question porte sur les projets en retard, mapping vers /kpis avec delayed:true", "endpoints": [{{"endpoint": "/kpis", "filters": {{"delayed": true}}}}]}}

Question: "Liste des employes du departement IT"
JSON: {{"reasoning": "Recherche d employes filtres par departement IT", "endpoints": [{{"endpoint": "/employees", "filters": {{"department": "IT"}}}}]}}

Question: "Taches bloquees et critiques"
JSON: {{"reasoning": "Deux filtres distincts sur /tasks : statut Blocked et priorite Critical", "endpoints": [{{"endpoint": "/tasks", "filters": {{"status": "Blocked"}}}}, {{"endpoint": "/tasks", "filters": {{"priority": "Critical"}}}}]}}

Question: "Qui sont les membres de mon equipe ?"
JSON: {{"reasoning": "Manager demande son equipe directe, supervised_by virtuel — jamais department", "endpoints": [{{"endpoint": "/employees", "filters": {{"supervised_by": "{user_id}"}}}}]}}

Question: "Liste de mes clients"
JSON: {{"reasoning": "Les clients sont dans /projects champ client_name, lister tous les projets", "endpoints": [{{"endpoint": "/projects", "filters": {{}}}}]}}

Question: "Projets du client Carthage Development Group"
JSON: {{"reasoning": "Filtrer les projets par client_name exact", "endpoints": [{{"endpoint": "/projects", "filters": {{"client_name": "Carthage Development Group"}}}}]}}

Question: "Quels sont les conges de mon equipe ?"
JSON: {{"reasoning": "Conges des employes supervises par ce manager, supervised_by virtuel", "endpoints": [{{"endpoint": "/leave-requests", "filters": {{"supervised_by": "{user_id}"}}}}]}}

Question: "Quelles sont les taches de mes employes ?"
JSON: {{"reasoning": "Taches des employes de l equipe du manager, supervised_by virtuel", "endpoints": [{{"endpoint": "/tasks", "filters": {{"supervised_by": "{user_id}"}}}}]}}

Question: "Quelles sont les taches critiques non terminees sur mes projets ?"
JSON: {{"reasoning": "Taches de priorite Critical non terminees, pas de filtre status car Done sera filtre cote Python", "endpoints": [{{"endpoint": "/tasks", "filters": {{"priority": "Critical"}}}}]}}

Role: {user_role} | ID: {user_id}
Question: {question}

JSON:"""

ANSWER_TEMPLATE = """Tu es un assistant ERP. Tu reponds en francais.
Tu affiches les donnees EXACTEMENT comme elles apparaissent dans DONNEES LIVE.

REGLES ABSOLUES:
R1. Si DONNEES LIVE contient un bloc "=== ... ===", le recopier MOT POUR MOT sans rien enlever ni filtrer ni renommer. INTERDIT de changer le nom du bloc (ex: PROJECTS ne devient pas CLIENTS).
R2. Ne JAMAIS ajouter de phrase introductive, commentaire ou note.
R3. Ne JAMAIS ecrire "Notez que", "Note:", "Cependant", "Puisque vous".
R4. Ne JAMAIS terminer par une question ou offre d aide.
R5. Ne JAMAIS inventer de donnee absente de DONNEES LIVE.
R6. Si question analytique, texte court structure uniquement depuis DONNEES LIVE.
R7. Si DONNEES LIVE contient "Aucune donnee live" ou est vide → reponds UNIQUEMENT: "Aucune donnée disponible pour cette requête."
R8. INTERDIT d inventer des noms, postes, departements ou chiffres qui ne sont PAS dans DONNEES LIVE.
R9. INTERDIT de repondre avec des donnees si DONNEES LIVE ne contient pas de bloc "=== ... ===".
R10. INTERDIT d ajouter une liste ou un resume APRES le bloc === : le bloc est la reponse complete, rien d autre.
R11. COPIE INTEGRALE OBLIGATOIRE : Tu DOIS recopier TOUTES les lignes du bloc ===, sans exception.
     Si Resultats (16) → tu affiches exactement 16 lignes. Pas 8, pas 10, pas 12. TOUTES.
     Couper la liste = ERREUR CRITIQUE. Compter les lignes avant de repondre.
R12. INTERDIT de dire que tu n as pas acces aux donnees si DONNEES LIVE contient un bloc === avec des resultats.
     Les donnees sont DIRECTEMENT dans DONNEES LIVE — tu dois les afficher sans les remettre en question.
     Toute phrase du type "je suis incapable", "je n ai pas acces", "je ne peux pas" est une ERREUR CRITIQUE
     quand DONNEES LIVE contient des resultats.
R13. INTERDIT d ajouter du texte APRES le dernier bloc ===. Le bloc === est la reponse complete et finale.
     Ne JAMAIS ecrire "Le manager X a le plus de..." ou tout autre resume/commentaire apres le bloc.
     Si la question est analytique (quel manager a le plus de X ?), reponds avec UNE SEULE PHRASE COURTE
     avant le bloc, jamais apres.
R14. INTERDIT de traduire les labels des blocs === : utiliser EXACTEMENT le label tel qu il apparait dans
     DONNEES LIVE. Si DONNEES LIVE dit "=== PROJECTS ===" ecrire "=== PROJECTS ===" pas "=== PROJETS ===".

EXEMPLES:

Question: liste des employes
DONNEES: === EMPLOYEES === Resultats (3): Ali — Ingenieur — Projets ...
REPONSE: === EMPLOYEES === Resultats (3): Ali — Ingenieur — Projets ...

Question: lister mes clients
DONNEES: === CLIENTS === Resultats (10): - Municipalite de Sousse | Projet: Complexe Sportif | ...
REPONSE: === CLIENTS === Resultats (10): - Municipalite de Sousse | Projet: Complexe Sportif | ...

Question: quel manager a le plus de taches bloquees ?
DONNEES: === TASKS-BY-MANAGER === Resultats (2): - Nadia Hamdi (Projects) | Total: 24 | Bloques: 10 | Critiques: 12 | En cours: 5 | Termines: 3 | Avancement: 13%\n- Karim Jebali (Projects) | Total: 15 | Bloques: 5 | ...
REPONSE: === TASKS-BY-MANAGER === Resultats (2): - Nadia Hamdi (Projects) | Total: 24 | Bloques: 10 | Critiques: 12 | En cours: 5 | Termines: 3 | Avancement: 13%\n- Karim Jebali (Projects) | ...

Question: quels projets sont en retard ?
DONNEES: === KPIS === Resultats (15): - Complexe Sportif Sousse | Retard: 56j | ...
REPONSE: === KPIS === Resultats (15): - Complexe Sportif Sousse | Retard: 56j | ...

Question: quels employes sont en conge en ce moment ?
DONNEES: === LEAVE-REQUESTS === Resultats (4): - Alice Martin | Type: Annual | Du: 2026-03-08 au 2026-03-14 | Jours: 5 | Statut: Approved ...
REPONSE: === LEAVE-REQUESTS === Resultats (4): - Alice Martin | Type: Annual | Du: 2026-03-08 au 2026-03-14 | Jours: 5 | Statut: Approved ...

Question: combien de jours de conge a pris Nadia Hamdi ?
DONNEES:
=== LEAVE-REQUESTS ===
Bilan Nadia Hamdi : 2j approuves | 2j en attente
Resultats (2):
- Nadia Hamdi | Type: Sick | Du: 2026-02-09 au 2026-02-10 | Jours: 2 | Statut: Approved
- Nadia Hamdi | Type: Personal | Du: 2026-02-23 au 2026-02-24 | Jours: 2 | Statut: Pending
REPONSE:
=== LEAVE-REQUESTS ===
Bilan Nadia Hamdi : 2j approuves | 2j en attente
Resultats (2):
- Nadia Hamdi | Type: Sick | Du: 2026-02-09 au 2026-02-10 | Jours: 2 | Statut: Approved
- Nadia Hamdi | Type: Personal | Du: 2026-02-23 au 2026-02-24 | Jours: 2 | Statut: Pending

DONNEES LIVE:
{live_context}

CONNAISSANCES DOCUMENTAIRES:
{doc_context}

PROFIL: {user_name} | Role: {user_role}
Question: {question}

REPONSE:"""

RAG_DOC_TEMPLATE = """Tu es un assistant interne. Tu reponds en francais.
Reponds UNIQUEMENT a partir des documents fournis.
Si l'information n'est pas dans les documents, dis-le clairement.
Commence directement par la reponse.

DOCUMENTS:
{doc_context}

Question: {question}

Reponse:"""

planner_prompt = ChatPromptTemplate.from_template(PLANNER_TEMPLATE)
planner_chain  = planner_prompt | planner_model

answer_prompt  = ChatPromptTemplate.from_template(ANSWER_TEMPLATE)
answer_chain   = answer_prompt | answer_model

rag_doc_prompt = ChatPromptTemplate.from_template(RAG_DOC_TEMPLATE)
rag_doc_chain  = rag_doc_prompt | answer_model


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
            return (
                f"=== PROFIL EMPLOYE ===\n"
                f"Nom        : {r.get('first_name','')} {r.get('last_name','')}\n"
                f"ID         : {r.get('employee_id','')}\n"
                f"Poste      : {r.get('position','')}\n"
                f"Departement: {r.get('department','')}\n"
                f"Role ERP   : {r.get('role','')}\n"
            )
        lines = [
            f"{r.get('first_name','')} {r.get('last_name','')} — "
            f"{r.get('position','')} — {r.get('department','')}"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/tasks":
        lines = [
            f"- {r.get('task_id','')}: {r.get('title','')} | "
            f"Statut: {r.get('status','')} | Priorite: {r.get('priority','')} | "
            f"Echeance: {r.get('due_date','')} | "
            f"Assigne a: {_resolve_name(r.get('assigned_to',''))} | "
            f"Projet: {r.get('project_id','')}"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/projects":
        if filters.get("_client_view"):
            seen_clients: set = set()
            client_lines = []
            for r in items:
                c = r.get("client_name", "")
                if not c or c in seen_clients:
                    continue
                seen_clients.add(c)
                client_lines.append(
                    f"- {c} | Projet: {r.get('project_name','')} | "
                    f"Statut: {r.get('status','')} | "
                    f"Avancement: {r.get('completion_percentage','')}%"
                )
            return (f"=== CLIENTS ===\nResultats ({len(client_lines)}):\n"
                    + "\n".join(client_lines) + "\n")
        lines = [
            f"- {r.get('project_id','')}: {r.get('project_name','')} | "
            f"Client: {r.get('client_name','')} | "
            f"Statut: {r.get('status','')} | "
            f"Avancement: {r.get('completion_percentage','')}% | "
            f"Budget: {r.get('budget_eur','')} EUR | Lieu: {r.get('location','')}"
            for r in items
        ]
        return f"=== PROJECTS ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/leave-requests":
        lines = [
            f"- {r.get('employee_name','')} | Type: {r.get('leave_type','')} | "
            f"Du: {r.get('start_date','')} au {r.get('end_date','')} | "
            f"Jours: {r.get('total_days','')} | Statut: {r.get('status','')}"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/issues":
        lines = [
            f"- {r.get('issue_id','')}: {r.get('title','')} | "
            f"Severite: {r.get('severity','')} | Categorie: {r.get('category','')} | "
            f"Statut: {r.get('status','')} | Projet: {r.get('project_id','')}"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/kpis":
        valid_items = [
            r for r in items
            if r.get('project_name') or r.get('project_id')
            if not (r.get('cost_performance_index', 1) == 0
                    and r.get('schedule_performance_index', 1) == 0)
        ]
        lines = [
            f"- {r.get('project_name', r.get('project_id',''))} | "
            f"Retard: {r.get('schedule_variance_days','')}j | "
            f"Budget: {r.get('budget_variance_percentage','')}% | "
            f"CPI: {r.get('cost_performance_index','')} | "
            f"SPI: {r.get('schedule_performance_index','')} | "
            f"Risque: {r.get('risk_level','')}"
            for r in valid_items
        ]
        return f"=== {label} ===\nResultats ({len(valid_items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/tasks/by-manager":
        lines = [
            f"- {r.get('manager_name','')} ({r.get('department','')}) | "
            f"Total: {r.get('total_tasks',0)} | Bloques: {r.get('blocked',0)} | "
            f"Critiques: {r.get('critical_tasks',0)} | En cours: {r.get('in_progress',0)} | "
            f"Termines: {r.get('done',0)} | Avancement: {r.get('done_pct',0)}%"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/stats/by-manager":
        lines = [
            f"- {r.get('manager_name','')} ({r.get('department','')}) | "
            f"Taches: {r.get('total_tasks',0)} | Bloquees: {r.get('blocked_tasks',0)} | "
            f"Critiques ouvertes: {r.get('open_critical',0)} | "
            f"Terminees: {r.get('done_tasks',0)} | Projets: {r.get('total_projects',0)}"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/timesheets":
        lines = [
            f"- {r.get('employee_id','')} | Projet: {r.get('project_id','')} | "
            f"Date: {r.get('work_date', r.get('date',''))} | "
            f"Heures: {r.get('hours_worked','')}h | {r.get('task_description','')}"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/equipment":
        lines = [
            f"- {r.get('equipment_id','')}: {r.get('name','')} | "
            f"Statut: {r.get('status','')} | Categorie: {r.get('category','')} | "
            f"Lieu: {r.get('location','')}"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/suppliers":
        lines = [
            f"- {r.get('supplier_name','')} | Categorie: {r.get('category','')} | "
            f"Statut: {r.get('status','')} | Note: {r.get('rating','')} | "
            f"Ville: {r.get('city','')}"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/notifications":
        lines = [
            f"- [{r.get('created_date','')}] {r.get('title','')}: {r.get('message','')} "
            f"({'Lu' if r.get('is_read') else 'Non lu'})"
            for r in items
        ]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"

    elif endpoint == "/stats/summary":
        r = items[0] if items else {}
        return (
            f"=== {label} ===\n"
            f"Projets total: {r.get('total_projects','')} | "
            f"Budget: {r.get('total_budget', r.get('total_budget_eur',''))} EUR | "
            f"Cout reel: {r.get('total_actual_cost', r.get('total_actual_cost_eur',''))} EUR | "
            f"Avancement moy: {r.get('avg_completion', r.get('avg_completion_pct',''))}%\n"
        )

    elif endpoint == "/stats/tasks":
        r = items[0] if items else {}
        return (
            f"=== {label} ===\n"
            f"Total: {r.get('total_tasks','')} | A faire: {r.get('todo','')} | "
            f"En cours: {r.get('in_progress','')} | Terminees: {r.get('done','')} | "
            f"Bloquees: {r.get('blocked','')} | Critiques: {r.get('critical','')}\n"
        )

    else:
        logger.warning("format_endpoint_data: endpoint non géré '%s'", endpoint)
        lines = ["• " + " | ".join(f"{k}: {v}" for k, v in r.items()
                                    if v is not None and k != "password_hash")
                 for r in items[:20]]
        return f"=== {label} ===\nResultats ({len(items)}):\n" + "\n".join(lines) + "\n"


# ═══════════════════════════════════════════════════════════════════════════════
# PLAN PARSER
# ═══════════════════════════════════════════════════════════════════════════════
def normalize_plan(parsed) -> dict:
    def clean_item(item):
        if not isinstance(item, dict):
            return None
        ep = item.get("endpoint", "")
        if not ep:
            return None
        raw_filters = item.get("filters") or item.get("params") or {}
        return {"endpoint": ep, "filters": sanitize_filters(raw_filters)}

    if isinstance(parsed, dict):
        if "endpoints" in parsed and isinstance(parsed["endpoints"], list):
            clean = [clean_item(i) for i in parsed["endpoints"]]
            clean = [i for i in clean if i]
            return {"endpoints": clean, "reasoning": parsed.get("reasoning", "")}
        if "endpoint" in parsed:
            item = clean_item(parsed)
            if item:
                return {"endpoints": [item], "reasoning": "normalized"}

    if isinstance(parsed, list):
        clean = [clean_item(i) for i in parsed if isinstance(i, dict)]
        clean = [i for i in clean if i]
        return {"endpoints": clean, "reasoning": "normalized"}

    return {"endpoints": [], "reasoning": "unknown format"}


def parse_llm_plan(raw: str) -> dict:
    raw = str(raw).strip()

    for attempt in [
        lambda r: json.loads(r),
        lambda r: json.loads(
            _re.sub(r"\s*```\s*$", "",
                    _re.sub(r"^```(?:json)?\s*", "", r, flags=_re.MULTILINE),
                    flags=_re.MULTILINE).strip()
        ),
        lambda r: json.loads(r[r.find("{"):r.rfind("}")+1]),
    ]:
        try:
            return normalize_plan(attempt(raw))
        except Exception:
            pass

    for src in [raw, raw[raw.find("{"):raw.rfind("}")+1] if "{" in raw else ""]:
        try:
            fixed = (src
                     + "]" * max(0, src.count("[") - src.count("]"))
                     + "}" * max(0, src.count("{") - src.count("}")))
            return normalize_plan(json.loads(fixed))
        except Exception:
            pass

    logger.warning("Could not parse plan: %s", raw[:300])
    return {"endpoints": [], "reasoning": "parse error"}


# ═══════════════════════════════════════════════════════════════════════════════
# ANSWER POST-PROCESSOR
# ═══════════════════════════════════════════════════════════════════════════════
_LEAK_LINE_PREFIXES = (
    "je vais répondre", "je vais repondre", "en fonction des règles", "en fonction des regles",
    "puisque la question", "puisque vous", "voici ma réponse", "voici ma reponse",
    "notez que", "note :", "note:", "il est important", "cependant,", "cependant ",
    "puisque vous", "pour obtenir une réponse", "pour obtenir une reponse",
    "je suppose que", "cette réponse est basée", "cette reponse est basee",
    "les employés disponibles sont", "les employes disponibles sont",
    "puis-je vous", "avez-vous d", "n'hésitez pas", "n hesitez pas",
    "si vous avez", "bien cordialement", "cordialement", "best,", "[votre nom]",
    "les projets en retard sont", "les projets sont", "voici les projets",
    "voici la liste", "voici les employés", "voici les employes",
    "en résumé", "en resume", "pour résumer", "pour resumer",
    "il y a donc", "au total,", "ainsi,",
    "je vais suivre", "je vais répondre", "je vais repondre",
    "voici ma réponse", "voici ma reponse", "voici la réponse",
    "voici la reponse", "voici les informations",
    "après avoir consulté", "apres avoir consulte",
    "en fonction des règles", "en fonction des regles",
    "en fonction des données", "en fonction des donnees",
    "je suis un assistant erp",
    "puisque les données", "puisque les donnees", "puisque la question",
    "remarque :", "remarque:", "note finale", "information complémentaire",
    "je suis désolé", "je suis desole", "cependant, en consultant",
    "si vous avez d'autres", "je serais ravi",
    "la réponse est", "la reponse est", "il y a", "les projets qui ont",
    "je vois que", "pour répondre", "pour repondre",
    "le manager", "nadia hamdi avec", "karim jebali avec",
    "le responsable", "ainsi, le", "donc, le", "en conclusion",
    "d'après les données", "d apres les donnees", "selon les données",
    "selon les donnees", "les résultats montrent", "les resultats montrent",
)

def _remove_duplicate_blocks(text: str) -> str:
    block_pattern = _re.compile(r"(=== [^=\n]+ ===)", _re.MULTILINE)
    positions = [(m.start(), m.group(1)) for m in block_pattern.finditer(text)]
    if len(positions) <= 1:
        return text

    blocks = []
    for i, (start, label) in enumerate(positions):
        end = positions[i+1][0] if i+1 < len(positions) else len(text)
        content = text[start:end]
        blocks.append((label.strip(), start, end, content))

    def data_lines(content):
        return sum(1 for l in content.splitlines()
                   if l.startswith("- ") or (l and not l.startswith("===")))

    seen_labels: dict = {}
    keep_indices = []
    for idx, (label, start, end, content) in enumerate(blocks):
        if label not in seen_labels:
            seen_labels[label] = (idx, data_lines(content))
            keep_indices.append(idx)
        else:
            prev_idx, prev_lines = seen_labels[label]
            curr_lines = data_lines(content)
            logger.info("Duplicate block '%s': first=%d lines, dup=%d lines → dropping dup",
                        label, prev_lines, curr_lines)
            if curr_lines > prev_lines:
                keep_indices[keep_indices.index(prev_idx)] = idx
                seen_labels[label] = (idx, curr_lines)

    if len(keep_indices) == len(blocks):
        return text

    parts = [blocks[i][3].rstrip() for i in sorted(keep_indices)]
    return "\n\n".join(parts)


def clean_answer(text: str) -> str:
    if "===" in text:
        _real = _re.compile(r"(=== [^=\n]+ ===\nResultats \(\d+\):)", _re.MULTILINE)
        _m = _real.search(text)
        if _m:
            text = text[_m.start():]
        else:
            text = text[text.find("==="):]

    lines = text.splitlines()
    cleaned, skip_rest = [], False
    for line in lines:
        low = line.strip().lower()
        if any(low.startswith(p) for p in _LEAK_LINE_PREFIXES):
            skip_rest = True
            continue
        if skip_rest and line.startswith("==="):
            skip_rest = False
        if not skip_rest:
            cleaned.append(line)

    result = "\n".join(cleaned)
    result = _remove_duplicate_blocks(result)
    result = _re.sub(
        r"(?im)^(reponse\s*:|réponse\s*:|donnees\s+live\s*:|puisque la question.*$)",
        "", result
    )

    if "===" in result:
        result_lines = result.splitlines()
        last_block_start = max(
            (i for i, ln in enumerate(result_lines) if ln.startswith("===")),
            default=-1
        )
        if last_block_start >= 0:
            cutoff = len(result_lines)
            for i in range(last_block_start + 1, len(result_lines)):
                ln = result_lines[i]
                if ln.strip() == "":
                    data_seen = any(
                        result_lines[j].startswith("- ") or "|" in result_lines[j]
                        for j in range(last_block_start + 1, i)
                    )
                    if data_seen:
                        cutoff = i
                        break
            result = "\n".join(result_lines[:cutoff])

    result = _re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE CACHE
# ═══════════════════════════════════════════════════════════════════════════════
_EMPLOYEE_CACHE: list[dict] = []


def load_employee_cache(token: str = "") -> None:
    global _EMPLOYEE_CACHE
    if not token:
        print("DEBUG load_employee_cache: token is EMPTY — skipping")
        return
    print(f"DEBUG load_employee_cache: len={len(token)} token={token[:50]}")
    try:
        resp = requests.get(
            f"{API_BASE_URL}/employees",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15
        )
        print(f"DEBUG load_employee_cache: status={resp.status_code}")
        if resp.status_code != 200:
            logger.warning("load_employee_cache: API → %d", resp.status_code)
            return
        rows = resp.json()
        _EMPLOYEE_CACHE = []
        for r in rows:
            fn, ln = r.get("first_name", ""), r.get("last_name", "")
            full   = f"{fn} {ln}".strip()
            full_l = full.lower()
            tris   = {full_l[i:i+3] for i in range(len(full_l)-2)} if len(full_l) > 2 else set()
            _EMPLOYEE_CACHE.append({
                "id":         r["employee_id"],
                "full_name":  full,
                "full_lower": full_l,
                "first":      fn.lower(),
                "last":       ln.lower(),
                "initials":   f"{fn[0]}. {ln}".lower() if fn else "",
                "position":   (r.get("position") or "").lower(),
                "department": (r.get("department") or "").lower(),
                "trigrams":   tris,
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

    scored = sorted([(e, _trigram_score(n, e)) for e in _EMPLOYEE_CACHE],
                    key=lambda x: x[1], reverse=True)
    if scored and scored[0][1] >= threshold:
        best = [e for e, s in scored if s >= threshold]
        if not (len(best) > 1 and scored[1][1] / scored[0][1] > 0.85):
            return scored[0][0]["id"], scored[0][0]["full_name"]

    return None, None


# ═══════════════════════════════════════════════════════════════════════════════
# MANAGER SCOPE HELPER
# ═══════════════════════════════════════════════════════════════════════════════
def _get_supervised_employees(manager_id: str, token: str) -> set:
    try:
        resp = requests.get(
            f"{API_BASE_URL}/employees",
            params={"employee_id": manager_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15
        )
        if resp.status_code != 200:
            logger.warning("_get_supervised_employees: API → %d", resp.status_code)
            return {manager_id}

        data = resp.json()
        mgr  = data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else {})
        sup_str = mgr.get("supervised_employees", "") or ""
        ids = {x.strip() for x in sup_str.replace(";", ",").split(",") if x.strip()}
        ids.add(manager_id)
        logger.info("Manager %s supervises: %s", manager_id, ids)
        return ids

    except Exception as e:
        logger.warning("_get_supervised_employees(%s): %s", manager_id, e)
        return {manager_id}


# ═══════════════════════════════════════════════════════════════════════════════
# PREPROCESS
# ═══════════════════════════════════════════════════════════════════════════════
_NOW_WORDS = [
    "en ce moment", "maintenant", "aujourd'hui",
    "en ce moment-ci", "a present", "à présent", "ce jour", "now", "today",
]
_NOW_WORDS_LEAVE_ONLY = ["actuellement"]

_FORMAT_REQUESTS = [
    "sous forme de tableau", "en tableau", "tableau", "table",
    "sous forme de liste", "en liste", "plus de details", "plus de détails",
    "détails", "details", "resume", "résumé", "synthese", "synthèse", "graphique", "chart",
]
_SUBJECT_INDICATORS = [
    "qui", "quels", "quelles", "quel", "quelle", "combien", "est-ce",
    "y a-t-il", "liste", "donne", "montre", "affiche", "les", "des", "du", "la", "le",
]
_FOLLOWUP_LEAVE = [
    "en ce moment", "maintenant", "actuellement", "aujourd'hui",
    "à présent", "a present", "ce jour", "now", "today",
]
_FOLLOWUP_EXPAND = {
    "conge":    "Quels employés sont en congé en ce moment ? [active_today=true]",
    "absent":   "Quels employés sont absents en ce moment ? [active_today=true]",
    "projet":   "Quels projets sont en cours en ce moment ?",
    "tache":    "Quelles tâches sont en cours en ce moment ?",
    "incident": "Quels incidents sont ouverts en ce moment ?",
}


def preprocess_question(question: str, last_exchange=None):
    q       = question.strip()
    q_lower = q.lower()
    words   = q.split()

    if last_exchange and len(words) <= 6:
        if any(fr in q_lower for fr in _FORMAT_REQUESTS):
            prev_q = last_exchange.get("user", "").strip()
            if prev_q:
                enriched = f"{prev_q} ({q})"
                logger.info("Format follow-up: '%s' → '%s'", q, enriched)
                return enriched, None

    if last_exchange and 1 <= len(words) <= 4:
        has_subject = any(s in q_lower for s in _SUBJECT_INDICATORS)
        has_verb    = any(v in q_lower for v in ["est","sont","a","ont","combien","quels","quel","?"])
        if not has_subject and not has_verb:
            prev_q = last_exchange.get("user", "").strip()
            if prev_q and prev_q.lower() not in q_lower:
                q = f"{prev_q} — {q}"
                q_lower = q.lower()
                words = q.split()

    if any(fw in q_lower for fw in _FOLLOWUP_LEAVE) and len(words) <= 4:
        for kw, expanded in _FOLLOWUP_EXPAND.items():
            if kw in q_lower:
                logger.info("Temporal follow-up: '%s' → '%s'", q, expanded)
                return expanded, None
        return "Quels employés sont en congé en ce moment ? [active_today=true]", None

    _leave_context = any(w in q_lower for w in ["conge", "congé", "absent", "absence", "leave"])
    _strong_now    = any(nw in q_lower for nw in _NOW_WORDS)
    _weak_now      = any(nw in q_lower for nw in _NOW_WORDS_LEAVE_ONLY)

    if (_strong_now or (_weak_now and _leave_context)) and "[active_today" not in q:
        q += " [active_today=true]"
        q_lower = q.lower()

    VERB_IND = ["est","sont","a","ont","quels","quel","combien","donne","montre","liste","quelles","comment","?"]
    if 1 <= len(words) <= 4 and not any(v in q_lower for v in VERB_IND):
        emp_id, full_name = resolve_employee_name(q)
        if emp_id == "AMBIGUOUS":
            return (f"Plusieurs employés correspondent à '{q}' : {full_name}. "
                    f"Pouvez-vous préciser le nom complet ?"), None
        if emp_id:
            expanded = (
                f"Donne-moi le profil complet de {full_name} (employee_id={emp_id}) : "
                f"ses congés, ses tâches en cours et ses informations générales."
            )
            logger.info("Bare name: '%s' → expanded", q)
            return expanded, emp_id

    resolved_id = resolved_name = None
    for n in [3, 2]:
        for i in range(len(words) - n + 1):
            candidate = " ".join(words[i:i+n])
            if len(candidate) < 4:
                continue
            if not any(w[0].isupper() for w in candidate.split() if w):
                continue
            emp_id, full_name = resolve_employee_name(candidate)
            if emp_id and emp_id != "AMBIGUOUS":
                resolved_id   = emp_id
                resolved_name = full_name
                break
        if resolved_id:
            break

    if not resolved_id:
        return q, None

    enriched = f"{q} [employee_id={resolved_id}, nom={resolved_name}]"
    logger.info("Employee resolved: %s → %s", resolved_name, resolved_id)
    return enriched, resolved_id


# ═══════════════════════════════════════════════════════════════════════════════
# LLM REFUSAL DETECTION  (Fix 1 — v28)
# ═══════════════════════════════════════════════════════════════════════════════
_REFUSAL_PHRASES = (
    "je suis incapable",
    "je ne peux pas",
    "je n'ai pas accès",
    "je n'ai pas acces",
    "il m'est impossible",
    "je ne suis pas en mesure",
    "je n'ai pas trouvé",
    "je n'ai pas trouve",
    "données non disponibles",
    "donnees non disponibles",
    "je n'ai aucune information",
    "je n'ai aucune donnee",
    "je n'ai aucune donnée",
    "impossible de récupérer",
    "impossible de recuperer",
    "je ne dispose pas",
    "ces informations ne sont pas disponibles",
    "cette information n'est pas disponible",
)

def _is_llm_refusal(answer: str, live_context: str) -> bool:
    """Returns True when the LLM produced a refusal but live data is actually present."""
    answer_lower = answer.lower()
    has_live_data = "===" in live_context and "Resultats (" in live_context
    is_refusal    = (
        any(p in answer_lower for p in _REFUSAL_PHRASES)
        and "===" not in answer
    )
    return is_refusal and has_live_data


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

    # ── FIX: handle bare "fichier" message ──────────────────────────────────
    _FILE_ONLY_MSGS = {"fichier", "file", "document", "pièce jointe", "piece jointe", "attachment"}
    if question.strip().lower() in _FILE_ONLY_MSGS:
        return (
            "J'ai bien reçu votre fichier. Cependant, je ne peux pas lire "
            "directement les fichiers joints pour l'instant.\n\n"
            "Si vous souhaitez que j'analyse son contenu, veuillez copier-coller "
            "le texte du fichier dans le chat."
        )

    # Step 0 : Preprocess
    question, _resolved_id = preprocess_question(question, last_exchange=last_exchange)
    logger.info("Processed question: %s (resolved_id=%s)", question, _resolved_id)
    q_lower = question.lower()

    # Sécurité manager
    if user_role == "manager" and _resolved_id is None:
        _name_words = [w for w in question.split()
                       if len(w) > 2 and w[0].isupper() and w.isalpha()
                       and w.lower() not in ["liste","montre","donne","affiche","quels",
                                              "quelles","quel","quelle","combien","comment",
                                              "quel","quels","qui","les","des","mes","mon",
                                              "nos","tout","tous","toutes","avec","pour",
                                              "dans","sur","par","son","ses","leur","leurs"]]
        _person_keywords = ["congé","conge","tâche","tache","profil","absent",
                            "performance","salary","salaire","jours","heures"]
        if (len(_name_words) >= 2
                and any(kw in q_lower for kw in _person_keywords)):
            logger.warning("Manager %s asked about unknown person '%s' → access denied",
                           user_id, " ".join(_name_words))
            return "⛔ Accès refusé : cet employé n'appartient pas à votre équipe."

    # #H2 — Glossaire
    if is_definition_question(q_lower):
        definition = handle_definition_question(q_lower)
        if definition:
            logger.info("#H2 Glossary answer")
            return definition

    # ── FIX 7 (v30): Policy question → RAG only, skip planner entirely ──────
    if is_policy_question(q_lower):
        logger.info("#H5 Policy question → RAG only (skipping planner + all API calls)")
        return _ask_llm_rag_only(question)

    # #H4 — Questions procédurales → RAG documentaire pur
    if is_procedural_question(q_lower):
        logger.info("#H4 Procedural → RAG doc-only")
        raw_chunks  = doc_retriever.invoke(question)
        proc_chunks = _rerank_doc_chunks(raw_chunks, question, top_k=6)
        for i, ch in enumerate(proc_chunks):
            logger.info("#H4 chunk[%d]: file=%s preview=%r",
                        i, ch.metadata.get("filename","?"), ch.page_content[:80])
        doc_ctx = "\n\n".join(
            f"[{ch.metadata.get('category','')} — {ch.metadata.get('filename','doc')}]\n"
            f"{ch.page_content}"
            for ch in proc_chunks
        )
        if not doc_ctx.strip():
            return "Je n'ai pas trouvé de documentation sur ce sujet."
        result = rag_doc_chain.invoke({"question": question, "doc_context": doc_ctx})
        return clean_answer(str(result))

    # Step 1 : Retrieve API docs + doc chunks
    api_docs   = api_retriever.invoke(question)
    doc_chunks = doc_retriever.invoke(question)

    role_allowed = ROLE_ALLOWED_ENDPOINTS.get(user_role, [])

    raw_endpoints = []
    for d in api_docs:
        ep = d.metadata.get("endpoint")
        if ep and ep in role_allowed:
            raw_endpoints.append(ep)
    available_endpoints = list(dict.fromkeys(raw_endpoints))
    for ep in role_allowed:
        if ep not in available_endpoints:
            available_endpoints.append(ep)

    logger.info("Available endpoints (role=%s): %s", user_role, available_endpoints)
    logger.info("Doc chunks: %d", len(doc_chunks))

    # Step 2 : LLM Planner
    plan_raw = planner_chain.invoke({
        "question":            question,
        "user_role":           user_role,
        "user_id":             user_id,
        "available_endpoints": available_endpoints,
    })
    plan = parse_llm_plan(str(plan_raw))
    logger.info("LLM Plan reasoning: %s", plan.get("reasoning", "—"))
    logger.info("LLM Plan endpoints: %s", plan.get("endpoints", []))

    if not plan.get("endpoints"):
        fallback = _apply_fallback_plan(q_lower, role_allowed)
        if fallback:
            plan["endpoints"] = fallback
            plan["reasoning"] = "fallback-deterministe"
            logger.info("Plan remplacé par fallback: %s", fallback)

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
    if len(deduped) > 6:
        logger.warning("Planner over-fetched %d endpoints → tronqué à 6", len(deduped))
        deduped = deduped[:6]
    plan["endpoints"] = deduped

    for item in plan.get("endpoints", []):
        if item.get("endpoint") == "/tasks":
            f = item.get("filters", {})
            if f.get("priority") == "Critical" and "status" in f:
                f.pop("status")
                logger.info("POST-PLAN: status retiré de /tasks Critical — géré par Python")

    _ANALYTICAL_WORDS = ["quel","quels","meilleur","pire","top","classement",
                         "plus","moins","combien","comparer","performance",
                         "retard","bloqué","critique","risque","depass"]
    _LISTING_WORDS    = ["liste","tous","toutes","affiche","montre","donne","all","complet"]
    is_analytical = any(w in q_lower for w in _ANALYTICAL_WORDS)
    is_listing    = any(w in q_lower for w in _LISTING_WORDS)
    n_endpoints   = len(plan["endpoints"])
    TOTAL_ROW_BUDGET = 60
    if is_analytical:
        per_ep_limit = max(5, TOTAL_ROW_BUDGET // max(n_endpoints, 1))
    elif is_listing and n_endpoints == 1:
        per_ep_limit = 25
    else:
        per_ep_limit = max(8, TOTAL_ROW_BUDGET // max(n_endpoints, 1))

    _ALWAYS_FULL = {"/stats/summary", "/stats/tasks", "/stats/by-manager",
                    "/tasks/by-manager", "/notifications"}
    _KPI_ROW_CAP  = 15
    _KPI_CROSS_CAP = 25
    _is_cross_query = any(w in q_lower for w in ["et ont", "et qui ont", "ayant", "avec des incidents", "ont des incidents"])
    for item in plan["endpoints"]:
        ep = item.get("endpoint","")
        if ep not in _ALWAYS_FULL:
            item["_row_limit"] = per_ep_limit
        if ep == "/kpis":
            cap = _KPI_CROSS_CAP if _is_cross_query else _KPI_ROW_CAP
            item["_row_limit"] = min(item.get("_row_limit", per_ep_limit), cap)

    logger.info("Context budget: %d endpoints, per_ep_limit=%d (analytical=%s, listing=%s)",
                n_endpoints, per_ep_limit, is_analytical, is_listing)
    logger.info("Final plan: %s", plan)

    _supervised_ids: set | None = None
    if user_role == "manager":
        _supervised_ids = _get_supervised_employees(user_id, token)
        logger.info("Manager %s scope: %s", user_id, _supervised_ids)

    if user_role == "manager" and _resolved_id is None:
        for item in plan.get("endpoints", []):
            f = item.get("filters", {})
            if (item.get("endpoint") == "/tasks"
                    and f.get("assigned_to") == user_id):
                f.pop("assigned_to")
                logger.info("POST-PLAN: assigned_to=%s retiré de /tasks pour manager", user_id)
            if (item.get("endpoint") in ("/leave-requests", "/timesheets", "/employees")
                    and f.get("employee_id") == user_id
                    and not any(w in q_lower for w in ["moi", "mes conge", "mon conge",
                                                        "ma fiche", "mes heures", "mon profil"])):
                f.pop("employee_id")
                logger.info("POST-PLAN: employee_id=%s retiré de %s pour manager",
                            user_id, item.get("endpoint"))

    if user_role == "manager" and _supervised_ids is not None:
        for item in plan.get("endpoints", []):
            f = item.get("filters", {})
            if "supervised_by" in f:
                f.pop("supervised_by")
                item["_team_filter"] = True
                logger.info("POST-PLAN: supervised_by virtuel intercepté sur %s → _team_filter",
                            item.get("endpoint",""))

    _CLIENT_WORDS = ["client", "clients", "mes clients", "liste clients", "lister clients"]
    if any(w in q_lower for w in _CLIENT_WORDS):
        for item in plan.get("endpoints", []):
            if item.get("endpoint") == "/projects":
                item["filters"]["_client_view"] = True
                logger.info("POST-PLAN: client question détectée → _client_view sur /projects")

    # ═══════════════════════════════════════════════════════════════════════════
    # Step 3 : Exécuter — HTTP calls vers FastAPI
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
                eid, ename = resolve_employee_name(str(raw_eid))
                if eid and eid != "AMBIGUOUS":
                    filters.pop("employee_id", None)
                    filters.pop("assigned_to", None)
                    filters[id_key] = eid
                    logger.info("Corrected person filter '%s' → %s on %s", raw_eid, eid, endpoint)
                else:
                    filters.pop("employee_id", None)
                    filters.pop("assigned_to", None)
                    logger.warning("Could not resolve person filter '%s' → dropped", raw_eid)
            elif not raw_eid and _resolved_id:
                filters[id_key] = _resolved_id
                logger.info("Propagated resolved id=%s → %s (key=%s)",
                            _resolved_id, endpoint, id_key)

        if user_role == "manager" and _supervised_ids is not None:
            id_key  = "assigned_to" if endpoint == "/tasks" else "employee_id"
            queried_id = filters.get(id_key) or filters.get("employee_id") or filters.get("assigned_to")
            if queried_id and queried_id != user_id:
                if queried_id not in _supervised_ids:
                    logger.warning(
                        "MANAGER SCOPE VIOLATION: %s (%s) tried to access data for %s",
                        user_name, user_id, queried_id
                    )
                    live_parts.append(
                        f"=== ACCÈS REFUSÉ ===\n"
                        f"Vous n'êtes pas autorisé à consulter les données de l'employé {queried_id}.\n"
                    )
                    continue

        active_today         = filters.pop("active_today", False)
        delayed_filter       = filters.pop("delayed", None)
        client_view          = filters.pop("_client_view", False)
        requested_risk_level = filters.get("risk_level", None)

        data = call_api(endpoint, filters, token)

        if item.get("_team_filter") and user_role == "manager" and _supervised_ids is not None:
            team_ids = _supervised_ids - {user_id}
            before_tf = len(data) if isinstance(data, list) else 0
            if isinstance(data, list):
                id_key_tf = "assigned_to" if endpoint == "/tasks" else "employee_id"
                data = [r for r in data if r.get(id_key_tf, "") in team_ids]
            logger.info("Team filter (%s): %d → %d (manager exclu)", endpoint, before_tf, len(data))

        if endpoint == "/kpis" and isinstance(data, list):
            seen_proj: dict = {}
            for r in data:
                pid = r.get("project_id") or r.get("project_name", "")
                if not pid:
                    continue
                r_delay   = r.get("schedule_variance_days") or 0
                existing  = seen_proj.get(pid)

                if delayed_filter:
                    if r_delay <= 0:
                        continue
                    if existing is None:
                        seen_proj[pid] = r
                    elif r_delay > (existing.get("schedule_variance_days") or 0):
                        seen_proj[pid] = r
                else:
                    if existing is None:
                        seen_proj[pid] = r
                    elif abs(r_delay) > abs(existing.get("schedule_variance_days") or 0):
                        seen_proj[pid] = r

            before_dedup = len(data)
            data = list(seen_proj.values())

            if delayed_filter or requested_risk_level:
                data.sort(key=lambda r: -(r.get("schedule_variance_days") or 0))
            else:
                data.sort(key=lambda r: -abs(r.get("schedule_variance_days") or 0))

            logger.info("KPIs dedup (risk_level=%s, delayed=%s): %d → %d projets uniques",
                        requested_risk_level, delayed_filter, before_dedup, len(data))

        if delayed_filter and endpoint == "/kpis" and isinstance(data, list):
            before = len(data)
            data = [r for r in data if (r.get("schedule_variance_days") or 0) > 0]
            logger.info("delayed filter final: %d → %d projets en retard", before, len(data))

        if active_today and isinstance(data, list):
            today = _date.today().isoformat()
            data  = [r for r in data
                     if r.get("start_date","") <= today <= r.get("end_date","9999")]
            logger.info("active_today filter (%s): %d résultats", today, len(data))

        if endpoint == "/tasks" and "non termin" in q_lower and isinstance(data, list):
            before_nt = len(data)
            data = [r for r in data if r.get("status", "") != "Done"]
            logger.info("Filtre 'non terminées': %d → %d (Done exclus)", before_nt, len(data))

        row_limit = item.get("_row_limit")
        if row_limit and isinstance(data, list):
            data = data[:row_limit]

        if (endpoint == "/leave-requests" and _resolved_id and
                any(w in q_lower for w in ["combien de jours","nombre de jours","total","bilan","conge","congé","pris"])):
            filters_bilan = {k: v for k, v in filters.items() if k != "status"}
            data = call_api(endpoint, filters_bilan, token)
            logger.info("FIX bilan: appel sans filtre status pour avoir Approved+Pending")

        if (endpoint == "/leave-requests" and _resolved_id and
                any(w in q_lower for w in ["combien de jours","nombre de jours","total","bilan"])):
            if isinstance(data, list):
                approved = [r for r in data if r.get("status","").lower() == "approved"]
                pending  = [r for r in data if r.get("status","").lower() == "pending"]
                tot_a    = sum(r.get("total_days",0) or 0 for r in approved)
                tot_p    = sum(r.get("total_days",0) or 0 for r in pending)
                emp_name = data[0].get("employee_name", _resolved_id) if data else _resolved_id
                if not data:
                    live_parts.append(f"=== LEAVE-REQUESTS ===\nResultats (0): Aucun conge trouve pour {emp_name}.\n")
                    continue
                sorted_data = approved + pending
                block = format_endpoint_data("/leave-requests", sorted_data, {})
                summary = f"Bilan {emp_name} : {tot_a}j approuves"
                if pending:
                    summary += f" | {tot_p}j en attente"
                block = block.replace("=== LEAVE-REQUESTS ===", f"=== LEAVE-REQUESTS ===\n{summary}")
                live_parts.append(block)
                continue

        if data:
            if client_view:
                filters["_client_view"] = True
            live_parts.append(format_endpoint_data(endpoint, data, filters))
        else:
            lbl = endpoint.strip("/").replace("/", "-").upper()
            live_parts.append(
                f"=== {lbl} ===\n"
                f"Resultats (0): Aucun resultat pour filtres: {filters}\n"
            )

    if any(w in q_lower for w in ["tâche", "tache", "task"]):
        _task_parts  = [p for p in live_parts if p.startswith("=== TASKS")]
        _other_parts = [p for p in live_parts if not p.startswith("=== TASKS")]
        live_parts = _task_parts + _other_parts
    live_context = "\n".join(live_parts) if live_parts else "Aucune donnee live — question documentaire."

    # ── Cross-query : KPIs en retard ET incidents ─────────────────────────────
    _is_cross_kpi_issue = any(w in q_lower for w in [
        "et ont", "et qui ont", "ayant", "avec des incidents", "ont des incidents", "et ont des",
        "incidents critical", "incidents critiques", "incidents high", "incidents élevés",
        "incidents elevés", "incidents élevés", "critical ou high", "critiques ou high",
        "critiques ou hauts", "critical ou hauts", "critical ou élevés",
        "retard et ont", "retard et", "en retard et",
    ]) and any(w in q_lower for w in ["incident", "issue", "problème", "probleme"])

    if _is_cross_kpi_issue:
        _kpi_data_raw = call_api("/kpis", {}, token)
        _kpi_data_raw = [r for r in _kpi_data_raw if (r.get("schedule_variance_days") or 0) > 0]
        seen_p: dict = {}
        for r in _kpi_data_raw:
            pid = r.get("project_id","")
            if pid not in seen_p or (r.get("schedule_variance_days",0) > seen_p[pid].get("schedule_variance_days",0)):
                seen_p[pid] = r
        _kpi_data_raw = sorted(seen_p.values(), key=lambda r: -(r.get("schedule_variance_days") or 0))

        _issue_filters: dict = {}
        if "critical" in q_lower and "high" not in q_lower:
            _issue_filters["severity"] = "Critical"
        elif "high" in q_lower and "critical" not in q_lower:
            _issue_filters["severity"] = "High"
        _issue_data_raw = call_api("/issues", _issue_filters, token)

        logger.info("Cross KPI/Issues: %d delayed projects, %d issues (filters=%s)",
                    len(_kpi_data_raw), len(_issue_data_raw), _issue_filters)

        if _kpi_data_raw and _issue_data_raw:
            issue_pids = {r.get("project_id","") for r in _issue_data_raw if r.get("project_id")}
            crossed = [r for r in _kpi_data_raw if r.get("project_id","") in issue_pids]
            logger.info("Cross-filter KPI/Issues: %d → %d avec incidents",
                        len(_kpi_data_raw), len(crossed))
            if crossed:
                crossed_block = format_endpoint_data("/kpis", crossed, {})
                crossed_block = crossed_block.replace("=== KPIS ===", "=== KPIS (croisé avec incidents) ===")
                other_parts = [p for p in live_parts
                               if not p.startswith("=== KPIS") and not p.startswith("=== ISSUES")]
                live_context = "\n".join(other_parts + [crossed_block])

    # ── Cross-query : Managers avec tâches bloquées ET projets en retard ───────
    _CROSS_MANAGER_BLOCKED_KWS  = ["tâches bloquées", "taches bloquées", "taches bloquees",
                                    "tâches bloquées", "bloquées et", "bloquées"]
    _CROSS_MANAGER_DELAYED_KWS  = ["projets en retard", "retard"]
    _CROSS_MANAGER_KWS_TRIGGER  = ["manager", "managers", "responsable", "responsables",
                                    "chef", "chefs"]
    _is_cross_manager_delayed = (
        any(w in q_lower for w in _CROSS_MANAGER_BLOCKED_KWS)
        and any(w in q_lower for w in _CROSS_MANAGER_DELAYED_KWS)
        and any(w in q_lower for w in _CROSS_MANAGER_KWS_TRIGGER)
    )

    if _is_cross_manager_delayed:
        logger.info("Cross-filter Manager/Delayed triggered")
        all_tasks_mgr = call_api("/tasks", {}, token)
        all_kpis_delayed = call_api("/kpis", {}, token)
        delayed_pids = {
            r.get("project_id","") for r in all_kpis_delayed
            if (r.get("schedule_variance_days") or 0) > 0 and r.get("project_id")
        }
        mgr_data_raw = _compute_virtual_endpoint("/tasks/by-manager", token)

        all_employees_mgr = call_api("/employees", {}, token)
        managers_map = {e["employee_id"]: e for e in all_employees_mgr
                        if e.get("role") == "manager"}
        emp_to_mgr_map: dict = {}
        for mid, mgr in managers_map.items():
            sup = mgr.get("supervised_employees") or ""
            for eid in [x.strip() for x in sup.replace(";", ",").split(",") if x.strip()]:
                emp_to_mgr_map[eid] = mid
        mgr_delayed_pids: dict = {}
        for t in all_tasks_mgr:
            aid = t.get("assigned_to","")
            pid = t.get("project_id","")
            mid = emp_to_mgr_map.get(aid) or (aid if aid in managers_map else None)
            if mid and pid in delayed_pids:
                mgr_delayed_pids.setdefault(mid, set()).add(pid)

        mgr_stats = mgr_data_raw if isinstance(mgr_data_raw, list) else []

        crossed_mgrs = [
            r for r in mgr_stats
            if r.get("blocked", 0) > 0
            and r.get("manager_id","") in mgr_delayed_pids
        ]
        lines_mgr = []
        for r in crossed_mgrs:
            mid = r.get("manager_id","")
            n_delayed = len(mgr_delayed_pids.get(mid, set()))
            lines_mgr.append(
                f"- {r.get('manager_name','')} ({r.get('department','')}) | "
                f"Total: {r.get('total_tasks',0)} | Bloques: {r.get('blocked',0)} | "
                f"Critiques: {r.get('critical_tasks',0)} | "
                f"Projets en retard: {n_delayed} | Avancement: {r.get('done_pct',0)}%"
            )
        logger.info("Cross-filter Manager/Delayed: %d managers with blocked + delayed projects",
                    len(crossed_mgrs))
        if lines_mgr:
            _header_mgr = ("=== MANAGERS (bloques + projets en retard) ===\n"
                           "Resultats (" + str(len(crossed_mgrs)) + "):\n")
            crossed_block_mgr = _header_mgr + "\n".join(lines_mgr)
            other_parts = [p for p in live_parts
                           if not p.startswith("=== TASKS-BY-MANAGER")
                           and not p.startswith("=== KPIS")]
            live_context = "\n".join(other_parts + [crossed_block_mgr])
        else:
            live_context = (
                "=== MANAGERS (bloques + projets en retard) ===\n"
                "Resultats (0): Aucun manager n a simultanement des taches bloquees "
                "et des projets en retard.\n"
            )

    # ── Cross-query : Employés avec tâches critiques ET en congé ─────────────
    _CROSS_CRITICAL_KWS = ["taches critiques", "tâches critiques"]
    _CROSS_LEAVE_KWS    = [
        "en conge", "en congé", "sont en conge", "sont en congé",
        "conge approuve", "congé approuvé", "absent", "absence"
    ]
    _is_cross_emp_leave = (
        any(w in q_lower for w in _CROSS_CRITICAL_KWS)
        and any(w in q_lower for w in _CROSS_LEAVE_KWS)
    )

    if _is_cross_emp_leave:
        today = _date.today().isoformat()
        all_critical_tasks = call_api("/tasks", {"priority": "Critical"}, token)
        critical_emp_ids = {r.get("assigned_to","") for r in all_critical_tasks if r.get("assigned_to")}
        all_leaves = call_api("/leave-requests", {"status": "Approved"}, token)
        on_leave_today = [
            r for r in all_leaves
            if r.get("start_date","") <= today <= r.get("end_date","9999")
        ]
        on_leave_ids = {r.get("employee_id","") for r in on_leave_today if r.get("employee_id")}
        both_ids = critical_emp_ids & on_leave_ids

        logger.info("Cross-filter Emp/Leave: %d avec tâches critiques, %d en congé → %d intersection",
                    len(critical_emp_ids), len(on_leave_ids), len(both_ids))

        if both_ids:
            all_employees = call_api("/employees", {}, token)
            matched_emps = [e for e in all_employees if e.get("employee_id","") in both_ids]
            lines = []
            for emp in matched_emps:
                eid  = emp.get("employee_id","")
                name = f"{emp.get('first_name','')} {emp.get('last_name','')}".strip()
                dept = emp.get("department","")
                pos  = emp.get("position","")
                emp_tasks = [t for t in all_critical_tasks if t.get("assigned_to") == eid]
                task_titles = ", ".join(t.get("title","?") for t in emp_tasks[:3])
                emp_leave = next((l for l in on_leave_today if l.get("employee_id") == eid), None)
                leave_info = ""
                if emp_leave:
                    leave_info = f"{emp_leave.get('leave_type','')} du {emp_leave.get('start_date','')} au {emp_leave.get('end_date','')} ({emp_leave.get('total_days','')}j)"
                lines.append(
                    f"- {name} | Dept: {dept} | Poste: {pos} | "
                    f"Taches critiques: {len(emp_tasks)} ({task_titles}) | "
                    f"Conge: {leave_info}"
                )
            if lines:
                crossed_block = (
                    f"=== EMPLOYEES (tâches critiques + en congé) ===\n"
                    f"Resultats ({len(matched_emps)}):\n"
                    + "\n".join(lines)
                )
                other_parts = [p for p in live_parts
                               if not p.startswith("=== EMPLOYEES")
                               and not p.startswith("=== TASKS")
                               and not p.startswith("=== LEAVE")]
                live_context = "\n".join(other_parts + [crossed_block])
        else:
            live_context = "=== EMPLOYEES (tâches critiques + en congé) ===\nResultats (0): Aucun employé n'a simultanément des tâches critiques et un congé approuvé actif.\n"

    if "=== ACCÈS REFUSÉ ===" in live_context:
        if _resolved_id is None:
            return "❓ Je n'ai pas pu identifier cet employé avec certitude. Pouvez-vous préciser le nom complet ?"
        return "⛔ Accès refusé : vous pouvez uniquement accéder aux données de votre propre équipe."

    _DATA_WORDS = [
        "employe", "employé", "tache", "tâche", "projet", "conge", "congé",
        "liste", "tous", "toutes", "affiche", "montre", "donne", "incident",
        "equipement", "équipement", "fournisseur", "kpi", "statistique",
        "client", "clients"
    ]
    if (live_context == "Aucune donnee live — question documentaire."
            and any(w in q_lower for w in _DATA_WORDS)):
        logger.warning("Garde-fou anti-hallucination : pas de données live pour une question de données")
        return (
            "Je suis votre assistant ERP BTP. 🏗️\n\n"
            "Cette demande est hors de mon périmètre (météo, données externes, etc.).\n\n"
            "Je peux vous aider sur : projets, KPIs, employés, tâches, "
            "congés, incidents, équipements, fournisseurs et procédures internes."
        )

    # Step 4 : Documentary context
    doc_chunks_reranked = _rerank_doc_chunks(doc_chunks, question, top_k=3)
    doc_parts = [
        f"[{ch.metadata.get('category','')} — {ch.metadata.get('filename','doc')}]\n{ch.page_content}"
        for ch in doc_chunks_reranked
    ]
    doc_context = "\n\n".join(doc_parts) if doc_parts else "Aucune documentation pertinente."

    # Step 5 : LLM génère la réponse finale
    result = answer_chain.invoke({
        "question":     question,
        "live_context": live_context,
        "doc_context":  doc_context,
        "user_role":    user_role,
        "user_name":    user_name,
    })

    answer = clean_answer(str(result))
    answer = _re.sub(r'\[employee_id=E\d+[^\]]*\]', '', answer).strip()

    _live_labels      = set(_re.findall(r"=== ([^=\n]+ ===)", live_context))
    _answer_labels    = set(_re.findall(r"=== ([^=\n]+ ===)", answer))
    _hallucinated_labels = _answer_labels - _live_labels - {"ACCÈS REFUSÉ ==="}

    if _hallucinated_labels:
        logger.warning("LLM hallucinated labels %s not in live_context → flagged",
                       _hallucinated_labels)

    _EMPTY_ANSWER_STRINGS = {
        "aucune donnée disponible pour cette requête.",
        "aucune donnée disponible — impossible de récupérer les informations demandées.",
        "je n'ai pas trouvé de documentation sur ce sujet.",
        "",
    }

    _answer_useless = (
        not answer
        or answer.strip().lower() in _EMPTY_ANSWER_STRINGS
        or ("aucune" in answer.lower() and "===" not in answer)
        or bool(_hallucinated_labels)
        or _is_llm_refusal(answer, live_context)
    )

    if _answer_useless and "=== " in live_context and "Resultats (" in live_context:
        logger.warning("LLM answer empty/useless/refusal — falling back to live_context directly")
        _blocks = _re.findall(
            r"=== [^=\n]+ ===\nResultats \(\d+\):.*?(?=\n=== |$)",
            live_context, _re.DOTALL
        )
        if _blocks:
            answer = "\n\n".join(b.strip() for b in _blocks)
        else:
            answer = live_context.strip()

    if not answer or answer.strip().lower() in _EMPTY_ANSWER_STRINGS:
        answer = (
            "Je suis votre assistant ERP BTP. 🏗️\n\n"
            "Je n'ai pas pu récupérer cette information — "
            "elle est probablement hors de mon périmètre "
            "(météo, actualités, données externes, etc.).\n\n"
            "Je peux vous aider sur :\n"
            "  • 📁 Projets & KPIs\n"
            "  • 👷 Employés & équipes\n"
            "  • ✅ Tâches & incidents\n"
            "  • 🏖️ Congés & absences\n"
            "  • 🔧 Équipements & fournisseurs\n"
            "  • 📋 Procédures & politiques internes"
        )
        logger.info("Fallback final déclenché — réponse hors périmètre")

    logger.info("=== RAW ANSWER ===\n%s\n==================", repr(answer))
    return answer