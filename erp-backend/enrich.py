"""
DB Enrichment Script — Construction ERP
Adds realistic data to empty tables:
- 35 tasks (critical/high on delayed projects)
- 15 leave requests (some overlapping critical tasks)
- 25 issues (safety/quality on high-risk projects)
- 20 timesheets
- 10 purchase orders
Run: python enrich_db.py
"""

import sqlite3
from datetime import datetime

DB_PATH = "erp_database.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# ════════════════════════════════════════════════════════════════════════════
# TASKS — 35 tasks across delayed/high-risk projects
# ════════════════════════════════════════════════════════════════════════════
tasks = [
    # P009 — Pont Autoroutier A1 (30 days late, High risk, 3 incidents)
    ("T006", "P009", "E008", "Coulage tabliers centraux", "Bétonner les tabliers des 3 travées centrales", "Critical", "In Progress", "2026-02-25", "E003", "2026-02-01", None, 40.0, 18.0),
    ("T007", "P009", "E022", "Installation équipements routiers", "Pose glissières, signalisation, éclairage", "Critical", "Todo", "2026-03-10", "E003", "2026-02-01", None, 30.0, None),
    ("T008", "P009", "E008", "Test de charge pont", "Essais de résistance structurelle", "High", "Todo", "2026-03-20", "E003", "2026-02-01", None, 16.0, None),
    ("T009", "P009", "E022", "Rapport géotechnique pile P3", "Analyser résultats sondages pile P3", "Critical", "In Progress", "2026-02-22", "E003", "2026-02-10", None, 12.0, 8.0),
    ("T010", "P009", "E008", "Réunion client Direction Autoroutière", "Point d'avancement mensuel avec client", "High", "Todo", "2026-02-28", "E003", "2026-02-15", None, 4.0, None),

    # P020 — Parc Industriel (25 days late, High risk, 4 incidents)
    ("T011", "P020", "E011", "Mise en conformité sécurité zone B", "Installer barrières et signalétique zone B", "Critical", "Todo", "2026-02-24", "E010", "2026-02-05", None, 20.0, None),
    ("T012", "P020", "E018", "Inspection structure hangar H3", "Contrôle soudures et assemblages", "Critical", "In Progress", "2026-02-26", "E010", "2026-02-08", None, 24.0, 10.0),
    ("T013", "P020", "E025", "Raccordement électrique bâtiment A", "Câblage haute tension et tableaux", "High", "Todo", "2026-03-05", "E010", "2026-02-10", None, 32.0, None),
    ("T014", "P020", "E011", "Audit sécurité externe", "Préparer documentation pour auditeur HSE", "Critical", "In Progress", "2026-02-23", "E010", "2026-02-12", None, 8.0, 3.0),
    ("T015", "P020", "E018", "Terrassement zone C", "Nivellement et compactage sol zone C", "High", "In Progress", "2026-03-01", "E010", "2026-02-01", None, 48.0, 20.0),

    # P004 — Complexe Sportif Sousse (20 days late, Medium risk)
    ("T016", "P004", "E012", "Pose revêtement terrain foot", "Gazon synthétique terrain principal", "Critical", "Todo", "2026-03-01", "E010", "2026-02-10", None, 24.0, None),
    ("T017", "P004", "E012", "Installation tribunes nord", "Montage gradins préfabriqués 2000 places", "High", "In Progress", "2026-03-15", "E010", "2026-02-05", None, 40.0, 12.0),
    ("T018", "P004", "E011", "Plomberie vestiaires", "Réseau eau chaude/froide vestiaires", "High", "Todo", "2026-02-28", "E010", "2026-02-12", None, 16.0, None),

    # P017 — Station d'Épuration (18 days late, Medium risk, 2 incidents)
    ("T019", "P017", "E011", "Installation filtres biologiques", "Pose membranes bioreacteur MBR", "Critical", "In Progress", "2026-03-05", "E010", "2026-02-01", None, 36.0, 14.0),
    ("T020", "P017", "E019", "Test étanchéité bassins", "Essais hydrauliques bassins primaires", "High", "Todo", "2026-03-10", "E010", "2026-02-05", None, 20.0, None),
    ("T021", "P017", "E019", "Formation opérateurs station", "Briefing équipe maintenance exploitation", "Medium", "Todo", "2026-03-20", "E010", "2026-02-10", None, 8.0, None),

    # P002 — Centre Commercial Carthage (15 days late, Low risk)
    ("T022", "P002", "E008", "Finitions façades nord et sud", "Pose panneaux aluminium et vitrages", "High", "In Progress", "2026-03-01", "E003", "2026-02-01", None, 32.0, 20.0),
    ("T023", "P002", "E022", "Installation ascenseurs", "Mise en service 6 ascenseurs + 2 monte-charges", "Critical", "Todo", "2026-03-10", "E003", "2026-02-10", None, 24.0, None),
    ("T024", "P002", "E008", "Réception provisoire client", "Préparation dossier réception avec Cartage Invest", "High", "Todo", "2026-03-20", "E003", "2026-02-15", None, 16.0, None),

    # P003 — Hôpital Régional Sfax (5 days late, High risk, 2 incidents)
    ("T025", "P003", "E011", "Installation salles opération", "Équipements chirurgie et bloc opératoire", "Critical", "In Progress", "2026-03-01", "E010", "2026-02-05", None, 40.0, 15.0),
    ("T026", "P003", "E019", "Réseau médical gaz", "Oxygène, vide médical, air comprimé", "Critical", "Todo", "2026-03-05", "E010", "2026-02-08", None, 28.0, None),
    ("T027", "P003", "E012", "Certification normes hospitalières", "Dossier conformité Ministry of Health", "High", "In Progress", "2026-03-15", "E010", "2026-02-10", None, 20.0, 5.0),

    # P011 — Hôtel 5 Étoiles Djerba (12 days late, Medium risk)
    ("T028", "P011", "E011", "Décoration suites présidentielles", "Mobilier haut de gamme et finitions luxe", "High", "In Progress", "2026-03-10", "E010", "2026-02-01", None, 48.0, 18.0),
    ("T029", "P011", "E016", "Installation piscine principale", "Revêtement et équipements filtration", "High", "Todo", "2026-03-05", "E010", "2026-02-10", None, 32.0, None),
    ("T030", "P011", "E011", "Mise en service spa et wellness", "Équipements sauna, hammam, jacuzzi", "Medium", "Todo", "2026-03-20", "E010", "2026-02-12", None, 24.0, None),

    # P001 — Résidence Les Palmiers (on time, good performance)
    ("T031", "P001", "E007", "Peinture appartements étages 5-8", "Application enduit et peinture finition", "Medium", "In Progress", "2026-03-01", "E003", "2026-02-10", None, 32.0, 10.0),
    ("T032", "P001", "E017", "Installation cuisine collective", "Équipements buanderie et cuisine résidence", "Medium", "Todo", "2026-03-10", "E003", "2026-02-12", None, 16.0, None),

    # P012 — Parking Multi-Étages (ahead of schedule)
    ("T033", "P012", "E007", "Marquage au sol niveaux 3-5", "Peinture places et signalétique", "Low", "In Progress", "2026-03-05", "E003", "2026-02-10", None, 12.0, 4.0),
    ("T034", "P012", "E021", "Système de guidage parking", "Installation capteurs et afficheurs", "High", "Todo", "2026-03-10", "E003", "2026-02-15", None, 20.0, None),

    # P007 — Usine Agroalimentaire (10 days late)
    ("T035", "P007", "E011", "Installation chaîne production", "Convoyeurs et équipements process", "Critical", "In Progress", "2026-03-01", "E010", "2026-02-01", None, 56.0, 20.0),
    ("T036", "P007", "E017", "Certification ISO 22000", "Dossier sécurité alimentaire et audit", "High", "Todo", "2026-03-15", "E010", "2026-02-10", None, 24.0, None),

    # P010 — Rénovation Médina Kairouan (ahead of schedule)
    ("T037", "P010", "E012", "Restauration mosaïques hammam", "Conservation et restauration mosaïques XVIe", "High", "In Progress", "2026-03-10", "E015", "2026-02-05", None, 40.0, 22.0),
    ("T038", "P010", "E016", "Consolidation remparts est", "Injection mortier chaux remparts historiques", "High", "Done", "2026-02-15", "E015", "2026-01-20", "2026-02-14", 32.0, 30.0),

    # P016 — Immeuble Résidentiel Nabeul
    ("T039", "P016", "E023", "Carrelage halls communs", "Pose marbre et granit espaces communs", "Medium", "Done", "2026-02-18", "E015", "2026-02-01", "2026-02-17", 20.0, 18.0),
    ("T040", "P016", "E016", "Raccordement STEG et SONEDE", "Formalités branchements eau et électricité", "High", "In Progress", "2026-02-28", "E015", "2026-02-10", None, 8.0, 2.0),
]

