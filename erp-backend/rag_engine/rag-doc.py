"""
RAG Document Generator for Construction ERP
Generates static policy/procedure/glossaire/email documents only.
Live data (projects, employees, KPIs, etc.) is handled by the LLM planner via API endpoints.
Run once: python generate_rag_documents.py
"""

import os

# ── Create folder structure ──────────────────────────────────────────────────
folders = [
    "rag_documents/policies",
    "rag_documents/procedures",
    "rag_documents/glossaire",
    "rag_documents/emails",
]
for folder in folders:
    os.makedirs(folder, exist_ok=True)

def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ {path} ({len(content):,} chars)")


# ════════════════════════════════════════════════════════════════════════════
# 1. POLICIES
# ════════════════════════════════════════════════════════════════════════════
write("rag_documents/policies/avantages_sociaux.txt", """
AVANTAGES SOCIAUX ET RÉMUNÉRATION
Construction Tunisie — Document RH officiel
===========================================

1. AVANTAGES SOCIAUX
- Mutuelle santé: prise en charge à 70% par l'entreprise
- Transport: indemnité mensuelle selon la distance domicile-travail
- Panier repas: 8 EUR/jour pour le personnel sur chantier
- Prime de fin d'année: équivalent à 1 mois de salaire (selon performance)
- Prime de chantier: 200 EUR/mois pour le personnel affecté sur chantier à plein temps

2. ÉVALUATION ET PERFORMANCE
- Évaluation annuelle de performance en décembre
- Entretien mi-parcours en juin
- Les objectifs sont définis en début d'année avec le manager
- Les KPIs de chaque projet impactent l'évaluation des chefs de projet
""")

write("rag_documents/policies/politique_conges.txt", """
POLITIQUE DE GESTION DES CONGÉS
Construction Tunisie ERP — Document RH officiel
================================================
Version: 2.0 | Date: Janvier 2026

1. TYPES DE CONGÉS ET DURÉES
------------------------------
1.1 Congé annuel payé
    - Tous les employés permanents ont droit à 35 jours ouvrables de congé annuel.
    - Les congés non pris ne peuvent pas être reportés à l'année suivante sauf accord écrit du DRH.
    - Le calcul se fait sur la base de l'année civile (1er janvier au 31 décembre).

1.2 Congé maladie
    - Durée maximale: 30 jours par an avec maintien du salaire complet.
    - Au-delà de 3 jours consécutifs, un certificat médical est obligatoire.
    - Au-delà de 30 jours, le dossier est transmis à la CNSS pour étude.

1.3 Congé de maternité
    - Durée: 60 jours calendaires (30 jours avant l'accouchement + 30 jours après).
    - Salaire maintenu à 100% pendant toute la durée.
    - Extension possible de 15 jours sur présentation d'un certificat médical.

1.4 Congé de paternité
    - Durée: 3 jours ouvrables à partir de la naissance de l'enfant.
    - À prendre dans les 15 jours suivant la naissance.

1.5 Congé exceptionnel (événements familiaux)
    - Mariage de l'employé: 5 jours
    - Mariage d'un enfant: 2 jours
    - Décès du conjoint ou d'un enfant: 5 jours
    - Décès d'un parent (père, mère): 3 jours
    - Décès d'un beau-parent: 2 jours
    - Décès d'un frère ou sœur: 1 jour
    - Circoncision d'un fils: 1 jour

1.6 Congé sans solde
    - Accordé exceptionnellement pour des raisons personnelles graves.
    - Durée maximale: 30 jours par an.
    - Doit être approuvé par le directeur de département et le DRH.

2. PROCÉDURE DE DEMANDE DE CONGÉ
----------------------------------
Étape 1: L'employé soumet sa demande via le système ERP (module Congés) au moins:
    - 15 jours à l'avance pour les congés de 5 jours et plus.
    - 3 jours à l'avance pour les congés de moins de 5 jours.
    - Immédiatement pour les congés maladie et événements familiaux.

Étape 2: Le manager direct examine la demande dans un délai de 48 heures.
    - Il vérifie la disponibilité de l'équipe et l'impact sur les projets en cours.
    - Il approuve ou rejette la demande avec commentaire obligatoire en cas de rejet.

Étape 3: Le système ERP notifie automatiquement l'employé de la décision.

Étape 4: En cas de désaccord, l'employé peut faire appel auprès du DRH.

3. RÈGLES IMPORTANTES
----------------------
- Un employé ne peut pas partir en congé si des tâches critiques lui sont assignées, sauf arrangement préalable.
- La direction peut rappeler un employé en congé en cas de force majeure (urgence sur chantier, etc.).
- Toute absence non justifiée dans les 24h est considérée comme absence non autorisée.
- Trois absences non autorisées consécutives peuvent mener à une procédure disciplinaire.

4. SOLDE DE CONGÉS
-------------------
- Consultable à tout moment dans le système ERP (profil employé).
- Le solde est mis à jour en temps réel après chaque approbation.
- En fin d'année, le solde non utilisé est perdu (pas de report sauf exception approuvée).

5. CONTACTS RH
---------------
- Département RH: rh@construction-tn.com
- DRH Direct: +216 25 678 901
- Système ERP: Rubrique "Mes Congés" dans le tableau de bord

DOCUMENT OFFICIEL — Construction Tunisie
""")

