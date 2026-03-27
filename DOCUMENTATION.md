# ERP Chatbot System — Supervisor Documentation
**Project:** Construction ERP with Integrated AI Chatbot  
**Stack:** FastAPI (Python) · SQLite · React (Vite) · Groq LLM API · ChromaDB · n8n  
**Date:** March 2026

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Project Structure](#3-project-structure)
4. [Authentication & Token System](#4-authentication--token-system)
5. [Role-Based Access Control (RBAC)](#5-role-based-access-control-rbac)
6. [API Security — Whitelist Middleware](#6-api-security--whitelist-middleware)
7. [Data Models & Business Entities](#7-data-models--business-entities)
8. [API Routes & Business Rules](#8-api-routes--business-rules)  
   8.1 [Tasks](#81-tasks)  
   8.2 [Leave Requests](#82-leave-requests)  
   8.3 [Projects & KPIs](#83-projects--kpis)  
   8.4 [Employees](#84-employees)  
   8.5 [Equipment, Suppliers, Purchase Orders](#85-equipment-suppliers-purchase-orders)  
   8.6 [Timesheets, Notifications, Documents](#86-timesheets-notifications-documents)
9. [Audit Logging](#9-audit-logging)
10. [RAG Chatbot Engine](#10-rag-chatbot-engine)  
    10.1 [Engine Version & LLM Stack](#101-engine-version--llm-stack)  
    10.2 [Two Vector Retrievers](#102-two-vector-retrievers)  
    10.3 [Question Classification Pipeline](#103-question-classification-pipeline)  
    10.4 [RBAC Inside the Chatbot](#104-rbac-inside-the-chatbot)  
    10.5 [Planner — Query Planning Phase](#105-planner--query-planning-phase)  
    10.6 [Formatter — Live Data Rendering](#106-formatter--live-data-rendering)  
    10.7 [Answer Generation Phase](#107-answer-generation-phase)
11. [Proactive Alert System](#11-proactive-alert-system)  
    11.1 [N8N Daily Automation Workflow](#111-n8n-daily-automation-workflow)  
    11.2 [Equipment Maintenance Alerts](#112-equipment-maintenance-alerts)  
    11.3 [Frontend Polling & Race Condition Fix](#113-frontend-polling--race-condition-fix)
12. [RAG Document Knowledge Base](#12-rag-document-knowledge-base)
13. [Frontend Architecture](#13-frontend-architecture)
14. [Environment Configuration](#14-environment-configuration)
15. [Security Summary](#15-security-summary)

---

## 1. System Overview

This is a **Construction ERP system** built for a Tunisian construction company. It manages:

- Projects, tasks, KPIs, issues, equipment, suppliers, purchase orders
- Employees, HR leave requests, timesheets, documents
- An integrated **AI assistant chatbot** that can answer questions about live ERP data using RAG (Retrieval-Augmented Generation)
- A **proactive alert system** that automatically pushes management warnings to employees via an n8n automation workflow

The backend is a **FastAPI** REST API backed by a **SQLite** database. The frontend is a **React** single-page application (Vite). The AI is powered by **Groq API** (llama-3.3-70b-versatile) with **local embeddings** (Ollama / mxbai-embed-large) stored in **ChromaDB**.

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend (Vite)                     │
│   Dashboard · Projects · Tasks · KPIs · Chat · Admin Panel      │
└─────────────────────────┬───────────────────────────────────────┘
                           │  HTTP/REST  +  Bearer JWT Token
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (port 8000)                    │
│                                                                  │
│  ┌────────────────┐   ┌──────────────────────────────────────┐  │
│  │ WhitelistMiddle│   │         CORS Middleware               │  │
│  │ware (layer 1)  │   │  (allowed origins from .env)         │  │
│  └────────┬───────┘   └──────────────────────────────────────┘  │
│           │                                                      │
│  ┌────────▼────────────────────────────────────────────────┐    │
│  │              JWT Authentication (layer 2)               │    │
│  │    authenticate_with_token() — verifies Bearer token    │    │
│  └────────┬────────────────────────────────────────────────┘    │
│           │                                                      │
│  ┌────────▼────────────────────────────────────────────────┐    │
│  │          RBAC Guards (layer 3, per-endpoint)            │    │
│  │  check_edit_permission() · get_accessible_projects()    │    │
│  └────────┬────────────────────────────────────────────────┘    │
│           │                                                      │
│  ┌────────▼────────────────────────────────────────────────┐    │
│  │                  API Routers                            │    │
│  │  /projects  /tasks  /employees  /leave-requests  /kpis  │    │
│  │  /issues  /equipment  /suppliers  /purchase-orders      │    │
│  │  /timesheets  /notifications  /documents  /reports      │    │
│  │  /stats  /activity-logs  /whitelist  /chat              │    │
│  └────────┬────────────────────────────────────────────────┘    │
│           │                                                      │
│  ┌────────▼──────────────┐   ┌────────────────────────────┐    │
│  │   SQLite Database     │   │   RAG Chatbot Engine       │    │
│  │   erp_database.db     │   │   chat.py (2565 lines)     │    │
│  └───────────────────────┘   └──────────────┬─────────────┘    │
│                                              │                   │
└──────────────────────────────────────────────┼───────────────────┘
                                               │
                          ┌────────────────────▼──────────────────┐
                          │   Groq API (llama-3.3-70b-versatile)  │
                          │   ChromaDB (mxbai-embed-large, local) │
                          └───────────────────────────────────────┘

External automation:
  ┌─────────────────────────────────────────────┐
  │  n8n Workflow (runs daily at 09:00)          │
  │  GET /tasks → GET /kpis → Filter → Groq LLM │
  │  → POST /chat/alerts (push to employee)      │
  └─────────────────────────────────────────────┘
```

---

## 3. Project Structure

```
Chatbot/
├── erp-backend/
│   ├── main.py                  ← FastAPI app entry point, middleware setup
│   ├── core/
│   │   ├── auth.py              ← JWT creation/verification, RBAC helpers, audit log
│   │   ├── database.py          ← SQLite connection dependency
│   │   └── models.py            ← Pydantic models for all entities
│   ├── api/routes/
│   │   ├── projects.py          ← /projects CRUD
│   │   ├── tasks.py             ← /tasks CRUD + RBAC scoping
│   │   ├── employees.py         ← /employees CRUD
│   │   ├── leave_requests.py    ← /leave-requests + approval workflow
│   │   ├── kpis.py              ← /kpis CRUD
│   │   ├── reports.py           ← /reports generation
│   │   ├── whitelist.py         ← /whitelist (admin only)
│   │   └── other.py             ← /issues /equipment /suppliers /purchase-orders
│   │                               /timesheets /notifications /documents
│   │                               /activity-logs /stats
│   └── rag_engine/
│       ├── chatbot.py           ← FastAPI router for /chat endpoints
│       ├── chat.py              ← Core RAG engine logic (2565 lines)
│       ├── vector.py            ← ChromaDB vector store builder
│       └── rag_documents/       ← Business knowledge text files
│           ├── policies/
│           ├── procedures/
│           ├── glossaire/
│           └── emails/
├── erp-frontend/
│   └── src/
│       ├── components/          ← React components (Dashboard, Projects, Tasks, etc.)
│       └── ...
└── n8n_daily_alerts_workflow.json  ← Importable n8n automation workflow
```

---

## 4. Authentication & Token System

**File:** `core/auth.py`

### How it works

1. The user submits `POST /login` with `{ username, password }`.
2. The server fetches the user from the `employees` table.
3. The password is verified against a stored **Argon2 hash** (`passlib.hash.argon2`).
4. On success, a **JWT access token** is generated:
   - Algorithm: **HS256**
   - Expiry: **60 minutes** from issuance
   - Secret: read from `JWT_SECRET_KEY` environment variable (fails at startup if missing)
   - Payload contains: `sub` (username), `employee_id`, `role`
5. The token is returned to the frontend and stored in memory.
6. Every protected request sends the token as `Authorization: Bearer <token>`.
7. The `authenticate_with_token()` dependency verifies the JWT and re-fetches the user from SQLite to ensure it is still valid (not deleted/changed).

### Token refresh

`POST /refresh-token` — returns a new token for the same user without re-entering credentials, as long as the current token is still valid.

### Password hashing

All passwords are hashed with **Argon2** (memory-hard algorithm). Plain-text passwords are never stored.

### Locked fields

`EMPLOYEE_LOCKED_FIELDS` prevents employees from modifying their own `role`, `salary`, `manager_id`, `supervised_employees`, `department`, or `position` through the API.

---

## 5. Role-Based Access Control (RBAC)

There are **4 roles** in the system:

| Role       | Description                                                           |
|------------|-----------------------------------------------------------------------|
| `ceo`      | Sees everything — all projects, all employees, all KPIs, all data     |
| `manager`  | Sees their supervised team's data and projects derived from tasks     |
| `rh`       | Human Resources — sees all employees and all leave requests           |
| `employee` | Sees only their own tasks, leave requests, timesheets, notifications  |

### Data scoping rules (enforced at the API layer)

#### Projects (`get_accessible_projects`)
- **CEO / RH:** `None` → no filter (sees all)
- **Manager:** derives accessible projects from the `tasks` table where `assigned_to IN (manager_id + supervised_employees)` — this is always fresh, never stale
- **Employee:** uses `assigned_projects` column from their own row

#### Tasks (`GET /tasks`)
- **Employee:** hard filter `AND assigned_to = {user_id}` — cannot see others' tasks
- **Manager:** hard filter `AND assigned_to IN ({team members + self})` — scoped to team
- **CEO/RH:** no filter — sees all tasks across all projects

#### Leave Requests
- **CEO/RH:** sees all
- **Manager:** sees only their supervised employees (+ themselves)
- **Employee:** sees only their own requests; cannot query by another `employee_id`

#### Edit Permissions
Only `ceo` and `manager` roles can **create, update, or delete** resources:
```python
def check_edit_permission(user):
    if user["role"] not in ["ceo", "manager"]:
        raise HTTPException(403, "Only CEO and Managers can create/edit/delete resources")
```

#### Leave Approval
- **Manager** can approve/reject leave requests for their **supervised employees only**
- **RH** can approve/reject any employee's leave request
- **CEO** can approve/reject manager-level requests (escalation)

#### Leave Submission
- **CEO and RH do not submit leave requests** (raises 403)
- **Employee** can only submit for themselves (`employee_id` must match their own)

---

## 6. API Security — Whitelist Middleware

**File:** `main.py` (`WhitelistMiddleware` class)

This is a **server-level middleware** that runs on every single HTTP request **before any route handler**. It acts as a firewall for the API surface.

### How it works

1. **Always allowed** (bypass whitelist check):
   - Exact paths: `/`, `/login`, `/me`, `/refresh-token`, `/openapi.json`
   - Prefix paths: `/docs`, `/redoc`, `/whitelist`, `/activity-logs`, `/stats`
   - All `OPTIONS` requests (CORS preflight)

2. **For all other requests**, the middleware:
   - Extracts the **base path** (e.g., `/tasks/T001` → `/tasks`)
   - Looks up `base_path` in the `api_whitelist` table in SQLite
   - If the endpoint is **not found** → `403 "API not in whitelist"`
   - If the endpoint is **inactive** (`is_active = 0`) → `403 "API disabled by administrator"`
   - If the HTTP **method is not allowed** → `405 "Method not allowed"`
   - Otherwise: request passes through to the route handler

3. The whitelist table is managed via `POST/PUT/DELETE /whitelist` — **admin role only**.

### Purpose

The whitelist allows the administrator to:
- Disable specific API endpoints without touching the code
- Restrict which HTTP methods are allowed per endpoint
- Enable/disable endpoints dynamically at runtime (no restart needed)

---

## 7. Data Models & Business Entities

**File:** `core/models.py`

All request/response bodies are typed with **Pydantic models**. Key entities:

| Entity           | Key Fields                                                                                 |
|------------------|-------------------------------------------------------------------------------------------|
| **Employee**     | `employee_id`, `username`, `role`, `department`, `position`, `manager_id`, `supervised_employees`, `assigned_projects` |
| **Project**      | `project_id`, `project_name`, `status`, `budget`, `actual_cost`, `completion_percentage`, `project_manager_id` |
| **Task**         | `task_id`, `project_id`, `assigned_to`, `priority` (Critical/High/Medium/Low), `status` (Todo/In Progress/Done/Blocked), `due_date` |
| **KPI**          | `kpi_id`, `project_id`, `budget_variance_percentage`, `schedule_variance_days`, `quality_score`, `spi`, `cpi`, `risk_level` |
| **LeaveRequest** | `request_id`, `employee_id`, `leave_type`, `start_date`, `end_date`, `total_days`, `status` (Pending/Approved/Rejected) |
| **Issue**        | `issue_id`, `project_id`, `severity`, `category` (Safety/Quality/Delay/Budget/Technical/Other), `status` |
| **Equipment**    | `equipment_id`, `status` (Available/In Use/Maintenance), `next_maintenance` |
| **Notification** | `notification_id`, `user_id`, `type`, `title`, `message`, `is_read`, `priority` |
| **ActivityLog**  | `log_id`, `user_id`, `action_type`, `entity_type`, `entity_id`, `description`, `timestamp` |
| **ApiWhitelist** | `id`, `endpoint`, `methods`, `description`, `is_active` |

---

## 8. API Routes & Business Rules

### 8.1 Tasks

**Prefix:** `/tasks`

| Method | Path               | Permission         | Description                                     |
|--------|--------------------|--------------------|--------------------------------------------------|
| GET    | `/tasks`           | All roles          | List tasks (auto-scoped by RBAC)                 |
| GET    | `/tasks/{id}`      | All roles          | Get single task (access denied if out of scope)  |
| POST   | `/tasks`           | CEO, Manager only  | Create task + auto-notify assigned employee      |
| PUT    | `/tasks/{id}`      | CEO, Manager only  | Update task fields                               |
| DELETE | `/tasks/{id}`      | CEO, Manager only  | Delete task                                      |
| PUT    | `/tasks/{id}/status` | All authenticated | Update only the status field                    |

**Business rules:**
- Task creation automatically generates a **notification** for the assigned employee
- Notification priority is `High` if task priority is `Critical` or `High`, otherwise `Medium`
- Every create/update/delete is **audit-logged**
- Tasks are ordered by `due_date ASC, priority DESC`
- An `overdue=true` filter returns tasks where `due_date < today AND status != 'Done'`

### 8.2 Leave Requests

**Prefix:** `/leave-requests`

| Method | Path                       | Permission           | Description                                      |
|--------|----------------------------|----------------------|--------------------------------------------------|
| GET    | `/leave-requests`          | Scoped by role       | List leave requests                              |
| GET    | `/leave-requests/pending`  | CEO, RH, Manager     | List requests waiting approval                   |
| GET    | `/leave-requests/{id}`     | Owner or approver    | Get single request                               |
| POST   | `/leave-requests`          | Manager, Employee    | Submit a leave request                           |
| PUT    | `/{id}/approve`            | RH or manager (team) | Approve request + update employee leave counters |
| PUT    | `/{id}/reject`             | RH or manager (team) | Reject request with mandatory comment            |
| PUT    | `/{id}/cancel`             | Owner only           | Cancel their own pending request                 |

**Business rules:**
- **Annual leave quota check**: system verifies the employee has enough remaining annual leave days before allowing submission. Returns `400 Insufficient annual leave` if exceeded.
- **Approval routing**: when an employee submits a request, a **notification is sent to their direct manager** and to **RH** simultaneously.
- **CEO approval for managers**: when a manager submits, the notification goes to the CEO.
- **On approval**: the `annual_leave_taken` (or `sick_leave_taken`/`other_leave_taken`) counter on the employee record is incremented.
- **On approval/rejection**: a notification is sent back to the requesting employee.
- Leave status lifecycle: `Pending → Approved | Rejected | Cancelled`

**Leave entitlements** (encoded in the chatbot engine):

| Leave Type   | Days |
|--------------|------|
| Annual       | 35   |
| Sick         | 30   |
| Maternity    | 60   |
| Paternity    | 3    |
| Exceptional  | 5    |
| Unpaid       | 30   |

### 8.3 Projects & KPIs

**Projects (`/projects`):**
- CRUD operations, CEO and Manager can edit
- Project assignment (`assigned_employees` field) automatically syncs to each employee's `assigned_projects` column via `sync_project_assignments()`
- Project manager and site supervisor are also auto-added to the project's employee list

**KPIs (`/kpis`):**
- Tracks per-project performance: `budget_variance_percentage`, `schedule_variance_days`, `quality_score`, `safety_incidents`, `risk_level`, `spi` (Schedule Performance Index), `cpi` (Cost Performance Index)
- `delayed=true` filter: returns projects where `schedule_variance_days > 0`
- `risk_level=High` filter: returns only high-risk projects
- `history=true` parameter: returns historical KPI trends

### 8.4 Employees

**Prefix:** `/employees`

- **CEO only** can create or delete employees
- Employees can update their own non-locked fields (name, email, phone)
- RBAC-locked fields: `role`, `salary`, `manager_id`, `supervised_employees`, `department`, `position`
- Soft-delete: status set to `Inactive` rather than physical deletion

### 8.5 Equipment, Suppliers, Purchase Orders

**Equipment (`/equipment`):**
- Status values: `Available`, `In Use`, `Maintenance`
- Proactive maintenance alerts: if `next_maintenance <= now + 7 days` and `status != 'Maintenance'`, the chatbot `/chat/proactive` endpoint generates an alert

**Suppliers (`/suppliers`):**
- Rating field (1–5 stars)
- Filter by `sort_by_rating=true` returns highest-rated first

**Purchase Orders (`/purchase-orders`):**
- Approval workflow: `Pending → Approved` with `approved_by` and `approval_date` fields

### 8.6 Timesheets, Notifications, Documents

**Timesheets:** Track hours worked per employee per day per project. `billable` and `approved` flags. Employees see only their own timesheets.

**Notifications:** System-generated, targeted per `user_id`. Frontend polls for unread notifications. `is_read` flag updated when user opens notification.

**Documents:** File metadata stored in DB (`file_path`, `file_size_kb`, `category`, `tags`). Physical files stored on disk.

---

## 9. Audit Logging

**Function:** `log_action()` in `core/auth.py`

Every significant action is automatically recorded in the `activity_logs` table:

```
log_id | user_id | action_type | entity_type | entity_id | description | timestamp
```

**Actions logged automatically:**
- `login` — on every successful authentication
- `Create` — on every resource creation (task, project, employee, leave request, etc.)
- `Update` — on every update
- `Delete` — on every deletion
- `Approve` / `Reject` — on leave request decisions
- `prompt` — on every chatbot query (first 100 characters of the message)

Accessible via `GET /activity-logs` (always whitelisted, visible to admin/CEO).

---

## 10. RAG Chatbot Engine

**Files:** `rag_engine/chatbot.py` (router), `rag_engine/chat.py` (engine, ~2565 lines)

This is the core AI component. It receives a user question and returns an intelligent, data-grounded answer.

### 10.1 Engine Version & LLM Stack

| Component       | Technology                                   |
|-----------------|----------------------------------------------|
| **LLM**         | Groq API — model `llama-3.3-70b-versatile`   |
| **Embeddings**  | Ollama local — model `mxbai-embed-large`     |
| **Vector DB**   | ChromaDB (persisted locally on disk)         |
| **Framework**   | LangChain (retriever interface only)         |
| **API calls**   | Internal REST calls to `http://localhost:8000` with the user's own Bearer token |

### 10.2 Two Vector Retrievers

The vector store holds two types of documents, each queried by a separate retriever:

| Retriever          | Filter                  | k  | Purpose                                      |
|--------------------|-------------------------|----|----------------------------------------------|
| `api_retriever`    | `category = "api"`      | 14 | Finds which API endpoint answers the question |
| `doc_retriever`    | `category IN [policy, procedure, glossaire, internal_communication, ...]` | 25 | Finds relevant HR/compliance documents |

### 10.3 Question Classification Pipeline

When `answer_question()` is called, the engine runs the question through a **classification pipeline** in order:

```
Incoming question
       │
       ├─► 1. GLOSSARY CHECK — is it a definition question?
       │       (e.g., "c'est quoi le SPI ?")
       │       → Returns hard-coded definition immediately (no LLM call)
       │
       ├─► 2. LEAVE BALANCE HANDLER — is it asking for leave balance?
       │       (e.g., "combien de jours me restent ?")
       │       → Calls /leave-requests live API, computes balance, returns
       │
       ├─► 3. MEETING/CR QUESTION — about meeting minutes?
       │       → Routes to doc_retriever (secretary notes in RAG corpus)
       │
       ├─► 4. POLICY QUESTION — about rules, procedures, regulations?
       │       (e.g., "quelle est la politique de congé ?")
       │       → Routes to RAG documents only (no live DB call)
       │
       └─► 5. LIVE DATA QUESTION — default path
               → Planner → API calls → Formatter → Answer LLM
```

### 10.4 RBAC Inside the Chatbot

The chatbot enforces RBAC **at the planning level**, before any API call is made:

```python
ROLE_ALLOWED_ENDPOINTS = {
    "ceo":      ["/projects", "/kpis", "/tasks", "/tasks/by-manager", "/employees",
                 "/leave-requests", "/issues", "/timesheets", "/equipment",
                 "/suppliers", "/purchase-orders", "/notifications", "/stats/*"],
    "manager":  ["/projects", "/tasks", "/tasks/by-manager", "/employees",
                 "/leave-requests", "/issues", "/timesheets", "/notifications",
                 "/stats/tasks", "/kpis", "/suppliers", "/purchase-orders"],
    "rh":       ["/leave-requests", "/employees", "/notifications"],
    "employee": ["/tasks", "/leave-requests", "/timesheets", "/notifications", "/kpis"],
}
```

If a question targets an endpoint not in the user's allowed list, the chatbot returns a scope restriction message instead of calling the API.

Additionally, the data scoping rules of the REST API apply — since the chatbot calls the API **with the user's own token**, the API itself enforces row-level filtering.

### 10.5 Planner — Query Planning Phase

The planner converts a natural-language question into a **structured list of API calls**.

**Step 1 — Deterministic fallback rules:** The engine first tries to resolve the question using keyword-based rules (no LLM call needed):

```
"employe", "personnel" → /employees
"retard", "kpi"        → /kpis
"projet", "chantier"   → /projects
"tache", "task"        → /tasks
"conge", "absence"     → /leave-requests
"incident", "probleme" → /issues
...
```

**Step 2 — LLM Planner (if fallback insufficient):** Calls Groq LLM with the `PLANNER_TEMPLATE` prompt. The prompt includes:
- Available endpoints for the user's role
- Exact DB enum values (statuses, priorities, categories)
- Mapping rules (e.g., "taches bloquees → `/tasks` with `status: Blocked`")
- Security rules (employee: force `assigned_to = user_id`; manager: never add personal filter to team queries)
- Output format: strict JSON `{ "reasoning": "...", "endpoints": [{endpoint, filters}] }`

**Filter extraction** — the engine also automatically extracts filters from the question text:

| Question contains    | Filter added                   |
|----------------------|-------------------------------|
| "bloqué", "blocked"  | `status: Blocked`             |
| "critique"           | `priority: Critical`          |
| "en cours"           | `status: In Progress`         |
| "en retard"          | `delayed: true` (for KPIs)    |
| "maintenant", "aujourd'hui" | `active_today: true` (for leave) |
| "mon équipe"         | `supervised_by: {user_id}`    |

**Virtual endpoints** (computed server-side, no DB table):
- `/tasks/by-manager` — aggregates tasks per manager with blocked/critical counts
- `/stats/by-manager` — manager performance ranking
- `/stats/tasks` — global task statistics

### 10.6 Formatter — Live Data Rendering

After API calls return data, `format_endpoint_data()` structures the raw JSON into a human-readable text block that the LLM can copy verbatim. Format examples:

```
=== TASKS ===
Résultats (12):
- T001: Coulage fondations | Statut: Blocked | Priorité: Critical | Échéance: 2024-04-15 | Assigné à: Mohamed Ali | Projet: P001
```

Employee IDs in `assigned_to` are **resolved to full names** via `_EMPLOYEE_CACHE` to avoid showing raw IDs in answers.

### 10.7 Answer Generation Phase

The final answer is generated by calling `_call_groq()` with the `ANSWER_TEMPLATE` prompt, which contains:
- **DONNEES LIVE** — the formatted live data blocks
- **CONNAISSANCES DOCUMENTAIRES** — any relevant RAG document chunks
- User profile (name, role)
- The original question

**Strict rules given to the LLM (enforced via prompt):**
- R1: Copy the `=== BLOCK ===` data word-for-word — no omissions
- R2: No introductory sentences
- R3: No "Note:", "However:", "Cependant:"
- R4: Never end with a question or offer of help
- R5: Never invent data not present in live data
- R6: Analytical questions → short structured text from live data only
- R7: If no live data → say "Aucune donnée disponible"
- R8: Never invent employee names or figures
- R10: No text after the last data block

---

## 11. Proactive Alert System

### 11.1 N8N Daily Automation Workflow

**File:** `n8n_daily_alerts_workflow.json`

The workflow runs automatically **every day at 09:00** via a cron trigger (`0 9 * * *`). It has 5 nodes:

```
[Schedule Trigger: 09:00 daily]
        │
        ▼
[Get Tasks] — GET /tasks (all tasks, admin token)
        │
        ▼
[Get KPIs] — GET /kpis (all KPI data)
        │
        ▼
[Filter Anomalies] — JavaScript code node:
  • Identifies delayed projects (schedule_variance_days > 0)
  • Selects tasks that are:
    - Blocked, OR
    - Not Done AND belonging to a delayed project
        │
        ▼
[Groq LLM] — For each problem task, generates a short 1-sentence
  proactive alert in French addressed to the responsible employee
  (model: llama3-8b-8192)
        │
        ▼
[Push Alert to Chatbot] — POST /chat/alerts
  { employee_id: <assignee>, message: <LLM-generated alert> }
  → Stored in the chat_alerts table, is_read = 0
```

### 11.2 Equipment Maintenance Alerts

**File:** `rag_engine/chatbot.py` — `GET /chat/proactive`

Independently of N8N, when any authenticated user opens the chatbot, the `GET /chat/proactive` endpoint automatically checks:

- Any equipment in the `equipment` table where `next_maintenance <= now + 7 days` AND `status != 'Maintenance'`
- Generates a maintenance alert message for each match

These alerts are returned alongside the N8N alerts as a combined list.

### 11.3 Frontend Polling & Race Condition Fix

The frontend polls `GET /chat/proactive` when the chat interface opens. The endpoint:

1. Queries unread N8N alerts for the user (`is_read = 0`)
2. Immediately marks them as `is_read = 1` in the same DB transaction (before returning)
3. Returns all alerts (equipment + N8N) in a single response

This **read-and-mark-atomic** pattern prevents the race condition where:
- The alert would be fetched twice (showing duplicates)
- Or be marked read before the user actually sees it

---

## 12. RAG Document Knowledge Base

**File:** `rag_engine/vector.py`

The vector store holds two categories:

### Category 1: API Semantic Routing Descriptions
14 hand-crafted documents (one per API endpoint) written as natural-language descriptions in French and English. These help the LLM planner find the right endpoint for any question.

### Category 2: Business Knowledge Documents
Text files organized in folders:

| Folder       | ChromaDB Category          | Content                              |
|--------------|----------------------------|--------------------------------------|
| `policies/`  | `policy`                   | HR policies, leave rules, safety EPI |
| `procedures/`| `procedure`                | Work procedures, onboarding          |
| `glossaire/` | `glossaire`                | BTP / ERP glossary terms             |
| `emails/`    | `internal_communication`   | Secretary meeting minutes, CR        |

**Chunking strategy:**
- Chunk size: 1000 characters
- Overlap: 200 characters
- Separators: `\n\n`, `\n`, `.`, ` ` (paragraph → sentence → word)

**Re-ranking:** After retrieval, `_rerank_doc_chunks()` re-scores chunks by keyword overlap with the question and keeps the top 6 most relevant chunks before sending to the LLM.

**Built-in glossary** (no vector lookup needed):

| Term | Definition                                      |
|------|-------------------------------------------------|
| SPI  | Schedule Performance Index = EV/PV              |
| CPI  | Cost Performance Index = EV/AC                  |
| KPI  | Key Performance Indicator                       |
| EPI  | Équipements de Protection Individuelle          |
| BTP  | Bâtiment et Travaux Publics                     |
| MOA  | Maître d'Ouvrage                                |
| MOE  | Maître d'Œuvre                                  |
| TF   | Taux de Fréquence = Accidents × 1M / Heures     |
| TG   | Taux de Gravité = Jours perdus × 1000 / Heures  |

---

## 13. Frontend Architecture

**Technology:** React 18 + Vite + TailwindCSS  
**Path:** `erp-frontend/src/`

| Component        | Route/Purpose                                              |
|------------------|------------------------------------------------------------|
| Dashboard        | Summary stats, KPI cards, project overview                  |
| Projects         | Projects table + CRUD modals                               |
| Tasks            | Kanban-style task board with filters                       |
| KPIs             | KPI table with delayed/risk highlights                     |
| Employees        | Employee directory, filtered by role/department            |
| LeaveRequests    | Leave request list + approval buttons                      |
| Equipment        | Equipment status grid                                      |
| Suppliers        | Supplier list with rating                                  |
| PurchaseOrders   | PO management                                              |
| Timesheets       | Timesheet log                                              |
| Notifications    | Notification bell + list                                   |
| AuditLogs        | Admin view of activity_logs                                |
| AdminPanel       | Whitelist management (admin role only)                     |
| Chat             | AI chatbot interface (polls /chat/proactive on open)       |
| Reports          | Report generation                                          |

**Authentication flow:**
1. Login page submits credentials → stores JWT token in React state (memory, not localStorage)
2. All API calls use `Authorization: Bearer <token>` header
3. On 401 response → redirect to login
4. Token refresh called proactively before expiry

---

## 14. Environment Configuration

**File:** `.env` (not committed to repository)

| Variable              | Description                                    |
|-----------------------|------------------------------------------------|
| `JWT_SECRET_KEY`      | Secret for JWT signing (required, app crashes at startup without it) |
| `GROQ_API_KEY`        | Groq API key for LLM inference                 |
| `ALLOWED_ORIGINS`     | Comma-separated list of allowed CORS origins (default: `http://localhost:3000,http://localhost:5173`) |

---

## 15. Security Summary

| Security Layer     | Mechanism                                                 | Location              |
|--------------------|-----------------------------------------------------------|-----------------------|
| Password hashing   | Argon2 (memory-hard, salted)                              | `core/auth.py`        |
| Authentication     | JWT HS256, 60-min expiry, verified on every request       | `core/auth.py`        |
| CORS               | Allowed origins enforced via middleware                   | `main.py`             |
| API Whitelist      | Database-driven per-endpoint/method firewall              | `main.py` middleware  |
| RBAC (API layer)   | Data scoping per role on every route                      | All API route files   |
| RBAC (AI layer)    | Chatbot only considers role-allowed endpoints in planning | `rag_engine/chat.py`  |
| Data isolation     | Employee sees only own data; manager sees only team data  | `core/auth.py` helpers + routes |
| Audit trail        | Every create/update/delete/login/prompt logged            | `core/auth.py` `log_action()` |
| LLM anti-hallucination | Strict prompt rules forbid inventing data             | `ANSWER_TEMPLATE` in `chat.py` |
| Locked fields      | Employees cannot change role/salary/hierarchy             | `EMPLOYEE_LOCKED_FIELDS` in `auth.py` |
| Leave quota check  | Backend validates annual leave balance before submitting  | `leave_requests.py`   |

---

*This document was generated from the source code of the ERP Chatbot project.*
