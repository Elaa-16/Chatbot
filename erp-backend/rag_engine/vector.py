"""
Vector Store Builder — Construction ERP RAG
Indexes:
  1. API endpoint descriptions (semantic routing)
  2. Only real documents: policies, procedures, glossaire, emails
Run: python vector.py
"""

import os
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

embeddings = OllamaEmbeddings(model="mxbai-embed-large")

vector_store = Chroma(
    collection_name="erp_apis",
    embedding_function=embeddings,
    persist_directory=r"C:\Users\msi\Chatbot\erp-backend\rag_engine\erp_chroma_db"
)
vector_store.reset_collection()
print("Cleared vector store")

all_documents = []

# ════════════════════════════════════════════════════════════════════════════
# PART 1: API ENDPOINT DESCRIPTIONS
# ════════════════════════════════════════════════════════════════════════════
api_docs = [
    Document(
        page_content="Get all projects, project status In Progress Completed Planning, budget_eur actual_cost_eur completion_percentage, location, construction sites, chantiers, projets en cours",
        metadata={"source": "api", "endpoint": "/projects", "type": "projects", "category": "api"}
    ),
    Document(
        page_content="Get delayed projects behind schedule late projects retard, schedule_variance_days positive means delayed, budget_variance_percentage, quality_score, safety_incidents, risk_level High Medium Low, KPI performance indicators, projets en retard, indicateurs",
        metadata={"source": "api", "endpoint": "/kpis", "type": "kpis", "category": "api"}
    ),
    Document(
        page_content="Get all tasks, task status Todo In Progress Done Blocked, priority Critical High Medium Low, assigned_to employee, due_date, taches, kanban board, travaux a faire, taches bloquees, taches critiques",
        metadata={"source": "api", "endpoint": "/tasks", "type": "tasks", "category": "api"}
    ),
    Document(
        page_content="Get tasks grouped by manager, manager performance, blocked tasks per manager, critical tasks per team, qui a le plus de taches bloquees, comparaison managers, charge de travail equipe, taches par chef, equipe bloquee, manager le moins performant",
        metadata={"source": "api", "endpoint": "/tasks/by-manager", "type": "tasks_by_manager", "category": "api"}
    ),
    Document(
        page_content="Get manager performance statistics, manager ranking, best worst manager, blocked tasks open critical tasks avg completion, statistiques managers, classement performance managers, manager le moins performant, performance chef de projet, comparaison chefs",
        metadata={"source": "api", "endpoint": "/stats/by-manager", "type": "stats_by_manager", "category": "api"}
    ),
    Document(
        page_content="Get issues incidents problems on construction site, severity Critical High Medium Low, category Safety Quality Delay Budget Technical Other, status Open In Progress Resolved Closed, incidents chantier, problemes securite, incidents non resolus, signalements, accidents",
        metadata={"source": "api", "endpoint": "/issues", "type": "issues", "category": "api"}
    ),
    Document(
        page_content="Get all employees, employee list, position, department, role ceo manager employee rh, team members, staff, equipe, employes, personnel, liste employes, employes disponibles, membres equipe, qui sont les employes, organigramme",
        metadata={"source": "api", "endpoint": "/employees", "type": "employees", "category": "api"}
    ),
    Document(
        page_content="Get all leave requests, conges, employee absence, vacation, sick leave annual leave, status Approved Rejected Pending, who is absent, demandes de conge, absences, conges en attente, conges approuves, qui est absent",
        metadata={"source": "api", "endpoint": "/leave-requests", "type": "leaves", "category": "api"}
    ),
    Document(
        page_content="Get statistics summary, total projects count, total budget sum, average completion percentage, overall company performance, dashboard stats, resume statistiques globales, vue globale, bilan general",
        metadata={"source": "api", "endpoint": "/stats/summary", "type": "stats", "category": "api"}
    ),
    Document(
        page_content="Get task statistics, total tasks count, todo count, in progress count, done count, blocked count, critical tasks count, high priority tasks statistics, bilan taches, statistiques taches globales",
        metadata={"source": "api", "endpoint": "/stats/tasks", "type": "task_stats", "category": "api"}
    ),
    Document(
        page_content="Get notifications, unread notifications, alerts, system messages, annonces, messages non lus, alertes",
        metadata={"source": "api", "endpoint": "/notifications", "type": "notifications", "category": "api"}
    ),
    Document(
        page_content="Get timesheets, hours worked, billable hours, work log, employee time tracking, heures travaillees, feuilles de temps, pointage",
        metadata={"source": "api", "endpoint": "/timesheets", "type": "timesheets", "category": "api"}
    ),
    Document(
        page_content="Get equipment, machinery status Available In Use Maintenance, construction tools and machines, equipements, materiel, engins, grue, bulldozer",
        metadata={"source": "api", "endpoint": "/equipment", "type": "equipment", "category": "api"}
    ),
    Document(
        page_content="Get suppliers, fournisseurs, supplier list, Active suppliers, supplier category, procurement, achats, materiaux, services",
        metadata={"source": "api", "endpoint": "/suppliers", "type": "suppliers", "category": "api"}
    ),
]