write("rag_documents/policies/securite_chantier.txt", """
POLITIQUE DE SÉCURITÉ ET SANTÉ AU TRAVAIL SUR CHANTIER
Construction Tunisie ERP — Document HSE officiel
========================================================
Version: 3.1 | Date: Janvier 2026

1. ÉQUIPEMENTS DE PROTECTION INDIVIDUELLE (EPI) OBLIGATOIRES
--------------------------------------------------------------
Tout personnel travaillant sur un chantier doit obligatoirement porter:
- Casque de protection (norme EN 397)
- Chaussures de sécurité (norme EN ISO 20345, embout acier)
- Gilet haute visibilité (classe 3)
- Gants de protection adaptés au travail effectué
- Lunettes de protection lors des travaux de découpe, soudure, ou projection
- Harnais de sécurité pour tout travail en hauteur supérieur à 2 mètres
- Protège-oreilles lors des travaux bruyants (> 85 dB)
- Masque anti-poussière (FFP2 minimum) lors des travaux poussiéreux

Le non-port d'EPI est passible d'un avertissement au premier manquement
et d'une sanction disciplinaire en cas de récidive.

2. PROCÉDURE EN CAS D'ACCIDENT SUR CHANTIER
---------------------------------------------
2.1 Premiers secours immédiats (0-5 minutes)
    - Alerter immédiatement: APPEL D'URGENCE: 190 (SAMU) / 198 (Protection Civile)
    - Sécuriser la zone pour éviter tout accident secondaire
    - Ne pas déplacer un blessé sauf danger immédiat
    - Administrer les premiers secours si vous êtes formé

2.2 Notification interne (dans l'heure)
    - Appeler le Chef de chantier immédiatement
    - Le Chef de chantier appelle le Chef de projet
    - Le Chef de projet informe le Responsable HSE: +216 20 HSE 001
    - Remplir le formulaire d'incident dans le système ERP (module Issues)

2.3 Déclaration officielle (dans les 24 heures)
    - Tout accident avec arrêt de travail doit être déclaré à la CNSS dans les 24h
    - Un rapport d'incident complet doit être soumis via le système ERP
    - Une enquête interne est déclenchée automatiquement pour tout accident grave

2.4 Retour au travail
    - Autorisation médicale obligatoire avant reprise après tout accident
    - Visite de reprise avec le médecin du travail si arrêt > 8 jours

3. RÈGLES DE SÉCURITÉ GÉNÉRALES
---------------------------------
- Interdit de consommer de l'alcool ou des substances psychoactives sur chantier
- Vitesse limitée à 10 km/h sur toute zone de chantier pour les véhicules
- Tout engin doit être inspecté avant utilisation (check-list quotidienne)
- Les zones de fouille et tranchées doivent être balisées et éclairées
- Stockage correct des matériaux: pas de matériaux instables en hauteur
- Les extincteurs doivent être accessibles et vérifiés tous les 6 mois
- Plan d'évacuation affiché à l'entrée de chaque chantier

4. TRAVAUX EN HAUTEUR
----------------------
- Interdit de travailler en hauteur par vent > 60 km/h
- Inspection quotidienne des échafaudages par le chef de chantier
- Filets de protection obligatoires pour travaux > 3 mètres
- Lignes de vie installées pour travaux sur toiture

5. GESTION DES PRODUITS DANGEREUX
-----------------------------------
- Fiches de données de sécurité (FDS) disponibles pour tout produit chimique
- Stockage séparé des produits inflammables (local ventilé, anti-feu)
- Récipients correctement étiquetés obligatoirement
- Formation à la manipulation des produits dangereux obligatoire

6. FORMATION SÉCURITÉ
----------------------
- Formation sécurité initiale obligatoire pour tout nouveau employé (2 jours)
- Recyclage annuel obligatoire (1/2 journée)
- Formation premiers secours (PSC1) recommandée pour tout chef de chantier
- Les formations sont enregistrées dans le profil employé sur l'ERP

7. INDICATEURS HSE SUIVIS
--------------------------
- Nombre d'accidents avec arrêt (objectif: 0)
- Nombre d'incidents sans arrêt
- Taux de fréquence (TF) = Accidents × 1,000,000 / Heures travaillées
- Taux de gravité (TG) = Jours perdus × 1,000 / Heures travaillées
- Ces indicateurs sont suivis dans les KPIs de chaque projet sur l'ERP

DOCUMENT HSE OFFICIEL — Construction Tunisie
Responsable HSE: Département Sécurité | securite@construction-tn.com
""")

