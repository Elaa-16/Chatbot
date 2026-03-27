"""
Reports router — Construction ERP
===================================
Generates real PDF reports from live DB data using reportlab.
Four report types:
  - project_status      : projects + KPIs + blocked tasks
  - employee_performance: employees + tasks + leave
  - budget              : budget vs actual + purchase orders
  - task_completion     : KPIs CPI/SPI + critical tasks + issues
"""

import io
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.database import get_db
from core.auth import authenticate_with_token, get_accessible_projects, log_action
from core.models import ReportCreate

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak,
)

# ── Colors ────────────────────────────────────────────────────────────────────
INDIGO  = colors.HexColor('#4f46e5')
INDIGO_L= colors.HexColor('#eef2ff')
GREEN   = colors.HexColor('#16a34a')
GREEN_L = colors.HexColor('#f0fdf4')
RED     = colors.HexColor('#dc2626')
RED_L   = colors.HexColor('#fef2f2')
ORANGE  = colors.HexColor('#f97316')
AMBER   = colors.HexColor('#d97706')
AMBER_L = colors.HexColor('#fffbeb')
SLATE   = colors.HexColor('#64748b')
SLATE_L = colors.HexColor('#f8fafc')
DARK    = colors.HexColor('#0f172a')
BORDER  = colors.HexColor('#e2e8f0')
WHITE   = colors.white

router = APIRouter(prefix="/reports", tags=["Reports"])

# ── Styles ────────────────────────────────────────────────────────────────────
def _styles():
    def s(name, **kw):
        return ParagraphStyle(name, **kw)
    return {
        'title':    s('T',  fontSize=22, textColor=DARK,   fontName='Helvetica-Bold', spaceAfter=4),
        'subtitle': s('ST', fontSize=11, textColor=SLATE,  fontName='Helvetica',      spaceAfter=2),
        'h2':       s('H2', fontSize=14, textColor=INDIGO, fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6),
        'body':     s('B',  fontSize=9,  textColor=DARK,   fontName='Helvetica',      spaceAfter=3, leading=13),
        'small':    s('SM', fontSize=8,  textColor=SLATE,  fontName='Helvetica'),
        'th':       s('TH', fontSize=8,  textColor=WHITE,  fontName='Helvetica-Bold', alignment=TA_CENTER),
        'td':       s('TD', fontSize=8,  textColor=DARK,   fontName='Helvetica',      alignment=TA_LEFT),
        'td_c':     s('TC', fontSize=8,  textColor=DARK,   fontName='Helvetica',      alignment=TA_CENTER),
        'td_r':     s('TR', fontSize=8,  textColor=DARK,   fontName='Helvetica',      alignment=TA_RIGHT),
        'good':     s('GD', fontSize=11, textColor=GREEN,  fontName='Helvetica-Bold', alignment=TA_CENTER),
        'bad':      s('BD', fontSize=11, textColor=RED,    fontName='Helvetica-Bold', alignment=TA_CENTER),
        'warn':     s('WN', fontSize=11, textColor=AMBER,  fontName='Helvetica-Bold', alignment=TA_CENTER),
    }

def _tbl(header_color=INDIGO):
    return TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), header_color),
        ('TEXTCOLOR',     (0,0), (-1,0), WHITE),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 8),
        ('ALIGN',         (0,0), (-1,0), 'CENTER'),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, SLATE_L]),
        ('GRID',          (0,0), (-1,-1), 0.4, BORDER),
        ('FONTNAME',      (0,1), (-1,-1), 'Helvetica'),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ])

def _risk_color(level):
    return {'High': RED, 'Medium': AMBER, 'Low': GREEN}.get(level, SLATE)

def _cpi_color(v):
    try:
        f = float(v)
        return GREEN if f >= 1.0 else (AMBER if f >= 0.9 else RED)
    except:
        return SLATE

def _header(st, title, subtitle, period_start=None, period_end=None, generated_by=None):
    elems = [HRFlowable(width='100%', thickness=3, color=INDIGO, spaceAfter=8)]
    elems.append(Paragraph(title, st['title']))
    elems.append(Paragraph(subtitle, st['subtitle']))
    parts = []
    if period_start and period_end:
        parts.append(f"Periode : {period_start} au {period_end}")
    parts.append(f"Genere le : {datetime.now().strftime('%d/%m/%Y a %H:%M')}")
    if generated_by:
        parts.append(f"Par : {generated_by}")
    elems.append(Paragraph("  |  ".join(parts), st['small']))
    elems.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceBefore=8, spaceAfter=12))
    return elems