c.executemany("""
    INSERT OR IGNORE INTO tasks 
    (task_id, project_id, assigned_to, title, description, priority, status, 
     due_date, created_by, created_date, completed_date, estimated_hours, actual_hours)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
""", tasks)
print(f"✅ Tasks: {len(tasks)} inserted")

# ════════════════════════════════════════════════════════════════════════════
# LEAVE REQUESTS — 15 requests, some overlapping critical tasks
# ════════════════════════════════════════════════════════════════════════════
leaves = [
    # E011 (Rami Ferchichi) — en congé PENDANT qu'il a des tâches critiques T011, T014, T019, T025, T035
    ("LR001", "E011", "Rami Ferchichi", "Annual", "2026-02-23", "2026-02-27", 5, "Congé familial planifié", "Approved", "2026-02-10", "E010", "2026-02-11", "Approuvé avant assignation tâches urgentes"),

    # E008 (Salma Bouaziz) — en congé avec T006 critique en cours
    ("LR002", "E008", "Salma Bouaziz", "Annual", "2026-02-24", "2026-02-26", 3, "Vacances", "Approved", "2026-02-15", "E003", "2026-02-16", "Approuvé"),

    # E012 (Sonia Mejri) — en congé avec T016 critique P004
    ("LR003", "E012", "Sonia Mejri", "Sick", "2026-02-22", "2026-02-25", 4, "Arrêt maladie", "Approved", "2026-02-22", "E010", "2026-02-22", "Urgence médicale"),

    # E019 (Fares Ghanmi) — congé rejeté car T026 critique
    ("LR004", "E019", "Fares Ghanmi", "Annual", "2026-02-25", "2026-03-01", 5, "Voyage personnel", "Rejected", "2026-02-18", "E005", "2026-02-19", "Tâches critiques en cours sur P017 et P003"),

    # Others — normal requests
    ("LR005", "E007", "Youssef Mansour", "Annual", "2026-03-10", "2026-03-14", 5, "Vacances printemps", "Approved", "2026-02-20", "E003", "2026-02-20", "OK"),
    ("LR006", "E022", "Ines Hammami", "Annual", "2026-03-01", "2026-03-03", 3, "Événement familial", "Approved", "2026-02-18", "E008", "2026-02-19", "Approuvé"),
    ("LR007", "E017", "Bilel Ltaief", "Sick", "2026-02-19", "2026-02-21", 3, "Grippe", "Approved", "2026-02-19", "E005", "2026-02-19", "Certificat médical reçu"),
    ("LR008", "E016", "Hela Dridi", "Annual", "2026-03-15", "2026-03-20", 6, "Congé annuel", "Approved", "2026-02-20", "E015", "2026-02-21", "Approuvé"),
    ("LR009", "E023", "Mehdi Abidi", "Annual", "2026-03-05", "2026-03-07", 3, "Mariage frère", "Approved", "2026-02-20", "E016", "2026-02-21", "Congé exceptionnel"),
    ("LR010", "E013", "Tarek Bouslama", "Annual", "2026-03-01", "2026-03-05", 5, "Vacances", "Approved", "2026-02-15", "E004", "2026-02-16", "Approuvé"),
    ("LR011", "E006", "Amira Nasri", "Annual", "2026-03-10", "2026-03-12", 3, "Congé annuel", "Approved", "2026-02-18", "E002", "2026-02-19", "OK"),
    ("LR012", "E025", "Khaled Jomaa", "Annual", "2026-02-28", "2026-03-02", 3, "Congé familial", "Rejected", "2026-02-20", "E018", "2026-02-20", "Projet P020 en retard critique"),
    ("LR013", "E018", "Asma Ben Youssef", "Annual", "2026-03-20", "2026-03-25", 6, "Vacances", "Approved", "2026-02-20", "E005", "2026-02-21", "Approuvé"),
    ("LR014", "E009", "Hichem Zarrouk", "Annual", "2026-03-08", "2026-03-12", 5, "Congé annuel", "Approved", "2026-02-18", "E002", "2026-02-19", "Approuvé"),
    ("LR015", "E024", "Wafa Slimani", "Annual", "2026-03-15", "2026-03-18", 4, "Voyage famille", "Approved", "2026-02-20", "E002", "2026-02-21", "OK"),
]