write("rag_documents/policies/reglement_interieur.txt", """
RÈGLEMENT INTÉRIEUR
Construction Tunisie — Document RH officiel
============================================
Version: 2.5 | Date: Janvier 2026

1. HORAIRES DE TRAVAIL
-----------------------
1.1 Horaires standard (bureaux et siège)
    - Lundi au vendredi: 08h00 – 17h00
    - Pause déjeuner: 12h30 – 13h30
    - Durée hebdomadaire: 40 heures

1.2 Horaires chantier
    - Lundi au samedi: 07h00 – 16h00
    - Pause: 12h00 – 13h00
    - Les heures supplémentaires sont payées à 125% (jours ouvrables) et 150% (vendredi/samedi)
    - Travail le dimanche: 175% du taux horaire normal

1.3 Pointage
    - L'enregistrement des heures se fait via le système ERP (timesheets)
    - Toute heure non enregistrée dans les 48h est perdue
    - Les chefs de chantier valident les heures de leur équipe chaque semaine

2. CODE VESTIMENTAIRE ET COMPORTEMENT
--------------------------------------
2.1 Tenue professionnelle
    - Tenue soignée et propre obligatoire pour tout le personnel
    - EPI obligatoires sur les chantiers (voir politique sécurité)
    - Le port de la tenue de travail fournie par l'entreprise est obligatoire sur chantier

2.2 Comportement professionnel
    - Respect mutuel entre tous les employés, sans discrimination
    - Comportement respectueux envers les clients et visiteurs
    - Toute forme de harcèlement (moral ou sexuel) est strictement interdite
    - L'utilisation du téléphone personnel est limitée aux pauses

3. UTILISATION DES RESSOURCES DE L'ENTREPRISE
-----------------------------------------------
3.1 Véhicules et équipements
    - Les véhicules de service ne peuvent être utilisés qu'à des fins professionnelles
    - Tout dommage doit être signalé immédiatement
    - Le système ERP trace toutes les affectations d'équipements

3.2 Système informatique et ERP
    - Chaque employé a un compte personnel et confidentiel
    - Partager ses identifiants est strictement interdit
    - L'accès aux données est limité selon le rôle (employé / manager / CEO)
    - Toute tentative d'accès non autorisé est un motif de licenciement

3.3 Téléphone et communication
    - La messagerie professionnelle doit être consultée chaque jour ouvrable
    - Les e-mails professionnels sont propriété de l'entreprise

4. ÉVALUATION ET PERFORMANCE
------------------------------
- Évaluation annuelle de performance en décembre
- Entretien mi-parcours en juin
- Les objectifs sont définis en début d'année avec le manager
- Les KPIs de chaque projet impactent l'évaluation des chefs de projet

5. PROCÉDURE DISCIPLINAIRE
----------------------------
Niveaux de sanctions:
  Niveau 1 — Avertissement écrit: retard répété, absence non justifiée courte durée
  Niveau 2 — Blâme: faute professionnelle légère, manquement aux règles de sécurité
  Niveau 3 — Mise à pied (1-5 jours sans solde): faute grave
  Niveau 4 — Licenciement pour faute grave: vol, fraude, harcèlement, mise en danger d'autrui

6. AVANTAGES SOCIAUX
---------------------
- Mutuelle santé: prise en charge à 70% par l'entreprise
- Transport: indemnité mensuelle selon la distance domicile-travail
- Panier repas: 8 EUR/jour pour le personnel sur chantier
- Prime de fin d'année: équivalent à 1 mois de salaire (selon performance)
- Prime de chantier: 200 EUR/mois pour le personnel affecté sur chantier à plein temps

DOCUMENT OFFICIEL — Construction Tunisie
DRH: rh@construction-tn.com | Tel: +216 25 678 901
""")

write("rag_documents/policies/procedure_achats.txt", """
PROCÉDURE DE GESTION DES ACHATS ET FOURNISSEURS
Construction Tunisie ERP — Document Finance officiel
=====================================================
Version: 1.8 | Date: Janvier 2026

1. PROCESSUS D'ACHAT
---------------------
1.1 Seuils d'approbation
    - Moins de 1,000 EUR: Chef de chantier peut approuver directement
    - 1,000 à 10,000 EUR: Chef de projet doit approuver
    - 10,000 à 50,000 EUR: Directeur Financier doit approuver
    - Plus de 50,000 EUR: CEO doit approuver

1.2 Processus standard
    Étape 1: Expression du besoin via le système ERP (bon de commande)
    Étape 2: Sélection du fournisseur (priorité aux fournisseurs référencés)
    Étape 3: Demande de devis (minimum 3 devis pour > 5,000 EUR)
    Étape 4: Validation selon seuils ci-dessus
    Étape 5: Émission du bon de commande officiel via ERP
    Étape 6: Réception et contrôle qualité
    Étape 7: Validation de la facture et paiement

2. RÉFÉRENCEMENT D'UN NOUVEAU FOURNISSEUR
-------------------------------------------
Pour ajouter un fournisseur dans le système:
    1. Remplir le formulaire de référencement (disponible sur ERP)
    2. Fournir: extrait de registre du commerce + attestation fiscale + références clients
    3. Validation par le service Achats dans les 5 jours ouvrables
    4. Visite de qualification pour les fournisseurs > 100,000 EUR/an

3. DÉLAIS DE PAIEMENT
----------------------
- Fournisseurs locaux: 30 jours fin de mois
- Fournisseurs internationaux: 45 jours
- Pénalités de retard de paiement: 8% annuel
- Escompte pour paiement comptant: négocié au cas par cas

4. GESTION DES LITIGES FOURNISSEURS
-------------------------------------
- Tout litige est signalé dans le système ERP (module Issues, catégorie "Autre")
- Le service Achats a 5 jours pour répondre
- Les litiges non résolus sont escaladés au CFO

DOCUMENT OFFICIEL — Construction Tunisie
Service Achats: achats@construction-tn.com
""")


# ════════════════════════════════════════════════════════════════════════════
# 2. PROCEDURES
# ════════════════════════════════════════════════════════════════════════════