all_documents.extend(api_docs)
print(f"API descriptions: {len(api_docs)} documents")

# ════════════════════════════════════════════════════════════════════════════
# PART 2: BUSINESS KNOWLEDGE DOCUMENTS ONLY
# policies, procedures, glossaire, emails
# NOTE: No project_report, kpi_analysis, employee_guide — live DB is better
# ════════════════════════════════════════════════════════════════════════════

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,   # 600 → 1000 : sections complètes dans un seul chunk
    chunk_overlap=200, # 100 → 200 : évite de couper une règle en deux chunks
    separators=["\n\n", "\n", ".", " "]
)

RAG_DIR = "rag_documents"

# ✅ Only index business knowledge — NOT dynamic data (projects, employees, kpis)
folder_metadata = {
    "policies":   {"category": "policy"},
    "procedures": {"category": "procedure"},
    "glossaire":  {"category": "glossaire"},
    "emails":     {"category": "internal_communication"},
}

total_chunks = 0
total_files = 0

for folder, meta in folder_metadata.items():
    folder_path = os.path.join(RAG_DIR, folder)
    if not os.path.exists(folder_path):
        print(f"Folder not found (skipping): {folder_path}")
        continue

    files = [f for f in os.listdir(folder_path) if f.endswith(".txt")]
    folder_chunks = 0

    for filename in files:
        filepath = os.path.join(folder_path, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = splitter.split_text(text)
        docs = [
            Document(
                page_content=chunk,
                metadata={
                    "source": filepath,
                    "filename": filename,
                    "folder": folder,
                    "category": meta["category"],
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "endpoint": None,
                    "type": meta["category"],
                }
            )
            for i, chunk in enumerate(chunks)
        ]

        all_documents.extend(docs)
        folder_chunks += len(docs)
        total_files += 1

    print(f"{folder:15s}: {len(files)} files -> {folder_chunks} chunks")
    total_chunks += folder_chunks

# ════════════════════════════════════════════════════════════════════════════
# INDEX IN BATCHES
# ════════════════════════════════════════════════════════════════════════════
print(f"\nTotal documents to index: {len(all_documents)}")
print(f"  - API descriptions: {len(api_docs)}")
print(f"  - Business knowledge chunks: {total_chunks} from {total_files} files")
print("\nIndexing into ChromaDB...")

BATCH_SIZE = 50
for i in range(0, len(all_documents), BATCH_SIZE):
    batch = all_documents[i:i+BATCH_SIZE]
    vector_store.add_documents(documents=batch)
    print(f"  Indexed {min(i+BATCH_SIZE, len(all_documents))}/{len(all_documents)}")

print(f"\nDone! Vector store ready at ./erp_chroma_db")
print(f"Total vectors: {len(all_documents)}")