c.executemany("""
    INSERT OR IGNORE INTO leave_requests
    (request_id, employee_id, employee_name, leave_type, start_date, end_date,
     total_days, reason, status, requested_date, reviewed_by, reviewed_date, review_comment)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
""", leaves)
print(f"✅ Leave requests: {len(leaves)} inserted")

# ════════════════════════════════════════════════════════════════════════════
# ISSUES — 25 issues on high-risk projects
# ════════════════════════════════════════════════════════════════════════════
issues = [
    # P009 — Pont Autoroutier A1 (3 incidents)
    ("IS001", "P009", "E008", "Fissures détectées pile P3", "Microfissures observées lors inspection pile P3, analyse en cours", "High", "Safety", "In Progress", "E022", "2026-02-10", None, None),
    ("IS002", "P009", "E022", "Retard livraison aciers charpente", "Fournisseur acier annonce 3 semaines de délai supplémentaire", "High", "Delay", "Open", "E003", "2026-02-12", None, None),
    ("IS003", "P009", "E008", "Accident opérateur grue", "Chute d'objet depuis grue, opérateur blessé légèrement", "Critical", "Safety", "Resolved", "E003", "2026-01-28", "2026-02-05", "Opérateur soigné, procédure revue, formation complémentaire effectuée"),

    # P020 — Parc Industriel (4 incidents)
    ("IS004", "P020", "E011", "Incident électrique bâtiment B", "Court-circuit lors câblage, 2 ouvriers légèrement brûlés", "Critical", "Safety", "Resolved", "E010", "2026-01-15", "2026-01-25", "Habilitations vérifiées, nouveau protocole consignation"),
    ("IS005", "P020", "E018", "Effondrement échafaudage partiel", "Section échafaudage zone C cédée, sans blessé", "Critical", "Safety", "Resolved", "E010", "2026-01-20", "2026-02-01", "Échafaudage remplacé, inspection générale effectuée"),
    ("IS006", "P020", "E025", "Non-conformité béton hangar H2", "Résistance béton inférieure aux spécifications (25MPa vs 30MPa requis)", "High", "Quality", "In Progress", "E011", "2026-02-05", None, None),
    ("IS007", "P020", "E011", "Dépassement budget zone industrielle", "Coûts terrassement zone C dépassent estimation de 15%", "High", "Budget", "Open", "E010", "2026-02-15", None, None),

    # P003 — Hôpital Régional Sfax (2 incidents)
    ("IS008", "P003", "E019", "Retard livraison équipements médicaux", "Fournisseur équipements IRM annonce délai 6 semaines", "High", "Delay", "Open", "E011", "2026-02-15", None, None),
    ("IS009", "P003", "E011", "Problème étanchéité toiture bloc A", "Infiltrations eau détectées bloc opératoire sous construction", "High", "Quality", "In Progress", "E019", "2026-02-08", None, None),

    # P017 — Station d'Épuration (2 incidents)
    ("IS010", "P017", "E019", "Contamination accidentelle bassin test", "Déversement produit chimique lors essai, zone isolée", "Critical", "Safety", "Resolved", "E010", "2026-01-30", "2026-02-10", "Bassin vidangé, dépollution effectuée, rapport ANPE soumis"),
    ("IS011", "P017", "E011", "Retard livraison membranes MBR", "Fournisseur européen annonce rupture stock 4 semaines", "High", "Delay", "Open", "E010", "2026-02-14", None, None),

    # P011 — Hôtel 5 Étoiles Djerba (2 incidents)
    ("IS012", "P011", "E011", "Défaut carrelage piscine principale", "Fissures carrelage piscine détectées après pose, reprise nécessaire", "High", "Quality", "In Progress", "E016", "2026-02-10", None, None),
    ("IS013", "P011", "E016", "Incident chantier toiture", "Ouvrier glissade toiture, contusion, arrêt 3 jours", "High", "Safety", "Resolved", "E010", "2026-01-25", "2026-02-02", "Protocole sécurité toiture renforcé"),

    # P004 — Complexe Sportif Sousse (1 incident)
    ("IS014", "P004", "E012", "Retard livraison gazon synthétique", "Fournisseur espagnol délai 3 semaines supplémentaires", "Medium", "Delay", "Open", "E010", "2026-02-18", None, None),

    # P007 — Usine Agroalimentaire (1 incident)
    ("IS015", "P007", "E017", "Non-conformité revêtement sol atelier", "Sol atelier ne respecte pas normes HACCP alimentaire", "High", "Quality", "In Progress", "E011", "2026-02-12", None, None),

    # P002 — Centre Commercial Carthage
    ("IS016", "P002", "E008", "Retard livraison vitrages façade", "Verrier annonce délai 2 semaines, impact sur planning", "Medium", "Delay", "Open", "E003", "2026-02-16", None, None),

    # P001 — Résidence Les Palmiers
    ("IS017", "P001", "E007", "Fissure façade niveau 3", "Microfissure enduit façade nord niveau 3, expertise requise", "Low", "Quality", "Open", "E003", "2026-02-18", None, None),

    # P015 — Centre Culturel Monastir (High risk in planning)
    ("IS018", "P015", "E003", "Retard permis de construire", "Mairie Monastir n'a pas encore délivré permis définitif", "High", "Delay", "Open", "E003", "2026-02-01", None, None),

    # P012 — Parking (ahead of schedule, minor issues)
    ("IS019", "P012", "E007", "Défaut peinture marquage sol N2", "Peinture écaillée niveau 2 après application, refaire", "Low", "Quality", "Resolved", "E021", "2026-02-05", "2026-02-10", "Reprise avec peinture antidérapante certifiée"),

    # Cross-project issues
    ("IS020", "P020", "E010", "Manque personnel qualifié zone C", "Besoin 5 soudeurs certifiés supplémentaires urgent", "High", "Technical", "Open", "E005", "2026-02-16", None, None),
    ("IS021", "P009", "E003", "Problème géotechnique imprévu", "Sol argileux découvert zone culée est, études complémentaires", "High", "Technical", "In Progress", "E008", "2026-02-08", None, None),
    ("IS022", "P003", "E010", "Surcoût équipements médicaux", "Prix équipements IRM et scanner +18% vs devis initial", "High", "Budget", "Open", "E002", "2026-02-14", None, None),
    ("IS023", "P017", "E010", "Problème raccordement ONAS", "ONAS demande modification point de rejet, études supplémentaires", "High", "Technical", "In Progress", "E019", "2026-02-10", None, None),
    ("IS024", "P020", "E025", "Détérioration route accès chantier", "Route communale endommagée par engins lourds, plainte commune", "Medium", "Other", "Open", "E005", "2026-02-17", None, None),
    ("IS025", "P011", "E010", "Retard agrément hôtelier", "Ministère tourisme demande documents complémentaires", "Medium", "Delay", "Open", "E016", "2026-02-15", None, None),
]