def _colored_p(text, base_style, color):
    return Paragraph(text, ParagraphStyle('x', parent=base_style, textColor=color))


# ═════════════════════════════════════════════════════════════════════════════
# PDF GENERATORS
# ═════════════════════════════════════════════════════════════════════════════

def _pdf_project_status(db, user, period_start, period_end, generated_by_name):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    st = _styles()
    W  = A4[0] - 4*cm
    story = _header(st, "Rapport Statut Projets",
                    "Vue d'ensemble des projets de construction",
                    period_start, period_end, generated_by_name)

    cursor = db.cursor()
    accessible = get_accessible_projects(user, db)
    if accessible is None:
        cursor.execute("SELECT * FROM projects ORDER BY status, project_name")
    else:
        ph = ','.join(['?']*len(accessible))
        cursor.execute(f"SELECT * FROM projects WHERE project_id IN ({ph}) ORDER BY status, project_name",
                       list(accessible))
    projects = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT k.* FROM kpis k
        INNER JOIN (SELECT project_id, MAX(kpi_date) md FROM kpis GROUP BY project_id) l
        ON k.project_id=l.project_id AND k.kpi_date=l.md
    """)
    kpi_map = {r['project_id']: dict(r) for r in cursor.fetchall()}

    cursor.execute("SELECT * FROM tasks WHERE status='Blocked'")
    blocked_by_proj = {}
    for t in cursor.fetchall():
        t = dict(t)
        blocked_by_proj.setdefault(t['project_id'], []).append(t)

    total      = len(projects)
    in_progress= sum(1 for p in projects if p.get('status')=='In Progress')
    completed  = sum(1 for p in projects if p.get('status')=='Completed')
    planning   = sum(1 for p in projects if p.get('status')=='Planning')
    delayed    = sum(1 for k in kpi_map.values() if (k.get('schedule_variance_days') or 0) > 0)
    high_risk  = sum(1 for k in kpi_map.values() if k.get('risk_level')=='High')

    story.append(Paragraph("Synthese globale", st['h2']))
    story.append(Table([
        [Paragraph(h, st['th']) for h in ['Total','En cours','Termines','Planif.','En retard','Risque eleve']],
        [Paragraph(str(total), st['good']), Paragraph(str(in_progress), st['good']),
         Paragraph(str(completed), st['good']), Paragraph(str(planning), st['warn']),
         Paragraph(str(delayed), st['bad'] if delayed else st['good']),
         Paragraph(str(high_risk), st['bad'] if high_risk else st['good'])],
    ], colWidths=[W/6]*6, style=_tbl()))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Detail par projet", st['h2']))
    rows = [[Paragraph(h, st['th']) for h in
             ['Projet','Statut','Avanc.%','Budget DT','Retard','CPI','SPI','Risque','Bloques']]]
    for p in projects:
        pid   = p['project_id']
        k     = kpi_map.get(pid, {})
        cpi   = k.get('cost_performance_index','')
        spi   = k.get('schedule_performance_index','')
        delay = k.get('schedule_variance_days', 0) or 0
        risk  = k.get('risk_level','—')
        nb    = len(blocked_by_proj.get(pid, []))
        rows.append([
            Paragraph(p.get('project_name','')[:26], st['td']),
            Paragraph(p.get('status',''), st['td_c']),
            Paragraph(f"{p.get('completion_percentage',0)}%", st['td_c']),
            Paragraph(f"{p.get('budget',0):,.0f}", st['td_r']),
            _colored_p(f"+{delay}j" if delay>0 else f"{delay}j", st['td_c'], RED if delay>0 else GREEN),
            _colored_p(str(cpi)[:5] if cpi else '—', st['td_c'], _cpi_color(cpi)),
            _colored_p(str(spi)[:5] if spi else '—', st['td_c'], GREEN if spi and float(spi)>=1 else AMBER),
            _colored_p(risk, st['td_c'], _risk_color(risk)),
            Paragraph(str(nb), st['td_c']),
        ])
    story.append(Table(rows, colWidths=[W*0.21,W*0.10,W*0.08,W*0.13,W*0.08,W*0.08,W*0.08,W*0.09,W*0.08],
                       style=_tbl()))

    all_blocked = [(pid,t) for pid,tasks in blocked_by_proj.items() for t in tasks]
    if all_blocked:
        story.append(PageBreak())
        story.append(Paragraph(f"Taches bloquees — Action requise ({len(all_blocked)})", st['h2']))
        bt = [[Paragraph(h, st['th']) for h in ['ID','Titre','Projet','Priorite','Echeance']]]
        for pid, t in all_blocked:
            pri = t.get('priority','')
            bt.append([
                Paragraph(t.get('task_id',''), st['td_c']),
                Paragraph(t.get('title','')[:38], st['td']),
                Paragraph(pid, st['td_c']),
                _colored_p(pri, st['td_c'], RED if pri=='Critical' else AMBER),
                Paragraph(t.get('due_date',''), st['td_c']),
            ])
        story.append(Table(bt, colWidths=[W*0.12,W*0.38,W*0.12,W*0.14,W*0.14], style=_tbl(RED)))

    doc.build(story)
    buf.seek(0)
    return buf


def _pdf_employee_performance(db, user, period_start, period_end, generated_by_name):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    st = _styles()
    W  = A4[0] - 4*cm
    story = _header(st, "Rapport Performance Employes",
                    "Taches, conges et activite par employe",
                    period_start, period_end, generated_by_name)

    cursor = db.cursor()
    cursor.execute("SELECT * FROM employees ORDER BY department, last_name")
    employees = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM tasks")
    tasks_by_emp = {}
    for t in cursor.fetchall():
        t = dict(t)
        tasks_by_emp.setdefault(t['assigned_to'], []).append(t)
    cursor.execute("SELECT * FROM leave_requests WHERE status='Approved'")
    leaves_by_emp = {}
    for l in cursor.fetchall():
        l = dict(l)
        leaves_by_emp.setdefault(l['employee_id'], []).append(l)
    cursor.execute("SELECT employee_id, SUM(hours_worked) AS hrs FROM timesheets GROUP BY employee_id")
    hours_by_emp = {r['employee_id']: (r['hrs'] or 0) for r in cursor.fetchall()}

    by_role = {}
    for e in employees:
        by_role[e.get('role','')] = by_role.get(e.get('role',''), 0) + 1

    story.append(Paragraph("Repartition par role", st['h2']))
    story.append(Table([
        [Paragraph(h, st['th']) for h in ['CEO','Manager','Employe','RH','Total']],
        [Paragraph(str(by_role.get('ceo',0)), st['td_c']),
         Paragraph(str(by_role.get('manager',0)), st['td_c']),
         Paragraph(str(by_role.get('employee',0)), st['td_c']),
         Paragraph(str(by_role.get('rh',0)), st['td_c']),
         Paragraph(str(len(employees)), st['good'])],
    ], colWidths=[W/5]*5, style=_tbl()))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Detail par employe", st['h2']))
    rows = [[Paragraph(h, st['th']) for h in
             ['Employe','Dept','Role','Taches','Terminees','En cours','Bloq.','Heures','Conges j']]]
    for e in employees:
        eid    = e['employee_id']
        etasks = tasks_by_emp.get(eid, [])
        done   = sum(1 for t in etasks if t.get('status')=='Done')
        inp    = sum(1 for t in etasks if t.get('status')=='In Progress')
        blk    = sum(1 for t in etasks if t.get('status')=='Blocked')
        hrs    = hours_by_emp.get(eid, 0)
        ldays  = sum(l.get('total_days',0) or 0 for l in leaves_by_emp.get(eid, []))
        rows.append([
            Paragraph(f"{e.get('first_name','')} {e.get('last_name','')}", st['td']),
            Paragraph(e.get('department','')[:10], st['td']),
            Paragraph(e.get('role','').capitalize(), st['td_c']),
            Paragraph(str(len(etasks)), st['td_c']),
            _colored_p(str(done), st['td_c'], GREEN),
            Paragraph(str(inp), st['td_c']),
            _colored_p(str(blk), st['td_c'], RED if blk else SLATE),
            Paragraph(f"{hrs:.0f}h", st['td_r']),
            Paragraph(str(ldays), st['td_c']),
        ])
    story.append(Table(rows,
        colWidths=[W*0.21,W*0.12,W*0.09,W*0.09,W*0.09,W*0.09,W*0.07,W*0.10,W*0.09],
        style=_tbl()))

    doc.build(story)
    buf.seek(0)
    return buf


def _pdf_budget(db, user, period_start, period_end, generated_by_name):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    st = _styles()
    W  = A4[0] - 4*cm
    story = _header(st, "Rapport Financier",
                    "Budget, couts reels et depassements par projet",
                    period_start, period_end, generated_by_name)

    cursor = db.cursor()
    accessible = get_accessible_projects(user, db)
    if accessible is None:
        cursor.execute("SELECT * FROM projects ORDER BY project_name")
    else:
        ph = ','.join(['?']*len(accessible))
        cursor.execute(f"SELECT * FROM projects WHERE project_id IN ({ph}) ORDER BY project_name",
                       list(accessible))
    projects = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM purchase_orders")
    pos = [dict(r) for r in cursor.fetchall()]
    po_by_proj = {}
    for po in pos:
        po_by_proj.setdefault(po['project_id'], []).append(po)

    cursor.execute("""
        SELECT k.* FROM kpis k
        INNER JOIN (SELECT project_id, MAX(kpi_date) md FROM kpis GROUP BY project_id) l
        ON k.project_id=l.project_id AND k.kpi_date=l.md
    """)
    kpi_map = {r['project_id']: dict(r) for r in cursor.fetchall()}

    total_budget = sum(p.get('budget',0) or 0 for p in projects)
    total_actual = sum(p.get('actual_cost',0) or 0 for p in projects)
    total_var    = total_actual - total_budget
    over_count   = sum(1 for p in projects if (p.get('actual_cost',0) or 0) > (p.get('budget',0) or 1))
    total_po_amt = sum(po.get('total_amount',0) or 0 for po in pos)

    story.append(Paragraph("Synthese financiere globale", st['h2']))
    story.append(Table([
        [Paragraph(h, st['th']) for h in ['Budget total','Cout reel','Ecart','Hors budget','Total POs']],
        [Paragraph(f"{total_budget:,.0f} DT", st['good']),
         Paragraph(f"{total_actual:,.0f} DT", st['warn']),
         _colored_p(f"{total_var:+,.0f} DT", st['bad'] if total_var>0 else st['good'], RED if total_var>0 else GREEN),
         Paragraph(str(over_count), st['bad'] if over_count else st['good']),
         Paragraph(f"{total_po_amt:,.0f} DT", st['td_c'])],
    ], colWidths=[W/5]*5, style=_tbl()))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Detail budgetaire par projet", st['h2']))
    rows = [[Paragraph(h, st['th']) for h in
             ['Projet','Budget DT','Cout reel DT','Ecart DT','Ecart %','CPI','Avanc.%','POs']]]
    for p in projects:
        pid    = p['project_id']
        budget = p.get('budget', 0) or 0
        actual = p.get('actual_cost', 0) or 0
        var    = actual - budget
        var_pct= (var/budget*100) if budget else 0
        k      = kpi_map.get(pid, {})
        cpi    = k.get('cost_performance_index','')
        nb_po  = len(po_by_proj.get(pid, []))
        rows.append([
            Paragraph(p.get('project_name','')[:24], st['td']),
            Paragraph(f"{budget:,.0f}", st['td_r']),
            Paragraph(f"{actual:,.0f}", st['td_r']),
            _colored_p(f"{var:+,.0f}", st['td_r'], RED if var>0 else GREEN),
            _colored_p(f"{var_pct:+.1f}%", st['td_c'], RED if var_pct>0 else GREEN),
            _colored_p(str(cpi)[:5] if cpi else '—', st['td_c'], _cpi_color(cpi)),
            Paragraph(f"{p.get('completion_percentage',0)}%", st['td_c']),
            Paragraph(str(nb_po), st['td_c']),
        ])
    story.append(Table(rows,
        colWidths=[W*0.20,W*0.13,W*0.14,W*0.12,W*0.09,W*0.08,W*0.08,W*0.07],
        style=_tbl()))

    if pos:
        story.append(PageBreak())
        story.append(Paragraph(f"Bons de commande ({len(pos)})", st['h2']))
        po_rows = [[Paragraph(h, st['th']) for h in
                    ['PO ID','Projet','Fournisseur','Montant DT','Statut','Livraison']]]
        for po in pos:
            amt = po.get('total_amount', 0) or 0
            po_rows.append([
                Paragraph(po.get('po_id',''), st['td_c']),
                Paragraph(po.get('project_id',''), st['td_c']),
                Paragraph(str(po.get('supplier_id',''))[:15], st['td']),
                Paragraph(f"{amt:,.0f}", st['td_r']),
                Paragraph(po.get('status',''), st['td_c']),
                Paragraph(po.get('delivery_date',''), st['td_c']),
            ])
        # Total row
        n = len(po_rows)
        po_rows.append([
            Paragraph('TOTAL', st['th']), Paragraph('', st['td']), Paragraph('', st['td']),
            Paragraph(f"{total_po_amt:,.0f}", ParagraphStyle('tt', parent=st['td_r'],
                textColor=WHITE, fontName='Helvetica-Bold')),
            Paragraph('', st['td']), Paragraph('', st['td']),
        ])
        ts = _tbl()
        ts.add('BACKGROUND', (0, n), (-1, n), INDIGO)
        story.append(Table(po_rows, colWidths=[W*0.13,W*0.12,W*0.22,W*0.18,W*0.18,W*0.15], style=ts))

    doc.build(story)
    buf.seek(0)
    return buf


def _pdf_kpi(db, user, period_start, period_end, generated_by_name):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    st = _styles()
    W  = A4[0] - 4*cm
    story = _header(st, "Rapport KPI — Performance & Risques",
                    "CPI, SPI, retards et incidents critiques",
                    period_start, period_end, generated_by_name)

    cursor = db.cursor()
    cursor.execute("""
        SELECT k.* FROM kpis k
        INNER JOIN (SELECT project_id, MAX(kpi_date) md FROM kpis GROUP BY project_id) l
        ON k.project_id=l.project_id AND k.kpi_date=l.md
        ORDER BY k.schedule_variance_days DESC
    """)
    kpis = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM tasks WHERE priority='Critical' AND status != 'Done'")
    critical_tasks = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM issues WHERE severity IN ('Critical','High') AND status='Open'")
    issues = [dict(r) for r in cursor.fetchall()]

    cpi_vals = [float(k['cost_performance_index']) for k in kpis if k.get('cost_performance_index')]
    spi_vals = [float(k['schedule_performance_index']) for k in kpis if k.get('schedule_performance_index')]
    avg_cpi  = sum(cpi_vals)/len(cpi_vals) if cpi_vals else 0
    avg_spi  = sum(spi_vals)/len(spi_vals) if spi_vals else 0
    delayed  = sum(1 for k in kpis if (k.get('schedule_variance_days') or 0) > 0)
    high_risk= sum(1 for k in kpis if k.get('risk_level')=='High')
    over_cpi = sum(1 for k in kpis if k.get('cost_performance_index') and float(k['cost_performance_index'])<1)

    story.append(Paragraph("Indicateurs globaux", st['h2']))
    story.append(Table([
        [Paragraph(h, st['th']) for h in ['CPI moyen','SPI moyen','En retard','Risque eleve','CPI<1','Critiques']],
        [Paragraph(f"{avg_cpi:.3f}", st['good'] if avg_cpi>=1 else st['bad']),
         Paragraph(f"{avg_spi:.3f}", st['good'] if avg_spi>=1 else st['warn']),
         Paragraph(str(delayed),   st['bad'] if delayed else st['good']),
         Paragraph(str(high_risk), st['bad'] if high_risk else st['good']),
         Paragraph(str(over_cpi),  st['bad'] if over_cpi else st['good']),
         Paragraph(str(len(critical_tasks)), st['bad'] if critical_tasks else st['good'])],
    ], colWidths=[W/6]*6, style=_tbl()))
    story.append(Spacer(1, 12))

    story.append(Paragraph("KPIs par projet (snapshot le plus recent)", st['h2']))
    rows = [[Paragraph(h, st['th']) for h in
             ['Projet','Date KPI','CPI','SPI','Retard','Budget%','Qualite','Risque']]]
    for k in kpis:
        cpi   = k.get('cost_performance_index','')
        spi   = k.get('schedule_performance_index','')
        delay = k.get('schedule_variance_days', 0) or 0
        bud   = k.get('budget_variance_percentage', 0) or 0
        risk  = k.get('risk_level','—')
        rows.append([
            Paragraph(k.get('project_name', k.get('project_id',''))[:24], st['td']),
            Paragraph(k.get('kpi_date',''), st['td_c']),
            _colored_p(str(cpi)[:5] if cpi else '—', st['td_c'], _cpi_color(cpi)),
            _colored_p(str(spi)[:5] if spi else '—', st['td_c'], GREEN if spi and float(spi)>=1 else AMBER),
            _colored_p(f"+{delay}j" if delay>0 else f"{delay}j", st['td_c'], RED if delay>0 else GREEN),
            _colored_p(f"{float(bud):+.1f}%" if bud else '0%', st['td_c'], RED if float(bud or 0)>0 else GREEN),
            Paragraph(str(k.get('quality_score',''))[:4], st['td_c']),
            _colored_p(risk, st['td_c'], _risk_color(risk)),
        ])
    story.append(Table(rows,
        colWidths=[W*0.24,W*0.11,W*0.08,W*0.08,W*0.09,W*0.09,W*0.09,W*0.09],
        style=_tbl()))

    if critical_tasks:
        story.append(PageBreak())
        story.append(Paragraph(f"Taches critiques non terminees ({len(critical_tasks)})", st['h2']))
        ct = [[Paragraph(h, st['th']) for h in ['ID','Titre','Projet','Statut','Echeance']]]
        for t in critical_tasks:
            stat = t.get('status','')
            ct.append([
                Paragraph(t.get('task_id',''), st['td_c']),
                Paragraph(t.get('title','')[:38], st['td']),
                Paragraph(t.get('project_id',''), st['td_c']),
                _colored_p(stat, st['td_c'], RED if stat=='Blocked' else AMBER),
                Paragraph(t.get('due_date',''), st['td_c']),
            ])
        story.append(Table(ct, colWidths=[W*0.11,W*0.40,W*0.12,W*0.15,W*0.14], style=_tbl(RED)))

    if issues:
        story.append(Spacer(1, 14))
        story.append(Paragraph(f"Incidents ouverts Critical/High ({len(issues)})", st['h2']))
        iss = [[Paragraph(h, st['th']) for h in ['ID','Titre','Projet','Severite','Categorie']]]
        for i in issues:
            sev = i.get('severity','')
            iss.append([
                Paragraph(i.get('issue_id',''), st['td_c']),
                Paragraph(i.get('title','')[:38], st['td']),
                Paragraph(i.get('project_id',''), st['td_c']),
                _colored_p(sev, st['td_c'], RED if sev=='Critical' else AMBER),
                Paragraph(i.get('category',''), st['td_c']),
            ])
        story.append(Table(iss, colWidths=[W*0.11,W*0.40,W*0.12,W*0.15,W*0.14], style=_tbl(AMBER)))

    doc.build(story)
    buf.seek(0)
    return buf


PDF_GENERATORS = {
    'project_status':       _pdf_project_status,
    'employee_performance': _pdf_employee_performance,
    'budget':               _pdf_budget,
    'task_completion':      _pdf_kpi,
}

REPORT_LABELS = {
    'project_status':       'Rapport_Projets',
    'employee_performance': 'Rapport_Employes',
    'budget':               'Rapport_Financier',
    'task_completion':      'Rapport_KPI',
}

# ═════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@router.get("")
def get_reports(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    if user["role"] == "ceo":
        cursor.execute("""
            SELECT r.*, e.first_name || ' ' || e.last_name as generated_by_name
            FROM reports r LEFT JOIN employees e ON r.generated_by = e.employee_id
            ORDER BY r.generation_date DESC
        """)
    elif user["role"] == "manager":
        cursor.execute("""
            SELECT r.*, e.first_name || ' ' || e.last_name as generated_by_name
            FROM reports r LEFT JOIN employees e ON r.generated_by = e.employee_id
            WHERE r.generated_by = ? ORDER BY r.generation_date DESC
        """, (user["employee_id"],))
    else:
        raise HTTPException(status_code=403, detail="Acces aux rapports refuse")
    return [dict(r) for r in cursor.fetchall()]


@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    user: dict = Depends(authenticate_with_token),
    db=Depends(get_db)
):
    """Stream a real PDF generated from live DB data."""
    if user["role"] not in ("ceo", "manager"):
        raise HTTPException(status_code=403, detail="Acces refuse")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    report = dict(row)
    if user["role"] == "manager" and report["generated_by"] != user["employee_id"]:
        raise HTTPException(status_code=403, detail="Acces refuse")

    gen = PDF_GENERATORS.get(report.get("report_type", ""))
    if not gen:
        raise HTTPException(status_code=400, detail="Type de rapport non supporte")

    cursor.execute("SELECT first_name, last_name FROM employees WHERE employee_id=?",
                   (report["generated_by"],))
    emp = cursor.fetchone()
    gen_name = f"{emp['first_name']} {emp['last_name']}" if emp else report["generated_by"]

    buf = gen(db=db, user=user,
              period_start=report.get("period_start",""),
              period_end=report.get("period_end",""),
              generated_by_name=gen_name)

    filename = f"{REPORT_LABELS.get(report['report_type'],'Rapport')}_{report_id}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/{report_id}")
def get_report(report_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    if user["role"] not in ("ceo", "manager"):
        raise HTTPException(status_code=403, detail="Acces aux rapports refuse")
    cursor = db.cursor()
    cursor.execute("""
        SELECT r.*, e.first_name || ' ' || e.last_name as generated_by_name
        FROM reports r LEFT JOIN employees e ON r.generated_by = e.employee_id
        WHERE r.report_id = ?
    """, (report_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    if user["role"] == "manager" and dict(row)["generated_by"] != user["employee_id"]:
        raise HTTPException(status_code=403, detail="Acces refuse")
    return dict(row)


@router.post("/generate", status_code=status.HTTP_201_CREATED)
def generate_report(
    report: ReportCreate,
    user: dict = Depends(authenticate_with_token),
    db=Depends(get_db)
):
    if user["role"] not in ("ceo", "manager"):
        raise HTTPException(status_code=403, detail="Acces aux rapports refuse")
    if report.report_type not in PDF_GENERATORS:
        raise HTTPException(status_code=400,
            detail=f"Type invalide. Valeurs: {list(PDF_GENERATORS.keys())}")

    cursor    = db.cursor()
    report_id = f"RPT{datetime.now().strftime('%Y%m%d%H%M%S')}"
    title     = report.title or \
        f"{REPORT_LABELS.get(report.report_type, 'Rapport')} — {datetime.now().strftime('%d/%m/%Y')}"

    cursor.execute("""
        INSERT INTO reports (report_id, report_type, title, period_start, period_end,
            generated_by, generation_date, file_path, filters, parameters, status, content)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (report_id, report.report_type, title,
          report.period_start, report.period_end,
          user["employee_id"], datetime.now().isoformat(),
          None, report.filters or "{}", report.parameters or "{}",
          "Completed", "{}"))
    log_action(cursor, user["employee_id"], "Create", "Report", report_id, f"Generated: {title}")
    db.commit()

    cursor.execute("""
        SELECT r.*, e.first_name || ' ' || e.last_name as generated_by_name
        FROM reports r LEFT JOIN employees e ON r.generated_by = e.employee_id
        WHERE r.report_id = ?
    """, (report_id,))
    row = cursor.fetchone()
    return dict(row) if row else {"report_id": report_id, "status": "Completed"}


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    if user["role"] not in ("ceo", "manager"):
        raise HTTPException(status_code=403, detail="Acces aux rapports refuse")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    if user["role"] == "manager" and dict(row)["generated_by"] != user["employee_id"]:
        raise HTTPException(status_code=403, detail="Acces refuse")
    cursor.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))
    log_action(cursor, user["employee_id"], "Delete", "Report", report_id, f"Deleted {report_id}")
    db.commit()
    return None