write("rag_documents/procedures/gestion_incidents.txt", """
PROCÉDURE DE GESTION DES INCIDENTS ET PROBLÈMES
Construction Tunisie ERP — Document Qualité
==============================================
Version: 1.5 | Date: Janvier 2026

1. DÉFINITION ET CATÉGORIES D'INCIDENTS
-----------------------------------------
Un incident est tout événement non planifié qui affecte ou pourrait affecter
la qualité, le délai, le budget ou la sécurité d'un projet.

Catégories dans le système ERP:
  - Safety (Sécurité): accidents, quasi-accidents, conditions dangereuses
  - Quality (Qualité): non-conformités, défauts de construction, rebus
  - Delay (Retard): événements causant des retards sur le planning
  - Budget (Budget): dépassements de coûts non prévus
  - Technical (Technique): pannes, problèmes techniques, défaillances
  - Other (Autre): tout incident ne rentrant pas dans les catégories ci-dessus

Niveaux de sévérité:
  - Low (Faible): impact mineur, résolution locale possible
  - Medium (Moyen): impact modéré, nécessite l'attention du chef de projet
  - High (Élevé): impact significatif, nécessite escalade au management
  - Critical (Critique): impact majeur sur la sécurité ou la viabilité du projet

2. PROCÉDURE DE DÉCLARATION
-----------------------------
Tout employé ayant connaissance d'un incident DOIT le déclarer dans l'ERP.
La non-déclaration d'un incident est considérée comme une faute professionnelle.

Étape 1: Aller dans l'ERP → Module "Issues/Incidents"
Étape 2: Créer un nouvel incident avec:
  - Titre clair et descriptif
  - Projet concerné
  - Catégorie et sévérité
  - Description détaillée (qui, quoi, quand, où, comment)
  - Attachement de photos si possible

Étape 3: Le système notifie automatiquement le chef de projet
Étape 4: Pour les incidents Critical/High → notification immédiate au CEO

3. DÉLAIS DE RÉSOLUTION CIBLES
--------------------------------
  - Critical: résolution ou plan d'action sous 24 heures
  - High: résolution sous 72 heures
  - Medium: résolution sous 7 jours
  - Low: résolution sous 30 jours

4. SUIVI ET CLÔTURE
---------------------
- Tout incident ouvert fait l'objet d'un suivi hebdomadaire en réunion de projet
- La clôture d'un incident nécessite une note de résolution dans l'ERP
- Les incidents Critical font l'objet d'une analyse des causes racines (Root Cause Analysis)
- Un rapport mensuel des incidents est généré automatiquement par l'ERP

5. ANALYSE ET AMÉLIORATION CONTINUE
-------------------------------------
- Les données d'incidents sont analysées trimestriellement
- Les projets avec plus de 3 incidents High/Critical en un mois déclenchent un audit
- Les leçons apprises sont partagées avec toutes les équipes

DOCUMENT QUALITÉ — Construction Tunisie
Responsable Qualité: qualite@construction-tn.com
""")

write("rag_documents/procedures/onboarding.txt", """
PROCÉDURE D'INTÉGRATION DES NOUVEAUX EMPLOYÉS (ONBOARDING)
Construction Tunisie ERP — Document RH
===========================================================
Version: 1.3 | Date: Janvier 2026

1. AVANT L'ARRIVÉE (J-7)
--------------------------
- Création du compte ERP par le service informatique
- Préparation du badge et des accès chantier
- Attribution d'un mentor (employé expérimenté du même département)
- Envoi du livret d'accueil par email

2. PREMIER JOUR (J0)
---------------------
Matin:
  08h00 — Accueil par le DRH et signature du contrat
  09h00 — Remise du badge, EPI, matériel informatique
  10h00 — Visite des locaux et présentation aux équipes
  11h00 — Formation ERP (création compte, navigation de base)

Après-midi:
  13h30 — Réunion avec le manager direct
  14h30 — Formation Sécurité obligatoire (2 heures)
  16h30 — Questions/Réponses avec le mentor

3. PREMIÈRE SEMAINE (J1-J7)
-----------------------------
- Formation approfondie sur le système ERP (2 jours)
- Visite des chantiers actifs avec un chef de projet
- Lecture des documents politiques (remis physiquement et accessibles sur ERP)
- Rencontre avec les fournisseurs principaux si pertinent
- Participation aux réunions d'équipe en mode observateur

4. PREMIER MOIS (J8-J30)
--------------------------
- Prise en main progressive des responsabilités
- Réunion hebdomadaire avec le mentor
- Accès complet au système ERP selon le rôle défini
- Point de suivi à J30 avec le manager et le DRH

5. PÉRIODE D'ESSAI (3-6 mois selon contrat)
---------------------------------------------
- Évaluation à mi-parcours (J45)
- Évaluation finale avant titularisation
- Rapport du manager transmis au DRH

6. ACCÈS SYSTÈME ERP PAR RÔLE
--------------------------------
  Rôle "employee":
    - Voir ses propres tâches assignées
    - Soumettre des demandes de congé
    - Enregistrer ses heures de travail
    - Consulter ses propres KPIs et données

  Rôle "manager":
    - Tout ce que peut faire un employé
    - Voir et gérer les tâches de son équipe
    - Approuver/Rejeter les demandes de congé de ses collaborateurs
    - Accès aux KPIs de ses projets
    - Créer et assigner des tâches

  Rôle "ceo":
    - Accès complet à toutes les données
    - Tableaux de bord globaux
    - KPIs de tous les projets
    - Données financières complètes

DOCUMENT RH — Construction Tunisie
DRH: rh@construction-tn.com
""")

write("rag_documents/procedures/gestion_equipements.txt", """
PROCÉDURE DE GESTION DES ÉQUIPEMENTS ET ENGINS
Construction Tunisie ERP — Document Technique
================================================
Version: 2.0 | Date: Janvier 2026

1. STATUTS DES ÉQUIPEMENTS
----------------------------
- "Available" (Disponible): L'équipement est prêt et peut être affecté à un projet
- "In Use" (En cours d'utilisation): L'équipement est affecté à un chantier actif
- "Maintenance" (En maintenance): L'équipement est en révision ou réparation

2. PROCÉDURE D'AFFECTATION
----------------------------
Étape 1: Chef de projet fait une demande dans l'ERP (module Équipements)
Étape 2: Vérification de la disponibilité en temps réel dans le système
Étape 3: Approbation du Responsable du parc matériel
Étape 4: Affectation enregistrée dans l'ERP avec date de début
Étape 5: Inspection de l'équipement par le chef de chantier avant utilisation
Étape 6: Rapport d'utilisation quotidien obligatoire pour engins > 100,000 EUR

3. PLAN DE MAINTENANCE PRÉVENTIVE
------------------------------------
- Maintenance légère: tous les 3 mois (vérification niveaux, graissage)
- Maintenance complète: tous les 6 mois (révision générale)
- Contrôle technique: annuel (conformité réglementaire)
- Tout équipement dont la prochaine maintenance est dépassée est automatiquement
  mis en statut "Maintenance" dans le système ERP

4. PROCÉDURE EN CAS DE PANNE
------------------------------
Étape 1: Le conducteur signale la panne immédiatement au chef de chantier
Étape 2: Créer un incident dans le système ERP (catégorie "Technical")
Étape 3: L'équipement est mis en statut "Maintenance" dans l'ERP
Étape 4: Contacter le fournisseur S003 (Équipement TP) pour les engins lourds
Étape 5: Estimer le délai de réparation et informer le chef de projet
Étape 6: Si délai > 3 jours, chercher un équipement de remplacement disponible

5. RÈGLES D'UTILISATION
------------------------
- Seuls les opérateurs certifiés peuvent conduire les engins lourds
- Interdiction formelle d'utiliser les équipements de l'entreprise à des fins personnelles
- Toute dégradation causée par négligence peut être imputée à l'employé responsable
- Le carnet de bord de chaque engin doit être rempli quotidiennement

DOCUMENT TECHNIQUE — Construction Tunisie
Responsable Parc Matériel: materiels@construction-tn.com
""")