c.executemany("""
    INSERT OR IGNORE INTO issues
    (issue_id, project_id, reported_by, title, description, severity, category,
     status, assigned_to, created_date, resolved_date, resolution_notes)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
""", issues)
print(f"✅ Issues: {len(issues)} inserted")

# ════════════════════════════════════════════════════════════════════════════
# TIMESHEETS — 20 entries
# ════════════════════════════════════════════════════════════════════════════
timesheets = [
    ("TS001", "E007", "P001", "2026-02-17", 8.0, "Peinture appartements étages 5-6", 1, 45.0, 1, "E003", "2026-02-18"),
    ("TS002", "E007", "P001", "2026-02-18", 8.0, "Peinture appartements étage 7", 1, 45.0, 1, "E003", "2026-02-19"),
    ("TS003", "E008", "P009", "2026-02-17", 10.0, "Supervision coulage béton pile P4", 1, 55.0, 1, "E003", "2026-02-18"),
    ("TS004", "E008", "P009", "2026-02-18", 9.0, "Contrôle ferraillage tablier central", 1, 55.0, 1, "E003", "2026-02-19"),
    ("TS005", "E011", "P020", "2026-02-17", 10.0, "Installation barrières sécurité zone B", 1, 50.0, 1, "E010", "2026-02-18"),
    ("TS006", "E011", "P003", "2026-02-18", 8.0, "Coordination installation bloc opératoire", 1, 50.0, 1, "E010", "2026-02-19"),
    ("TS007", "E012", "P004", "2026-02-17", 8.0, "Suivi pose tribunes nord", 1, 45.0, 1, "E010", "2026-02-18"),
    ("TS008", "E017", "P001", "2026-02-17", 8.0, "Installation équipements cuisine collective", 1, 42.0, 1, "E005", "2026-02-18"),
    ("TS009", "E017", "P007", "2026-02-18", 8.0, "Supervision installation chaîne production", 1, 42.0, 1, "E005", "2026-02-19"),
    ("TS010", "E018", "P020", "2026-02-17", 10.0, "Inspection structure hangar H3", 1, 48.0, 1, "E005", "2026-02-18"),
    ("TS011", "E019", "P017", "2026-02-17", 8.0, "Tests étanchéité bassin secondaire", 1, 42.0, 1, "E005", "2026-02-18"),
    ("TS012", "E019", "P003", "2026-02-18", 8.0, "Installation réseau oxygène médical", 1, 42.0, 1, "E005", "2026-02-19"),
    ("TS013", "E022", "P009", "2026-02-17", 9.0, "Rapport géotechnique pile P3", 1, 50.0, 1, "E008", "2026-02-18"),
    ("TS014", "E022", "P002", "2026-02-18", 8.0, "Pose panneaux aluminium façade nord", 1, 50.0, 1, "E008", "2026-02-19"),
    ("TS015", "E016", "P011", "2026-02-17", 8.0, "Décoration suites présidentielles 5ème étage", 1, 45.0, 1, "E015", "2026-02-18"),
    ("TS016", "E023", "P016", "2026-02-17", 8.0, "Carrelage hall commun RDC", 1, 42.0, 1, "E016", "2026-02-18"),
    ("TS017", "E021", "P012", "2026-02-18", 6.0, "Configuration système guidage parking", 1, 48.0, 1, "E003", "2026-02-19"),
    ("TS018", "E025", "P020", "2026-02-17", 10.0, "Terrassement zone C secteur nord", 1, 40.0, 1, "E018", "2026-02-18"),
    ("TS019", "E008", "P002", "2026-02-19", 8.0, "Pose vitrages façade sud", 1, 55.0, 1, "E003", "2026-02-20"),
    ("TS020", "E011", "P007", "2026-02-19", 9.0, "Installation convoyeurs ligne production A", 1, 50.0, 1, "E010", "2026-02-20"),
]

