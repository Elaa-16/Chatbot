"""
seed_api_docs.py
~~~~~~~~~~~~~~~~
Rebuilds the 'erp_apis' collection in ChromaDB with rich, semantically
dense API documentation chunks.

WHY THIS MATTERS
----------------
The RAG retriever finds endpoints by cosine similarity between the user's
question and the API doc chunks. If a chunk only says:

    "/leave-requests — filters: status, employee_id"

…it ranks low for "combien de jours a pris Nadia Hamdi" because there is
almost no semantic overlap.

A rich chunk that says:

    "Use /leave-requests to answer: who is absent, how many days off has
     an employee taken, pending approvals, sick/annual/emergency leave…"

…ranks high for many more natural-language questions.

USAGE
-----
    python seed_api_docs.py

Run once after any change to API_DOCS below, or when retrieval quality
degrades. The script drops and recreates the collection cleanly.
"""

from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

CHROMA_DIR        = "./erp_chroma_db"
COLLECTION_NAME   = "erp_apis"
EMBEDDING_MODEL   = "mxbai-embed-large"

# ── Rich API documentation chunks ────────────────────────────────────────────
# Each entry has:
#   endpoint : exact path used as filter key in the planner
#   category : "api" — used by api_retriever
#   content  : dense natural-language description with synonyms and example
#              questions the user might ask — this is what gets embedded
#
# RULE: write content AS IF you are answering "when should the planner
# call this endpoint?" Include every paraphrase a CEO/manager/RH/employee
# might use. More synonyms = better recall.