# ════════════════════════════════════════════════════════════════════════════
# 3. EMAILS / MEMOS
# ════════════════════════════════════════════════════════════════════════════

write("rag_documents/emails/memo_reunion_fevrier2026.txt", """
MÉMO INTERNE — RÉUNION DE DIRECTION
Date: 15 Février 2026
De: Ahmed Trabelsi (CEO)
À: Tous les chefs de projet et managers
Objet: Points critiques Q1 2026

Équipe,

Suite à la réunion de direction du 14 février 2026, voici les décisions et points d'action:

1. PROJETS PRIORITAIRES EN FÉVRIER 2026
----------------------------------------
Le Pont Autoroutier A1 (P009) est notre préoccupation principale ce mois-ci.
Avec 30 jours de retard et un dépassement budgétaire de 6.8%, une réunion de crise
est planifiée pour le 22 février avec toute l'équipe projet.

Le Parc Industriel (P020) présente également 25 jours de retard avec 4 incidents
de sécurité. Un auditeur HSE externe sera mandaté la semaine prochaine.

2. BUDGET
----------
Le CFO (Leila Ben Salem) a présenté le bilan financier:
- Budget total engagé sur tous projets actifs: environ 50 millions EUR
- Taux de consommation budgétaire global: dans les normes
- Attention particulière sur P002 (Centre Commercial Carthage) dont le budget
  est consommé à 89% alors que le projet est à 89% d'avancement - marge très faible.

3. RESSOURCES HUMAINES
-----------------------
- Recrutement de 3 nouveaux ingénieurs de chantier en cours (département Projets)
- Formation sécurité obligatoire rappelée pour tous les nouveaux arrivants
- L'évaluation mi-année est avancée au 1er mai 2026 cette année

4. ÉQUIPEMENTS
---------------
La Bétonnière Mobile (EQ004) est en réparation (pompe défaillante).
Délai estimé: 3 semaines. Les projets impactés doivent prévoir une solution de remplacement.
Contacter le fournisseur S003 (Équipement TP) pour location temporaire.

5. PROCHAINE RÉUNION
---------------------
Réunion mensuelle de suivi projets: 15 Mars 2026 à 09h00, Salle de conférence A.

Ahmed Trabelsi
CEO — Construction Tunisie
""")

write("rag_documents/emails/email_rappel_securite.txt", """
EMAIL INTERNE — RAPPEL SÉCURITÉ URGENT
Date: 10 Février 2026
De: Département HSE
À: Tous les chefs de chantier
Objet: URGENT — Rappel règles sécurité suite incidents récents

Bonjour,

Suite aux incidents enregistrés récemment sur plusieurs chantiers, notamment:
- 3 incidents sur le Pont Autoroutier A1 (P009)
- 2 incidents sur l'Hôtel 5 Étoiles Djerba (P011)
- 2 incidents sur la Station d'Épuration (P017)

Nous rappelons IMPÉRATIVEMENT les règles suivantes:

1. Le port du casque et des chaussures de sécurité est NON NÉGOCIABLE.
   Tout manquement constaté entraîne une mise à pied immédiate d'1 jour.

2. Avant tout travail en hauteur, le harnais DOIT être vérifié et attaché.

3. Les check-lists quotidiennes des engins doivent être remplies CHAQUE MATIN
   avant utilisation. Elles doivent être uploadées sur l'ERP avant 08h30.

4. Tout incident, même mineur, doit être déclaré dans l'ERP le jour même.

5. Les zones de fouilles sur P009 doivent être rebalisées immédiatement.
   Le chef de chantier de P009 est personnellement responsable de cette action
   avant reprise des travaux lundi matin.

Un contrôle surprise HSE sera effectué sur tous les chantiers actifs
durant la semaine du 17 au 21 Février 2026.

Département HSE — Construction Tunisie
securite@construction-tn.com
""")

write("rag_documents/emails/email_client_p009.txt", """
EMAIL CLIENT — MISE À JOUR PROJET
Date: 12 Février 2026
De: Karim Jebali (Chef de Projet)
À: Direction Autoroutière de Tunisie (Client P009)
Objet: Point d'avancement — Pont Autoroutier A1 (P009)

Madame, Monsieur,

Je vous adresse ce point d'avancement mensuel concernant le projet Pont Autoroutier A1.

AVANCEMENT GLOBAL
------------------
Taux de complétion actuel: 68%
Retard cumulé: 30 jours sur le planning initial

CAUSES DU RETARD
-----------------
1. Conditions météorologiques défavorables en décembre 2025 (10 jours)
2. Délais de livraison des aciers de structure (15 jours)
3. Problèmes géotechniques imprévus sur la pile P3 (5 jours)

MESURES CORRECTIVES
--------------------
- Renforcement des équipes: 15 ouvriers supplémentaires mobilisés depuis le 1er février
- Travail en 2x8 sur les tâches critiques du chemin critique
- Nouveau planning de rattrapage joint à ce message
- Objectif: réduire le retard à 15 jours d'ici fin mars

PROCHAINES ÉTAPES
------------------
- Semaine 8: Coulage des tabliers centraux
- Semaine 9-10: Installation des équipements routiers
- Semaine 11: Tests de charge

Nous restons à votre disposition pour toute question.

Cordialement,
Karim Jebali | Chef de Projet Senior
construction-tn.com | +216 23 345 678
""")