c.executemany("""
    INSERT OR IGNORE INTO timesheets
    (timesheet_id, employee_id, project_id, date, hours_worked, task_description,
     billable, hourly_rate, is_approved, approved_by, approved_date)
    VALUES (?,?,?,?,?,?,?,?,?,?,?)
""", timesheets)
print(f"✅ Timesheets: {len(timesheets)} inserted")

# ════════════════════════════════════════════════════════════════════════════
# PURCHASE ORDERS — 10 orders
# ════════════════════════════════════════════════════════════════════════════
purchase_orders = [
    ("PO001", "P009", "S001", "2026-02-01", "2026-02-20", 285000.0, "Delivered", "Ciment Portland 500T, Acier HA 80T", "E008", "E003", "Livraison chantier pont A1"),
    ("PO002", "P020", "S003", "2026-02-05", "2026-03-01", 450000.0, "Pending", "Location grue 200T 3 mois", "E011", "E010", "Engin pour hangar H3"),
    ("PO003", "P003", "S004", "2026-02-08", "2026-03-15", 180000.0, "Approved", "Installation électrique blocs A et B hôpital", "E019", "E010", "Câblage haute tension"),
    ("PO004", "P002", "S002", "2026-02-10", "2026-02-28", 95000.0, "Delivered", "Matériaux finitions façades: aluminium, joints", "E008", "E003", "Façades centre commercial"),
    ("PO005", "P017", "S005", "2026-02-12", "2026-03-10", 65000.0, "Approved", "Tuyauterie PEHD DN400, vannes industrielles", "E019", "E010", "Réseau hydraulique station"),
    ("PO006", "P004", "S002", "2026-02-14", "2026-03-20", 120000.0, "Pending", "Gazon synthétique FIFA Quality Pro 8000m2", "E012", "E010", "Terrain principal complexe sportif"),
    ("PO007", "P009", "S003", "2026-02-15", "2026-03-05", 75000.0, "Approved", "Location équipements topographie et contrôle", "E022", "E003", "Mesures et contrôles pont"),
    ("PO008", "P020", "S001", "2026-02-16", "2026-03-01", 320000.0, "Pending", "Béton prêt emploi C30/37 2500m3", "E018", "E010", "Dallage zone industrielle C"),
    ("PO009", "P011", "S004", "2026-02-17", "2026-03-15", 95000.0, "Approved", "Installation électrique hôtel: chambres et communs", "E016", "E010", "Câblage 200 chambres"),
    ("PO010", "P001", "S005", "2026-02-18", "2026-03-05", 28000.0, "Approved", "Plomberie sanitaires appartements étages 6-10", "E007", "E003", "Résidence Les Palmiers"),
]