API_DOCS = [
    {
        "endpoint": "/employees",
        "content": """
Use /employees to answer any question about the list of staff, team members,
or personnel. Examples:
- "Liste tous les employés"
- "Qui travaille dans l'entreprise ?"
- "Quels sont les membres de l'équipe ?"
- "Employés du département Finance"
- "Qui a le rôle manager ?"
- "Affiche le profil de [nom]"
- "Combien d'employés y a-t-il ?"
Available filters: department (Finance, Projects, HR, Operations, IT, Executive),
role (ceo, manager, employee, rh).
Returns: employee_id, first_name, last_name, position, department, role.
"""
    },
    {
        "endpoint": "/leave-requests",
        "content": """
Use /leave-requests to answer any question about absences, leave, days off,
congés, vacances. Examples:
- "Quels employés sont en congé en ce moment ?"
- "Qui est absent ?"
- "Combien de jours de congé a pris [nom] ?"
- "Congés approuvés / en attente / refusés"
- "Demandes de congé en attente de validation"
- "Congés urgents (Emergency)"
- "Congé maladie, congé annuel, congé personnel"
- "Est-ce que [nom] est en congé ?"
- "Liste des absences de l'équipe"
Available filters: status (Approved, Pending, Rejected), employee_id.
Returns: employee_name, leave_type, start_date, end_date, total_days, status, reason.
"""
    },
    {
        "endpoint": "/tasks",
        "content": """
Use /tasks to answer questions about individual tasks, work items, assignments.
Examples:
- "Quelles tâches sont bloquées ?"
- "Tâches critiques non terminées"
- "Mes tâches en cours"
- "Tâches assignées à [employé]"
- "Tâches en retard"
- "Tâches à faire (Todo)"
- "Quelles tâches sont en cours ?"
- "Tâches de haute priorité"
Available filters: status (Todo, In Progress, Done, Blocked),
priority (Critical, High, Medium, Low), project_id, assigned_to.
Returns: task_id, title, status, priority, due_date, employee_name, project_name.
"""
    },
    {
        "endpoint": "/tasks/by-manager",
        "content": """
Use /tasks/by-manager to compare managers by task statistics — blocked tasks,
critical tasks, total tasks, completion rate. Examples:
- "Quel manager a le plus de tâches bloquées ?"
- "Classement des managers par performance"
- "Quel manager a le plus de tâches critiques dans son équipe ?"
- "Charge de travail par manager"
- "Comparaison des managers"
- "Quel manager est le moins performant ?"
- "Tâches bloquées par équipe"
No filters needed — returns all managers.
Returns: manager_name, department, total_tasks, blocked, critical_tasks,
in_progress, done, high_tasks.
"""
    },
    {
        "endpoint": "/stats/by-manager",
        "content": """
Use /stats/by-manager for a performance ranking of managers including blocked
tasks, open critical tasks, completion stats, and average project progress.
Examples:
- "Classement des managers par performance"
- "Quel manager a le meilleur taux de complétion ?"
- "Manager le moins performant"
- "Statistiques par manager"
- "Performance globale des chefs d'équipe"
- "Qui gère le mieux son équipe ?"
No filters needed — returns all managers with aggregated stats.
Returns: manager_name, department, total_tasks, blocked_tasks, done_tasks,
open_critical, total_projects, avg_completion.
"""
    },
    {
        "endpoint": "/projects",
        "content": """
Use /projects to answer questions about project list, status, budget, location,
and overall progress. Examples:
- "Combien de projets sont en cours ?"
- "Projets terminés"
- "Projets en phase de planification"
- "Liste de tous les projets"
- "Quel projet a le meilleur avancement ?"
- "Budget des projets"
- "Projets à Tunis / Sfax / Sousse"
Available filters: status (In Progress, Completed, Planning).
Returns: project_id, project_name, status, budget_eur, actual_cost_eur,
completion_percentage, location, end_date.
"""
    },
    {
        "endpoint": "/kpis",
        "content": """
Use /kpis for project performance indicators: schedule variance (delays),
budget variance, CPI, SPI, risk level, quality score. Examples:
- "Quels projets sont en retard ?"
- "Projets qui dépassent leur budget"
- "Projets à risque élevé"
- "Pire CPI / pire SPI"
- "Projets avec retard de planning"
- "Indicateurs de performance des projets"
- "Projets en avance sur le planning"
- "Analyse financière des projets"
- "Quel projet est le plus en difficulté ?"
Available filters: delayed (true = schedule_variance_days > 0),
risk_level (High, Medium, Low), project_id.
Returns: project_name, schedule_variance_days, budget_variance_percentage,
cost_performance_index (CPI), schedule_performance_index (SPI),
risk_level, completion_percentage.
"""
    },
    {
        "endpoint": "/issues",
        "content": """
Use /issues for construction site problems, incidents, safety alerts, quality
defects, technical breakdowns. Examples:
- "Quels incidents sont ouverts ?"
- "Incidents critiques sur les chantiers"
- "Problèmes de sécurité non résolus"
- "Incidents de qualité"
- "Pannes d'équipements signalées"
- "Fissures, accidents, retards signalés"
- "Incidents High ou Critical"
- "Y a-t-il des alertes sécurité ?"
Available filters: severity (Critical, High, Medium, Low),
status (Open, In Progress, Resolved, Closed),
category (Safety, Quality, Delay, Budget, Technical, Other),
project_id.
Returns: issue_id, title, severity, category, status, project_name,
created_date, reported_by_name.
"""
    },
    {
        "endpoint": "/stats/summary",
        "content": """
Use /stats/summary for a global overview of the company: total projects,
in-progress vs completed, total budget, actual cost, average completion.
Examples:
- "Résumé global de l'entreprise"
- "Statistiques globales"
- "Vue d'ensemble de tous les projets"
- "Budget total de l'entreprise"
- "Tableau de bord exécutif"
- "Combien de projets en tout ?"
- "État général de l'entreprise"
No filters. Returns: total_projects, in_progress, completed, planning,
total_budget_eur, total_actual_cost_eur, avg_completion_pct.
"""
    },
    {
        "endpoint": "/stats/tasks",
        "content": """
Use /stats/tasks for aggregated task counts across all statuses and priorities.
Examples:
- "Statistiques des tâches"
- "Combien de tâches bloquées au total ?"
- "Répartition des tâches par statut"
- "Combien de tâches critiques y a-t-il ?"
- "Vue globale des tâches"
No filters. Returns: total_tasks, todo, in_progress, done, blocked,
critical, high.
"""
    },
    {
        "endpoint": "/timesheets",
        "content": """
Use /timesheets for hours worked, time tracking, work logs per employee
or project. Examples:
- "Combien d'heures a travaillé [nom] ?"
- "Feuilles de temps de l'équipe"
- "Heures travaillées sur le projet X"
- "Total d'heures ce mois"
- "Qui a travaillé le plus d'heures ?"
Available filters: project_id, employee_id (injected automatically by role).
Returns: employee_name, project_name, date, hours_worked, task_description.
"""
    },
    {
        "endpoint": "/equipment",
        "content": """
Use /equipment for construction equipment status, availability, maintenance
schedules. Examples:
- "Quels équipements sont disponibles ?"
- "Équipements en maintenance"
- "Équipements en cours d'utilisation"
- "Grues, engins, matériel disponibles"
- "Quelle machine est en panne ?"
Available filters: status (Available, In Use, Maintenance), category.
Returns: equipment_id, name, status, category, location, next_maintenance.
"""
    },
    {
        "endpoint": "/suppliers",
        "content": """
Use /suppliers for vendor and supplier information, ratings, contact details.
Examples:
- "Liste des fournisseurs actifs"
- "Fournisseurs les mieux notés"
- "Fournisseurs de matériaux de construction"
- "Contact du fournisseur X"
- "Quels fournisseurs livrent à Tunis ?"
Available filters: status (Active, Inactive, Blacklisted).
Returns: supplier_name, category, status, rating, contact_person, email, city.
"""
    },
    {
        "endpoint": "/notifications",
        "content": """
Use /notifications for unread alerts, system messages, and notifications
for the current user. Examples:
- "Mes notifications non lues"
- "Alertes récentes"
- "Nouveaux messages système"
No filters — always scoped to the current user.
Returns: title, message, is_read, created_date.
"""
    },
]

# ── Seed the vector store ─────────────────────────────────────────────────────
def seed():
    print(f"Connecting to ChromaDB at '{CHROMA_DIR}', collection '{COLLECTION_NAME}'...")
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)

    # Load existing store
    store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )

    # Delete existing API docs to avoid duplicates
    try:
        existing = store.get(where={"category": "api"})
        if existing and existing.get("ids"):
            store.delete(ids=existing["ids"])
            print(f"  Deleted {len(existing['ids'])} existing API doc chunks.")
    except Exception as e:
        print(f"  Warning during cleanup: {e}")

    # Build and add documents
    docs = []
    for item in API_DOCS:
        doc = Document(
            page_content=item["content"].strip(),
            metadata={
                "category": "api",
                "endpoint": item["endpoint"],
                "source":   "api_documentation",
            }
        )
        docs.append(doc)

    store.add_documents(docs)
    print(f"  Added {len(docs)} API documentation chunks.")
    print()
    print("Done. Endpoints seeded:")
    for item in API_DOCS:
        print(f"  {item['endpoint']}")

if __name__ == "__main__":
    seed()