# ════════════════════════════════════════════════════════════════════════════
# 4. GLOSSAIRE MÉTIER
# ════════════════════════════════════════════════════════════════════════════

write("rag_documents/glossaire/glossaire_metier_btp.txt", """
GLOSSAIRE MÉTIER — BTP ET GESTION DE PROJETS DE CONSTRUCTION
Construction Tunisie ERP
=============================================================
Ce glossaire définit tous les termes métier utilisés dans le système ERP,
les projets de construction, et les communications internes.

═══════════════════════════════════════════════════════════
A
═══════════════════════════════════════════════════════════

Acier de structure
  Barres d'acier utilisées comme armatures dans le béton armé.
  Terme connexe: ferraillage, HA (Haute Adhérence)

Appel d'offres (AO)
  Procédure par laquelle le maître d'ouvrage sollicite des offres de plusieurs
  entreprises pour la réalisation de travaux. Peut être ouvert ou restreint.

Avenant
  Modification contractuelle ajoutée à un marché de construction en cours.
  Peut impacter le budget et le délai du projet.

Avancement (completion_percentage dans l'ERP)
  Pourcentage de réalisation d'un projet. Calculé sur la base des travaux
  physiquement exécutés par rapport au total prévu.
  Exemple: Un projet à 72% d'avancement a réalisé 72% de ses travaux.

═══════════════════════════════════════════════════════════
B
═══════════════════════════════════════════════════════════

Béton armé
  Béton renforcé par des armatures en acier. Matériau de base de la
  construction moderne. Résistance à la compression (béton) + traction (acier).

Béton prêt à l'emploi (BPE)
  Béton fabriqué en centrale et livré sur chantier par camion toupie.

Budget alloué (budget_eur dans l'ERP)
  Montant total prévu pour réaliser un projet, en euros.
  Comprend: main d'œuvre, matériaux, équipements, sous-traitance, frais généraux.

Budget variance (budget_variance_percentage dans l'ERP)
  Écart entre le budget prévu et le coût réel, exprimé en pourcentage.
  Positif (+) = dépassement de budget (mauvais)
  Négatif (-) = économie par rapport au budget (bon)

═══════════════════════════════════════════════════════════
C
═══════════════════════════════════════════════════════════

Chantier
  Lieu physique où s'effectuent les travaux de construction.
  Chaque chantier est géré par un chef de chantier (site supervisor).

Chef de chantier (Site Supervisor)
  Responsable de la coordination quotidienne des travaux sur le terrain.
  Gère les ouvriers, les livraisons, la sécurité et l'avancement quotidien.

Chef de projet (Project Manager)
  Responsable global d'un projet: planning, budget, qualité, relation client.
  Dans l'ERP: champ project_manager_id.

CPI — Cost Performance Index (Indice de Performance des Coûts)
  CPI = Valeur acquise / Coût réel
  CPI > 1.0: le projet est sous budget
  CPI < 1.0: le projet dépasse le budget
  CPI = 1.0: le projet est exactement dans le budget

CNSS
  Caisse Nationale de Sécurité Sociale. Organisme tunisien gérant
  les cotisations sociales, les accidents du travail et les maladies professionnelles.

Coffrage
  Moule temporaire dans lequel on coule le béton. Retiré après durcissement.

Congé annuel (annual_leave dans l'ERP)
  annual_leave_total = jours accordés (35 jours standard)
  annual_leave_taken = jours déjà pris
  Solde restant = annual_leave_total - annual_leave_taken

═══════════════════════════════════════════════════════════
D
═══════════════════════════════════════════════════════════

Décompte
  Document récapitulatif des travaux exécutés, servant de base à la facturation.
  Établi périodiquement (mensuel en général) par le chef de projet.

Délai contractuel
  Date de livraison prévue dans le contrat de construction.
  Tout dépassement peut entraîner des pénalités de retard.

═══════════════════════════════════════════════════════════
E
═══════════════════════════════════════════════════════════

EPI — Équipements de Protection Individuelle
  casque, chaussures de sécurité, gilet, gants, lunettes, harnais.
  Port obligatoire sur tous les chantiers de Construction Tunisie.

ERP — Enterprise Resource Planning (Progiciel de Gestion Intégré)
  Système informatique centralisant toutes les données de l'entreprise:
  projets, employés, finances, équipements, fournisseurs, congés, KPIs.

═══════════════════════════════════════════════════════════
F
═══════════════════════════════════════════════════════════

Ferraillage
  Mise en place des armatures en acier avant coulage du béton.

Fondations
  Partie de la structure transmettant les charges du bâtiment au sol.
  Types: superficielles (semelles, radiers) ou profondes (pieux, micropieux).

Fournisseur référencé
  Entreprise approuvée et enregistrée dans le système ERP.

═══════════════════════════════════════════════════════════
G
═══════════════════════════════════════════════════════════

Gestion des risques (risk_level dans l'ERP)
  Low: risque faible | Medium: risque modéré | High: risque élevé

═══════════════════════════════════════════════════════════
H
═══════════════════════════════════════════════════════════

HSE — Hygiène, Sécurité, Environnement
  Département responsable de la sécurité sur les chantiers.

═══════════════════════════════════════════════════════════
I
═══════════════════════════════════════════════════════════

Incident (Issues dans l'ERP)
  Tout événement non planifié affectant un projet.
  Catégories: Safety, Quality, Delay, Budget, Technical, Other.
  Sévérités: Low, Medium, High, Critical.

═══════════════════════════════════════════════════════════
K
═══════════════════════════════════════════════════════════

KPI — Key Performance Indicator (Indicateur Clé de Performance)
  KPIs suivis dans l'ERP:
  - budget_variance_percentage: écart budgétaire en %
  - schedule_variance_days: retard en jours (positif = retard, négatif = avance)
  - quality_score: score qualité sur 100
  - safety_incidents: nombre d'incidents sécurité
  - client_satisfaction_score: note client sur 5
  - team_productivity_percentage: productivité équipe en %
  - cost_performance_index (CPI): indice performance coûts
  - schedule_performance_index (SPI): indice performance calendrier
  - risk_level: niveau de risque (Low/Medium/High)

═══════════════════════════════════════════════════════════
M
═══════════════════════════════════════════════════════════

Maître d'œuvre (MOE)
  Entité technique responsable de la conception et du suivi des travaux.

Maître d'ouvrage (MOA)
  Client qui commande et finance les travaux. Dans l'ERP: champ client_name.

Marché de travaux
  Contrat signé entre le client et l'entreprise. Définit périmètre, prix et délai.

═══════════════════════════════════════════════════════════
P
═══════════════════════════════════════════════════════════

Planning de chantier
  Document définissant le séquencement et les dates des travaux.
  Le retard est mesuré par schedule_variance_days dans l'ERP.

Projet (projects dans l'ERP)
  Statuts possibles: "In Progress", "Completed", "Planning".

═══════════════════════════════════════════════════════════
R
═══════════════════════════════════════════════════════════

RAG — Retrieval-Augmented Generation
  Technique d'IA utilisée par le chatbot ERP pour répondre à partir de documents.

Retard (schedule_variance_days dans l'ERP)
  > 0: le projet est EN RETARD
  < 0: le projet est EN AVANCE
  = 0: le projet est DANS LES DÉLAIS

═══════════════════════════════════════════════════════════
S
═══════════════════════════════════════════════════════════

SPI — Schedule Performance Index (Indice de Performance du Calendrier)
  SPI = Valeur acquise / Valeur planifiée
  SPI > 1.0: EN AVANCE | SPI < 1.0: EN RETARD | SPI = 1.0: DANS LES DÉLAIS

Sous-traitant
  Entreprise mandatée pour réaliser une partie spécifique des travaux.

═══════════════════════════════════════════════════════════
T
═══════════════════════════════════════════════════════════

Tâche (tasks dans l'ERP)
  Statuts: "Todo", "In Progress", "Done".
  Priorités: "Critical", "High", "Medium", "Low".

Timesheet (feuille de temps)
  Enregistrement des heures travaillées. Saisi dans le module Timesheets de l'ERP.

Taux de fréquence (TF) = Accidents × 1,000,000 / Heures travaillées
Taux de gravité (TG) = Jours perdus × 1,000 / Heures travaillées

═══════════════════════════════════════════════════════════
ABRÉVIATIONS COURANTES
═══════════════════════════════════════════════════════════
BPE: Béton Prêt à l'Emploi
BTP: Bâtiment et Travaux Publics
CEO: Chief Executive Officer (Directeur Général)
CFO: Chief Financial Officer (Directeur Financier)
CPI: Cost Performance Index
DRH: Directeur des Ressources Humaines
EPI: Équipements de Protection Individuelle
ERP: Enterprise Resource Planning
HSE: Hygiène Sécurité Environnement
KPI: Key Performance Indicator
MOA: Maître d'Ouvrage
MOE: Maître d'Œuvre
SPI: Schedule Performance Index
TF: Taux de Fréquence | TG: Taux de Gravité
TP: Travaux Publics

FIN DU GLOSSAIRE — Construction Tunisie ERP
""")