c.executemany("""
    INSERT OR IGNORE INTO purchase_orders
    (po_id, project_id, supplier_id, order_date, delivery_date, total_amount,
     status, items, created_by, approved_by, notes)
    VALUES (?,?,?,?,?,?,?,?,?,?,?)
""", purchase_orders)
print(f"✅ Purchase orders: {len(purchase_orders)} inserted")

# ════════════════════════════════════════════════════════════════════════════
# VERIFY
# ════════════════════════════════════════════════════════════════════════════
conn.commit()
conn.close()

conn2 = sqlite3.connect(DB_PATH)
c2 = conn2.cursor()
for table in ["tasks", "leave_requests", "issues", "timesheets", "purchase_orders"]:
    c2.execute(f"SELECT COUNT(*) FROM {table}")
    print(f"  {table}: {c2.fetchone()[0]} rows")
conn2.close()

print("\n✅ DB enrichment complete!")
print("Key scenarios now available:")
print("  - E011 (Rami) en congé 23-27 fév avec 5 tâches critiques assignées")
print("  - E008 (Salma) en congé 24-26 fév avec tâche critique T006 P009")
print("  - E012 (Sonia) en congé maladie avec tâche critique T016 P004")
print("  - P009: 30j retard + 3 issues Safety + tâches critiques")
print("  - P020: 25j retard + 4 incidents + issues Budget/Quality")
print("  - 10 purchase orders avec statuts variés")