# ════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("✅ ALL STATIC DOCUMENTS GENERATED SUCCESSFULLY")
print("="*60)

total_chars = 0
doc_count = 0
for root, dirs, files in os.walk("rag_documents"):
    for file in files:
        path = os.path.join(root, file)
        size = os.path.getsize(path)
        total_chars += size
        doc_count += 1

print(f"📄 Total documents: {doc_count}")
print(f"📝 Total size: {total_chars:,} chars (~{total_chars//5:,} tokens)")
print(f"📁 Folder: rag_documents/")
print("\nNext step: python vector.py to index everything!")
print("\nNOTE: Live data (projects, employees, KPIs, equipment, suppliers)")
print("      is served via API endpoints to the LLM planner — not in RAG.")

# ════════════════════════════════════════════════════════════════════════════
# 5. NOTES DE RÉUNION / COMPTES RENDUS / SECRÉTARIAT
# ════════════════════════════════════════════════════════════════════════════

write("rag_documents/emails/cr_reunion_chantier_mars2026.txt", """
COMPTE RENDU DE RÉUNION DE CHANTIER
Construction Tunisie — Réunion hebdomadaire
===========================================
Date: 10 mars 2026 | Lieu: Bureau de chantier P009 — Pont Autoroutier A1
Présents: Karim Jebali (Chef de projet), Rami Ferchichi (Superviseur), Nadia Hamdi (Manager)
Secrétaire de séance: Mariem Chakroun

ORDRE DU JOUR
1. Avancement des travaux
2. Points bloquants
3. Sécurité
4. Prochaines étapes

1. AVANCEMENT
- Fondations piles P3 et P4 : 85% terminées (retard de 12 jours sur planning initial)
- Coffrage tablier : en cours, livraison acier prévue 14 mars
- Avancement global projet : 68%

2. POINTS BLOQUANTS
- Livraison acier structure (HA32) bloquée chez fournisseur Acier Plus — manque de stock
- Permis voirie non encore accordé par la municipalité — relance envoyée le 08/03
- Grue mobile en attente de certification HSE (inspection prévue 15 mars)

3. SÉCURITÉ
- 0 accident ce mois. Rappel port EPI obligatoire zone B.
- Formation geste et posture programmée pour le 20 mars.

4. DÉCISIONS
- Karim Jebali doit relancer fournisseur Acier Plus avant le 12 mars
- Nadia Hamdi suit le dossier permis voirie en urgence
- Prochaine réunion: 17 mars 2026

Signature: Mariem Chakroun (Secrétaire) | Karim Jebali (Approbateur)
""")

write("rag_documents/emails/note_secretariat_semaine11.txt", """
NOTE DE SECRÉTARIAT — SEMAINE 11/2026
Construction Tunisie — Direction Générale
==========================================
Date: 11 mars 2026 | Rédigée par: Mariem Chakroun

RÉSUMÉ DE LA SEMAINE
- Réunion direction du lundi 09/03 : budget Q1 validé à 87% d'exécution
- Visite client Ministère de l'Équipement (projet P009) le 10/03 : satisfaction 4/5
- Départ en congé de Sonia Mejri (16-18 mars) — remplacement assuré par Ines Hammami
- Nouvelle demande de congé Rami Ferchichi (16-20 mars) — en attente validation Karim Jebali

COURRIERS REÇUS
- Lettre de réclamation client Djerba Luxury Hotels (P011) : retard livraison suites VIP
- Devis reçu de Ciments de Tunisie pour livraison chantier P020 — en attente validation achat

RAPPELS
- Évaluations mi-parcours Q1 à soumettre avant le 20 mars
- Renouvellement contrat Grue Services prévu le 31 mars
- Réunion HSE mensuelle : 18 mars à 14h00

ACTIONS EN ATTENTE
- Réponse bureau de contrôle pour P012 (demandée depuis 01/03)
- Validation budget phase 2 projet P009 par CEO
""")

write("rag_documents/emails/cr_reunion_direction_fevrier2026.txt", """
COMPTE RENDU RÉUNION DE DIRECTION
Construction Tunisie — Comité de Direction
===========================================
Date: 02 février 2026 | Durée: 2h30
Présents: Ahmed Trabelsi (CEO), Leila Ben Salem (CFO), Fatma Gharbi (DRH),
          Karim Jebali (Directeur Projets), Mohamed Khelifi (Directeur Opérations)
Secrétaire: Mariem Chakroun

1. BILAN FINANCIER JANVIER 2026
- Budget total portefeuille: 103.7 M DT
- Coût réel à date: 58.6 M DT (56.5% du budget consommé)
- Avancement moyen: 54.1% — légèrement en dessous du prévisionnel (57%)
- Projets en dépassement budgétaire: Centre Culturel Monastir (+4.2%)
- CFO: recommande audit interne sur P010 (Rénovation Médina Kairouan) — CPI=0.98

2. RESSOURCES HUMAINES
- DRH: 4 employés en congé simultanément semaine 10 dont 2 avec tâches critiques
- Action: protocole de remplacement obligatoire avant départ en congé si tâche critique
- Recrutement: 2 postes ouverts (ingénieur génie civil + conducteur de travaux)

3. PROJETS PRIORITAIRES
- P009 Pont Autoroutier A1: retard 30j — réunion urgente avec équipe chantier
- P020 Parc Industriel: retard 25j — révision planning nécessaire
- P004 Complexe Sportif Sousse: blocage approvisionnement acier

4. DÉCISIONS PRISES
- Budget exceptionnel de 50K DT accordé pour P009 (accélération travaux)
- Audit qualité P012 programmé pour fin février
- Révision des procédures de congés pour éviter absences critiques simultanées

Prochaine réunion direction: 02 mars 2026
Approbation: Ahmed Trabelsi
""")

write("rag_documents/emails/note_rh_procedure_interne.txt", """
NOTE DE SERVICE RH — PROCÉDURES INTERNES
Construction Tunisie — Département RH
======================================
Réf: RH-2026-003 | Date: 15 janvier 2026
De: Fatma Gharbi (DRH) | À: Tous les employés

RAPPEL DES PROCÉDURES RH IMPORTANTES

1. DEMANDE DE CONGÉ
- Toute demande doit être soumise via l'ERP (module Congés)
- Délai minimum: 15 jours pour congé ≥ 5 jours, 3 jours pour congé < 5 jours
- Un employé NE PEUT PAS partir en congé s'il a des tâches critiques non assignées
- En cas d'urgence: contacter directement le DRH

2. ÉVALUATION DE PERFORMANCE
- Évaluation annuelle: décembre de chaque année
- Évaluation mi-parcours: juin de chaque année
- Les KPIs projets sont pris en compte dans l'évaluation des chefs de projet
- Toute mauvaise performance (3 mois consécutifs) déclenche un plan d'amélioration

3. ACCÈS AU SYSTÈME ERP
- Chaque employé accède uniquement à ses propres données
- Les managers voient les données de leur équipe directe
- Le CEO et RH ont accès global (dans les limites de leurs rôles)
- Tout accès non autorisé est tracé et sanctionnable

4. SIGNALEMENT D'INCIDENTS
- Tout incident sur chantier doit être signalé dans l'ERP sous 24h
- Accidents graves: appel immédiat HSE + rapport dans les 2h
- Incidents répétitifs: réunion sécurité obligatoire dans les 48h

Fatma Gharbi — DRH
""")