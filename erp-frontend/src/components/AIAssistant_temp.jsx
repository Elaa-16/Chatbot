import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  X, Send, Plus, Search, Mic, Paperclip, Bot,
  Maximize2, Minimize2, Sparkles, Sun, Moon,
  FileText, Image as ImageIcon, XCircle, Settings,
  BarChart2, Clock, Trash2, Users, AlertTriangle,
  CalendarOff, Wrench, TrendingUp, TrendingDown,
  CheckCircle2, Circle, Timer, Ban, Package,
  Building2, ChevronRight, Activity
} from 'lucide-react';

const fontLink = document.createElement('link');
fontLink.rel = 'stylesheet';
fontLink.href = 'https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Instrument+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&family=JetBrains+Mono:wght@400;500&display=swap';
document.head.appendChild(fontLink);

const SUGGESTIONS = ['Statut des projets', 'Budget total', 'Projets en retard', 'Employés en congé'];

const makeWelcomeMessage = () => ({
  id: 1, role: 'bot',
  content: "Bonjour. Je suis votre assistant IA pour le système ERP. Je peux analyser vos données, générer des rapports et répondre à toutes vos questions opérationnelles.",
  time: new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
});

const makeNewConversation = () => ({
  id: Date.now(),
  title: 'Nouvelle conversation',
  preview: '',
  date: 'Maintenant',
  messages: [makeWelcomeMessage()],
});

const getUserId = () => {
  try {
    const token = localStorage.getItem('token');
    if (!token) return 'anonymous';
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g,'+').replace(/_/g,'/')));
    return payload.sub || payload.user_id || payload.id || 'anonymous';
  } catch {
    return 'anonymous';
  }
};

const getBotResponse = async (userMessage, lastExchange = {}) => {
  const token = localStorage.getItem("token");
  const userRole = localStorage.getItem("user_role");
  const userId   = localStorage.getItem("user_id");
  const userName = localStorage.getItem("user_name");
  if (!token) return "Session non authentifiée. Veuillez vous connecter.";
  try {
    const response = await fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({ message: userMessage, user_role: userRole || "employee", user_id: userId || "", user_name: userName || "User", last_exchange: lastExchange }),
    });
    if (!response.ok) {
      if (response.status === 503) return "L'assistant IA est temporairement indisponible.";
      if (response.status === 401) return "Session expirée. Veuillez vous reconnecter.";
      return "Une erreur est survenue. Veuillez réessayer.";
    }
    const data = await response.json();
    return data.answer;
  } catch { return "Impossible de joindre le serveur."; }
};

// ═══════════════════════════════════════════════════════
// DESIGN TOKENS
// ═══════════════════════════════════════════════════════
const STATUS_META = {
  'Approved':    { color: '#10b981', bg: 'rgba(16,185,129,0.12)', label: 'Approuvé',    icon: '✓' },
  'Pending':     { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', label: 'En attente',  icon: '◔' },
  'Rejected':    { color: '#ef4444', bg: 'rgba(239,68,68,0.12)',  label: 'Refusé',      icon: '✕' },
  'Done':        { color: '#10b981', bg: 'rgba(16,185,129,0.12)', label: 'Terminé',     icon: '✓' },
  'Blocked':     { color: '#ef4444', bg: 'rgba(239,68,68,0.12)',  label: 'Bloqué',      icon: '⊘' },
  'In Progress': { color: '#3b82f6', bg: 'rgba(59,130,246,0.12)', label: 'En cours',    icon: '▶' },
  'Todo':        { color: '#94a3b8', bg: 'rgba(148,163,184,0.12)',label: 'À faire',     icon: '○' },
  'Critical':    { color: '#f43f5e', bg: 'rgba(244,63,94,0.12)',  label: 'Critique',    icon: '!!' },
  'High':        { color: '#f97316', bg: 'rgba(249,115,22,0.12)', label: 'Élevé',       icon: '!' },
  'Medium':      { color: '#eab308', bg: 'rgba(234,179,8,0.12)',  label: 'Moyen',       icon: '~' },
  'Low':         { color: '#22c55e', bg: 'rgba(34,197,94,0.12)',  label: 'Faible',      icon: '↓' },
  'Available':   { color: '#10b981', bg: 'rgba(16,185,129,0.12)', label: 'Disponible',  icon: '✓' },
  'In Use':      { color: '#3b82f6', bg: 'rgba(59,130,246,0.12)', label: 'En usage',    icon: '▶' },
  'Maintenance': { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', label: 'Maintenance', icon: '⚙' },
  'Completed':   { color: '#10b981', bg: 'rgba(16,185,129,0.12)', label: 'Terminé',     icon: '✓' },
  'Planning':    { color: '#8b5cf6', bg: 'rgba(139,92,246,0.12)', label: 'Planifié',    icon: '◈' },
  'Open':        { color: '#f43f5e', bg: 'rgba(244,63,94,0.12)',  label: 'Ouvert',      icon: '!' },
  'Resolved':    { color: '#10b981', bg: 'rgba(16,185,129,0.12)', label: 'Résolu',      icon: '✓' },
  'Closed':      { color: '#94a3b8', bg: 'rgba(148,163,184,0.12)',label: 'Fermé',       icon: '○' },
};

const LEAVE_TYPE_COLOR = {
  'Annual': '#6366f1', 'Sick': '#f43f5e', 'Personal': '#8b5cf6',
  'Emergency': '#f97316', 'Maternity': '#ec4899', 'Paternity': '#06b6d4',
};

const DEPT_COLOR = {
  'Finance': '#6366f1', 'Projects': '#3b82f6', 'Human Resources': '#ec4899',
  'HR': '#ec4899', 'Operations': '#f97316', 'IT': '#22c55e',
  'Executive': '#f43f5e', 'Sales': '#eab308',
};

const normalizeLabel = (raw) => {
  return (raw || '')
    .toUpperCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/\s*\(.*?\)\s*/g, '')
    .trim();
};

const ENDPOINT_META = {
  'EMPLOYEES':        { icon: Users,         label: 'Équipe',           color: '#6366f1' },
  'LEAVE-REQUESTS':   { icon: CalendarOff,   label: 'Congés',           color: '#f43f5e' },
  'TASKS':            { icon: CheckCircle2,  label: 'Tâches',           color: '#3b82f6' },
  'TASKS-BY-MANAGER': { icon: BarChart2,     label: 'Tâches / Manager', color: '#8b5cf6' },
  'STATS-BY-MANAGER': { icon: Activity,      label: 'Stats / Manager',  color: '#8b5cf6' },
  'PROJECTS':         { icon: Building2,     label: 'Projets',          color: '#0ea5e9' },
  'KPIS':             { icon: TrendingUp,    label: 'KPIs',             color: '#10b981' },
  'ISSUES':           { icon: AlertTriangle, label: 'Incidents',        color: '#ef4444' },
  'EQUIPMENT':        { icon: Wrench,        label: 'Équipements',      color: '#f59e0b' },
  'SUPPLIERS':        { icon: Package,       label: 'Fournisseurs',     color: '#06b6d4' },
  'STATS-SUMMARY':    { icon: BarChart2,     label: 'Vue globale',      color: '#6366f1' },
  'STATS-TASKS':      { icon: Activity,      label: 'Stats tâches',     color: '#3b82f6' },
  'TIMESHEETS':       { icon: Timer,         label: 'Feuilles de temps',color: '#8b5cf6' },
  'NOTIFICATIONS':    { icon: Activity,      label: 'Notifications',    color: '#f59e0b' },
  'STATS-PROJECTS-COUNT':         { icon: BarChart2,    label: 'Répartition projets', color: '#6366f1' },
  'STATS-MANAGER-DELAYED':        { icon: TrendingDown, label: 'Projets en retard',   color: '#ef4444' },
  'STATS-LEAVE-TOP':              { icon: CalendarOff,  label: 'Top congés',          color: '#f43f5e' },
  'STATS-TASKS-OVERDUE':          { icon: Timer,        label: 'Tâches en retard',    color: '#f97316' },
  'STATS-DELAYED-WITH-INCIDENTS': { icon: AlertTriangle,label: 'Retard + Incidents',  color: '#ef4444' },
  'STATS-BUDGET-RISK':            { icon: TrendingUp,   label: 'Budget + Risque',     color: '#f97316' },
  'STATS-MANAGERS-BLOCKED':       { icon: Ban,          label: 'Managers bloqués',    color: '#f43f5e' },
  'STATS-LEAVE-CRITICAL-TASKS':   { icon: AlertTriangle,label: 'Congés + Critiques',  color: '#ef4444' },
};

// ═══════════════════════════════════════════════════════
// BADGE
// ═══════════════════════════════════════════════════════
const Badge = ({ value, size = 'sm' }) => {
  const m = STATUS_META[value];
  if (!m) return <span style={{ fontSize: 12, fontFamily: "'JetBrains Mono',monospace", color: '#94a3b8' }}>{value}</span>;
  const pad = size === 'lg' ? '4px 12px' : '2px 9px';
  const fs  = size === 'lg' ? 12.5 : 11;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      backgroundColor: m.bg, color: m.color,
      borderRadius: 20, padding: pad, fontSize: fs,
      fontWeight: 600, fontFamily: "'Instrument Sans',sans-serif",
      border: `1px solid ${m.color}30`, whiteSpace: 'nowrap',
    }}>
      <span style={{ fontSize: fs - 1 }}>{m.icon}</span>
      {m.label}
    </span>
  );
};

// ═══════════════════════════════════════════════════════
// PROGRESS BAR
// ═══════════════════════════════════════════════════════
const ProgressBar = ({ pct, color, height = 5 }) => {
  const n = parseFloat(pct) || 0;
  const c = color || (n >= 80 ? '#10b981' : n >= 50 ? '#6366f1' : n >= 30 ? '#f59e0b' : '#ef4444');
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height, borderRadius: height, backgroundColor: 'rgba(148,163,184,0.15)', overflow: 'hidden' }}>
        <div style={{ width: `${Math.min(n, 100)}%`, height: '100%', borderRadius: height, backgroundColor: c, transition: 'width .6s ease' }} />
      </div>
      <span style={{ fontSize: 11, fontFamily: "'JetBrains Mono',monospace", color: '#94a3b8', minWidth: 30, textAlign: 'right' }}>{n}%</span>
    </div>
  );
};

// ═══════════════════════════════════════════════════════
// BLOCK PARSER — FIX: filtre ligne "Bilan ..."
// ═══════════════════════════════════════════════════════
const parsePipeLine = (line) => {
  const clean = line.replace(/^[\s\-•·]+/, '').trim();
  if (!clean) return null;
  if (clean.endsWith('|')) return null;
  if (/^Repartition:/i.test(clean)) return null;
  if (/^Total\s/i.test(clean)) return null;
  if (/^Bilan\s/i.test(clean)) return null; // FIX: ignorer la ligne résumé bilan

  // Employee line: "First Last — Position — Department"
  if (clean.match(/^[A-ZÀÂÇÉÈÊËÎÏÔÙÛÜ]/) && clean.includes(' — ') && !clean.includes(' | ')) {
    const parts = clean.split(' — ');
    return { _type: 'employee', Nom: parts[0]?.trim(), Poste: parts[1]?.trim(), Département: parts[2]?.trim() };
  }

 const obj = {};
  const segments = clean.split(' | ');
  segments.forEach((seg, idx) => {
    const colonIdx = seg.indexOf(':');
    if (colonIdx > -1) {
      const k = seg.slice(0, colonIdx).trim();
      const v = seg.slice(colonIdx + 1).trim();
      if (k) obj[k] = v;
    } else if (idx === 0) {
      obj['_name'] = seg.trim();
    }
  });

  // FIX: lignes au format "T005: Réunion sécurité | Statut: ..."
  // parsées en obj['T005'] = 'Réunion sécurité' → extraire en _name
  if (!obj['_name']) {
    const firstKey = Object.keys(obj)[0] || '';
    if (/^[A-Z]{1,3}\d+$/.test(firstKey)) {
      obj['_name'] = obj[firstKey];
      obj['_id']   = firstKey;
      delete obj[firstKey];
    }
  }

  if (Object.keys(obj).length === 0) return null;
  return obj;
};

const parseBlock = (blockText) => {
  const lines = blockText.trim().split('\n');
  if (!lines.length) return null;

  const headerMatch = lines[0].match(/^===\s*(.+?)\s*===$/);
  if (!headerMatch) return null;
  const rawLabel = headerMatch[1];

  const countLine  = lines.find(l => /^Resultats\s*\(/.test(l.trim()));
  const countMatch = countLine?.match(/\((\d+)/);
  const count      = countMatch ? parseInt(countMatch[1]) : null;

  if (count === 0 || lines.some(l => /Aucun.*(resultat|donnee)/i.test(l))) {
    return { rawLabel, type: 'empty' };
  }

  // FIX: conserver les lignes brutes AVANT filtrage pour récupérer "Bilan ..."
  const allDataLines = lines.filter(l => {
    const t = l.trim();
    return t && !/^===/.test(t) && !/^Resultats\s*\(/.test(t) && !/^Aucun/.test(t);
  });

  // Ligne résumé bilan (ex: "Bilan Nadia Hamdi : 2j approuves | 2j en attente")
  const bilanLine = allDataLines.find(l => /^Bilan\s/i.test(l.trim()))?.trim() || null;

  const dataLines = allDataLines.filter(l => {
    const t = l.trim();
    if (/^Total\s/i.test(t)) return false;
    if (/^Repartition:/i.test(t)) return false;
    if (/^Bilan\s/i.test(t)) return false; // FIX: exclure des dataLines
    return true;
  });

  if (!dataLines.length) {
    const statLines = lines.filter(l => {
      const t = l.trim();
      return t && !t.startsWith('===') && !t.startsWith('Resultats') && t.includes(':');
    });
    if (statLines.length) {
      const stats = {};
      statLines.forEach(sl => {
        sl.split(' | ').forEach(seg => {
          const c = seg.indexOf(':');
          if (c > -1) stats[seg.slice(0, c).trim()] = seg.slice(c + 1).trim();
        });
      });
      if (Object.keys(stats).length) return { rawLabel, type: 'stats', stats };
    }
    return null;
  }

  const rows = dataLines.map(parsePipeLine).filter(Boolean);
  // FIX: inclure bilanLine dans le résultat parsé
  return { rawLabel, type: 'rows', count: count ?? rows.length, rows, bilanLine };
};

// ═══════════════════════════════════════════════════════
// MANAGER-DELAYED BLOCK PARSER
// ═══════════════════════════════════════════════════════
const parseManagerDelayedBlock = (blockText) => {
  const lines = blockText.trim().split('\n');
  const headerMatch = lines[0].match(/^===\s*(.+?)\s*===$/);
  if (!headerMatch) return null;

  const managers = [];
  let current = null;

  for (const line of lines.slice(1)) {
    const t = line.trim();
    if (!t || /^Resultats/.test(t)) continue;

    if (/^-\s+/.test(line) && t.includes('Projets en retard:')) {
      if (current) managers.push(current);
      const clean = t.replace(/^-\s+/, '');
      const parts = clean.split(' | ');
      const nameMatch = parts[0]?.match(/^(.+?)\s*\((.+?)\)$/);
      const delayMatch = parts[1]?.match(/Projets en retard:\s*(\d+)\s*\/\s*(\d+)/);
      current = {
        name: nameMatch ? nameMatch[1].trim() : parts[0]?.trim(),
        dept: nameMatch ? nameMatch[2].trim() : '',
        delayed: delayMatch ? parseInt(delayMatch[1]) : 0,
        total: delayMatch ? parseInt(delayMatch[2]) : 0,
        projects: [],
      };
    } else if (/^[•·]/.test(t) && current) {
      const clean = t.replace(/^[•·]\s*/, '');
      const dashIdx = clean.indexOf(' — ');
      const projectName = dashIdx > -1 ? clean.slice(0, dashIdx) : clean;
      const rest = dashIdx > -1 ? clean.slice(dashIdx + 3) : '';
      const proj = { name: projectName };
      rest.split(' | ').forEach(seg => {
        const c = seg.indexOf(':');
        if (c > -1) { proj[seg.slice(0,c).trim()] = seg.slice(c+1).trim(); }
        else if (seg.match(/(\d+)j/)) { proj['Retard'] = seg.trim(); }
      });
      current.projects.push(proj);
    }
  }
  if (current) managers.push(current);
  return { rawLabel: headerMatch[1], type: 'manager-delayed', managers };
};

// ═══════════════════════════════════════════════════════
// CARD RENDERERS
// ═══════════════════════════════════════════════════════
const EmployeeCard = ({ row, C }) => {
  const nom    = row['Nom'] || row['_name'] || '';
  const poste  = row['Poste'] || row['Position'] || '';
  const dept   = row['Dept'] || row['Département'] || row['Department'] || '';
  const tasks  = row['Taches critiques'] || row['Tâches critiques'] || '';
  const conge  = row['Conge'] || row['Congé'] || '';

  const dColor   = DEPT_COLOR[dept] || '#6366f1';
  const initials = (nom || '?').split(' ').map(w => w[0]).filter(Boolean).slice(0, 2).join('').toUpperCase();

  return (
    <div
      style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '10px 14px', borderRadius: 10, backgroundColor: C.cardBg, border: `1px solid ${C.border}`, transition: 'background .15s' }}
      onMouseEnter={e => e.currentTarget.style.backgroundColor = C.cardHover}
      onMouseLeave={e => e.currentTarget.style.backgroundColor = C.cardBg}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{
          width: 34, height: 34, borderRadius: 9, flexShrink: 0,
          backgroundColor: `${dColor}18`, border: `1.5px solid ${dColor}40`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 12, fontWeight: 700, color: dColor, fontFamily: "'Syne',sans-serif"
        }}>
          {initials || '?'}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: C.textPrimary, fontFamily: "'Instrument Sans',sans-serif" }}>
            {nom || '—'}
          </div>
          {poste && (
            <div style={{ fontSize: 11.5, color: C.textMuted, marginTop: 1 }}>{poste}</div>
          )}
        </div>
        {dept && (
          <span style={{
            fontSize: 10.5, fontWeight: 600, color: dColor,
            backgroundColor: `${dColor}14`, border: `1px solid ${dColor}30`,
            borderRadius: 6, padding: '2px 7px', whiteSpace: 'nowrap', flexShrink: 0
          }}>
            {dept}
          </span>
        )}
      </div>
      {tasks && (
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 6, fontSize: 11.5, color: C.textMuted, paddingLeft: 44 }}>
          <span style={{ color: '#f43f5e', fontWeight: 700, flexShrink: 0 }}>⚠</span>
          <span style={{ lineHeight: 1.4 }}>{tasks}</span>
        </div>
      )}
      {conge && (
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 6, fontSize: 11.5, color: C.textMuted, paddingLeft: 44 }}>
          <span style={{ flexShrink: 0 }}>🏖</span>
          <span style={{ lineHeight: 1.4 }}>{conge}</span>
        </div>
      )}
    </div>
  );
};

const LeaveCard = ({ row, C }) => {
  const status  = row['Statut'] || row['Status'] || '';
  const ltype   = row['Type'] || '';
  const ltColor = LEAVE_TYPE_COLOR[ltype] || '#6366f1';
  const days    = row['Jours'] || row['Days'] || '';
  const name    = row['_name'] || row['Nom'] || '';
  const duVal   = row['Du'] || '';
  return (
    <div style={{ padding: '10px 14px', borderRadius: 10, backgroundColor: C.cardBg, border: `1px solid ${C.border}`, borderLeft: `3px solid ${ltColor}`, transition: 'background .15s' }}
      onMouseEnter={e => e.currentTarget.style.backgroundColor = C.cardHover}
      onMouseLeave={e => e.currentTarget.style.backgroundColor = C.cardBg}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: ltColor, flexShrink: 0 }} />
          {name && <span style={{ fontSize: 13.5, fontWeight: 600, color: C.textPrimary, fontFamily: "'Instrument Sans',sans-serif" }}>{name}</span>}
          {ltype && <span style={{ fontSize: 11, fontWeight: 600, color: ltColor, backgroundColor: `${ltColor}14`, borderRadius: 6, padding: '1px 7px', border: `1px solid ${ltColor}30` }}>{ltype}</span>}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          {days && <span style={{ fontSize: 11.5, color: C.textMuted, fontFamily: "'JetBrains Mono',monospace" }}>{days}j</span>}
          {status && <Badge value={status} />}
        </div>
      </div>
      {duVal && <div style={{ marginTop: 5, fontSize: 11.5, color: C.textMuted, display: 'flex', alignItems: 'center', gap: 4 }}><Clock size={10} strokeWidth={2} />{duVal}</div>}
    </div>
  );
};

const TaskCard = ({ row, C }) => {
  const status   = row['Statut'] || row['Status'] || '';
  const priority = row['Priorite'] || row['Priority'] || row['Priorité'] || '';
  const title    = row['_name'] || row['Titre'] || row['Title'] || '';
  const assignee = row['Assigne a'] || row['Assigned'] || row['Assigné à'] || '';
  const project  = row['Projet'] || row['Project'] || '';
  const due      = row['Echeance'] || row['Due'] || row['Échéance'] || '';
  const sm = STATUS_META[status] || {};
  return (
    <div style={{ padding: '10px 14px', borderRadius: 10, backgroundColor: C.cardBg, border: `1px solid ${C.border}`, borderLeft: `3px solid ${sm.color || '#6366f1'}`, transition: 'background .15s' }}
      onMouseEnter={e => e.currentTarget.style.backgroundColor = C.cardHover}
      onMouseLeave={e => e.currentTarget.style.backgroundColor = C.cardBg}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: C.textPrimary, fontFamily: "'Instrument Sans',sans-serif", lineHeight: 1.3 }}>{title}</div>
          <div style={{ marginTop: 4, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            {assignee && <span style={{ fontSize: 11.5, color: C.textMuted }}>👤 {assignee}</span>}
            {project && <span style={{ fontSize: 11.5, color: C.textMuted }}>📁 {project}</span>}
            {due && <span style={{ fontSize: 11.5, color: C.textMuted, fontFamily: "'JetBrains Mono',monospace" }}>📅 {due}</span>}
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, flexShrink: 0 }}>
          <Badge value={status} />
          {priority && <Badge value={priority} />}
        </div>
      </div>
    </div>
  );
};

const ProjectCard = ({ row, C }) => {
  const status = row['Statut'] || row['Status'] || '';
  const name   = row['_name'] || '';
  const pct    = (row['Avancement'] || '').replace('%', '');
  const budget = row['Budget'] || '';
  const lieu   = row['Lieu'] || '';
  return (
    <div style={{ padding: '12px 14px', borderRadius: 10, backgroundColor: C.cardBg, border: `1px solid ${C.border}`, transition: 'background .15s' }}
      onMouseEnter={e => e.currentTarget.style.backgroundColor = C.cardHover}
      onMouseLeave={e => e.currentTarget.style.backgroundColor = C.cardBg}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, marginBottom: 8 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: C.textPrimary, fontFamily: "'Instrument Sans',sans-serif" }}>{name}</div>
          <div style={{ display: 'flex', gap: 8, marginTop: 3, flexWrap: 'wrap' }}>
            {lieu && <span style={{ fontSize: 11.5, color: C.textMuted }}>📍 {lieu}</span>}
            {budget && <span style={{ fontSize: 11.5, color: C.textMuted }}>💰 {budget}</span>}
          </div>
        </div>
        <Badge value={status} />
      </div>
      {pct && <ProgressBar pct={pct} />}
    </div>
  );
};

const KpiCard = ({ row, C }) => {
  const name   = row['_name'] || row['Projet'] || row['Project'] || '';
  const retard = parseInt(row['Retard'] || '0');
  const budget = parseFloat(row['Budget'] || '0');
  const cpi    = parseFloat(row['CPI'] || '0');
  const spi    = parseFloat(row['SPI'] || '0');
  const risque = row['Risque'] || '';
  const avance = (row['Avancement'] || '').replace('%', '');
  const rm     = STATUS_META[risque] || {};

  const delayColor  = retard > 30 ? '#ef4444' : retard > 0 ? '#f59e0b' : '#10b981';
  const budgetColor = budget > 15 ? '#ef4444' : budget > 5 ? '#f59e0b' : '#10b981';

  return (
    <div style={{ padding: '12px 14px', borderRadius: 10, backgroundColor: C.cardBg, border: `1px solid ${C.border}`, borderLeft: `3px solid ${rm.color || '#10b981'}`, transition: 'background .15s' }}
      onMouseEnter={e => e.currentTarget.style.backgroundColor = C.cardHover}
      onMouseLeave={e => e.currentTarget.style.backgroundColor = C.cardBg}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <span style={{ fontSize: 13.5, fontWeight: 700, color: C.textPrimary, fontFamily: "'Instrument Sans',sans-serif", flex: 1, minWidth: 0, marginRight: 8 }}>
          {name || '—'}
        </span>
        {risque && <Badge value={risque} />}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 6 }}>
        {[
          { label: 'Retard',   value: `${retard}j`,       color: delayColor },
          { label: 'Budget Δ', value: `${budget}%`,        color: budgetColor },
          { label: 'CPI',      value: cpi.toFixed(2),      color: cpi >= 1 ? '#10b981' : '#ef4444' },
          { label: 'SPI',      value: spi.toFixed(2),      color: spi >= 1 ? '#10b981' : '#ef4444' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ textAlign: 'center', padding: '6px 4px', borderRadius: 7, backgroundColor: `${color}10` }}>
            <div style={{ fontSize: 13, fontWeight: 700, color, fontFamily: "'JetBrains Mono',monospace" }}>{value}</div>
            <div style={{ fontSize: 9.5, color: C.textMuted, marginTop: 2, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
          </div>
        ))}
      </div>
      {avance && <div style={{ marginTop: 8 }}><ProgressBar pct={avance} /></div>}
    </div>
  );
};

const IssueCard = ({ row, C }) => {
  const sev    = row['Severite'] || row['Severity'] || row['Sévérité'] || '';
  const status = row['Statut'] || row['Status'] || '';
  const title  = row['_name'] || '';
  const cat    = row['Categorie'] || row['Category'] || row['Catégorie'] || '';
  const proj   = row['Projet'] || row['Project'] || '';
  const sm     = STATUS_META[sev] || {};
  return (
    <div style={{ padding: '10px 14px', borderRadius: 10, backgroundColor: C.cardBg, border: `1px solid ${C.border}`, borderLeft: `3px solid ${sm.color || '#ef4444'}`, transition: 'background .15s' }}
      onMouseEnter={e => e.currentTarget.style.backgroundColor = C.cardHover}
      onMouseLeave={e => e.currentTarget.style.backgroundColor = C.cardBg}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: C.textPrimary, fontFamily: "'Instrument Sans',sans-serif" }}>{title}</div>
          <div style={{ marginTop: 4, display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            {cat && <span style={{ fontSize: 11, color: C.textMuted, backgroundColor: C.tagBg, padding: '1px 7px', borderRadius: 5 }}>{cat}</span>}
            {proj && <span style={{ fontSize: 11.5, color: C.textMuted }}>📁 {proj}</span>}
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end', flexShrink: 0 }}>
          {sev && <Badge value={sev} />}
          {status && <Badge value={status} />}
        </div>
      </div>
    </div>
  );
};

const ManagerCard = ({ row, C }) => {
  const name    = row['manager_name'] || row['_name'] || '';
  const dept    = row['department'] || row['Département'] || row['Department'] || '';
  const dColor  = DEPT_COLOR[dept] || '#6366f1';
  const blocked = parseInt(row['Bloques'] || row['blocked'] || row['Bloquees'] || row['blocked_tasks'] || '0');
  const critical= parseInt(row['Critiques'] || row['critical_tasks'] || row['Critiques ouvertes'] || row['open_critical'] || '0');
  const total   = parseInt(row['Total'] || row['total_tasks'] || '0');
  const done    = parseInt(row['Termines'] || row['done'] || row['Terminees'] || row['done_tasks'] || '0');
  const avance  = row['Avancement moy'] ? row['Avancement moy'].replace('%','') : null;
  const donePct = total > 0 ? Math.round((done/total)*100) : 0;
  return (
    <div style={{ padding: '12px 14px', borderRadius: 10, backgroundColor: C.cardBg, border: `1px solid ${C.border}`, transition: 'background .15s' }}
      onMouseEnter={e => e.currentTarget.style.backgroundColor = C.cardHover}
      onMouseLeave={e => e.currentTarget.style.backgroundColor = C.cardBg}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        <div style={{ width: 34, height: 34, borderRadius: 9, backgroundColor: `${dColor}18`, border: `1.5px solid ${dColor}40`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color: dColor, fontFamily: "'Syne',sans-serif", flexShrink: 0 }}>
          {name.split(' ').map(w => w[0]).filter(Boolean).slice(0,2).join('').toUpperCase()}
        </div>
        <div>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: C.textPrimary, fontFamily: "'Instrument Sans',sans-serif" }}>{name}</div>
          <div style={{ fontSize: 11, color: dColor, marginTop: 1 }}>{dept}</div>
        </div>
        <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: C.textPrimary, fontFamily: "'JetBrains Mono',monospace" }}>{total}</div>
          <div style={{ fontSize: 9.5, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>tâches</div>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
        <div style={{ padding: '6px 10px', borderRadius: 7, backgroundColor: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.15)' }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#ef4444', fontFamily: "'JetBrains Mono',monospace" }}>{blocked}</div>
          <div style={{ fontSize: 9.5, color: '#ef4444', opacity: 0.7, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Bloquées</div>
        </div>
        <div style={{ padding: '6px 10px', borderRadius: 7, backgroundColor: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.15)' }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#f43f5e', fontFamily: "'JetBrains Mono',monospace" }}>{critical}</div>
          <div style={{ fontSize: 9.5, color: '#f43f5e', opacity: 0.7, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Critiques</div>
        </div>
      </div>
      {avance && <div style={{ marginTop: 8 }}><ProgressBar pct={avance} /></div>}
      {total > 0 && !avance && <div style={{ marginTop: 8 }}><ProgressBar pct={donePct} color="#10b981" height={4} /></div>}
    </div>
  );
};

const ManagerDelayedCard = ({ manager, C }) => {
  const dColor   = DEPT_COLOR[manager.dept] || '#ef4444';
  const initials = manager.name.split(' ').map(w => w[0]).filter(Boolean).slice(0, 2).join('').toUpperCase();
  const ratio    = manager.total > 0 ? manager.delayed / manager.total : 0;
  const ratioColor = ratio >= 0.8 ? '#ef4444' : ratio >= 0.5 ? '#f97316' : '#f59e0b';
  return (
    <div style={{ borderRadius: 12, backgroundColor: C.cardBg, border: `1px solid ${C.border}`, borderLeft: `3px solid ${ratioColor}`, overflow: 'hidden', transition: 'background .15s' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '11px 14px 10px', backgroundColor: `${ratioColor}08`, borderBottom: `1px solid ${C.border}` }}>
        <div style={{ width: 34, height: 34, borderRadius: 9, flexShrink: 0, backgroundColor: `${dColor}18`, border: `1.5px solid ${dColor}40`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color: dColor, fontFamily: "'Syne',sans-serif" }}>{initials}</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: C.textPrimary, fontFamily: "'Instrument Sans',sans-serif" }}>{manager.name}</div>
          <div style={{ fontSize: 11, color: dColor, marginTop: 1 }}>{manager.dept}</div>
        </div>
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: ratioColor, fontFamily: "'JetBrains Mono',monospace", lineHeight: 1 }}>
            {manager.delayed}<span style={{ fontSize: 12, color: C.textMuted, fontWeight: 400 }}>/{manager.total}</span>
          </div>
          <div style={{ fontSize: 9.5, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.06em', marginTop: 2 }}>en retard</div>
        </div>
      </div>
      {manager.projects.length > 0 && (
        <div style={{ padding: '6px 10px 8px' }}>
          {manager.projects.map((proj, i) => {
            const riskMeta = STATUS_META[proj['Risque']] || {};
            const avance   = (proj['Avancement'] || '').replace('%', '');
            const retard   = proj['Retard'] || '';
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 6px', borderRadius: 7, marginBottom: 2, backgroundColor: i % 2 === 0 ? 'transparent' : C.cardHover }}>
                <div style={{ width: 5, height: 5, borderRadius: '50%', backgroundColor: riskMeta.color || '#94a3b8', flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ fontSize: 12, color: C.textPrimary, fontFamily: "'Instrument Sans',sans-serif", fontWeight: 500 }}>{proj.name}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                  {retard && <span style={{ fontSize: 11, fontFamily: "'JetBrains Mono',monospace", color: '#ef4444', fontWeight: 600 }}>{retard}</span>}
                  {avance && <span style={{ fontSize: 11, fontFamily: "'JetBrains Mono',monospace", color: C.textMuted }}>{avance}%</span>}
                  {proj['Risque'] && <Badge value={proj['Risque']} />}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

const GenericCard = ({ row, C }) => {
  const entries = Object.entries(row).filter(([k]) => !k.startsWith('_'));
  const name = row['_name'];
  return (
    <div style={{ padding: '10px 14px', borderRadius: 10, backgroundColor: C.cardBg, border: `1px solid ${C.border}`, transition: 'background .15s' }}
      onMouseEnter={e => e.currentTarget.style.backgroundColor = C.cardHover}
      onMouseLeave={e => e.currentTarget.style.backgroundColor = C.cardBg}>
      {name && <div style={{ fontSize: 13.5, fontWeight: 600, color: C.textPrimary, fontFamily: "'Instrument Sans',sans-serif", marginBottom: 6 }}>{name}</div>}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 16px' }}>
        {entries.map(([k, v]) => {
          const isStatus = STATUS_META[v];
          return (
            <div key={k}>
              <div style={{ fontSize: 10, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600, marginBottom: 2 }}>{k}</div>
              {isStatus ? <Badge value={v} /> : <div style={{ fontSize: 13, color: C.textPrimary, fontFamily: "'Instrument Sans',sans-serif", fontWeight: 500 }}>{v}</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════
// STATS SUMMARY
// ═══════════════════════════════════════════════════════
const StatsSummaryBlock = ({ stats, C }) => {
  const tiles = [
    { key: 'Projets total',  icon: Building2,    color: '#6366f1' },
    { key: 'En cours',       icon: Activity,     color: '#3b82f6' },
    { key: 'Termines',       icon: CheckCircle2, color: '#10b981' },
    { key: 'Budget total',   icon: TrendingUp,   color: '#f59e0b' },
    { key: 'Cout reel',      icon: TrendingDown, color: '#f97316' },
    { key: 'Avancement moy', icon: BarChart2,    color: '#8b5cf6' },
  ];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
      {tiles.map(({ key, icon: Icon, color }) => {
        const val = stats[key];
        if (!val) return null;
        return (
          <div key={key} style={{ padding: '12px 14px', borderRadius: 10, backgroundColor: `${color}0f`, border: `1px solid ${color}25` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <Icon size={13} color={color} strokeWidth={2} />
              <span style={{ fontSize: 10, color, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em' }}>{key}</span>
            </div>
            <div style={{ fontSize: 17, fontWeight: 700, color: C.textPrimary, fontFamily: "'JetBrains Mono',monospace", lineHeight: 1 }}>{val}</div>
          </div>
        );
      })}
    </div>
  );
};

// ═══════════════════════════════════════════════════════
// BLOCK RENDERER — FIX: affiche bilanLine pour LEAVE-REQUESTS
// ═══════════════════════════════════════════════════════
const BlockRenderer = ({ block, darkMode, C }) => {
  const canonicalLabel = normalizeLabel(block.rawLabel);
  const meta   = ENDPOINT_META[canonicalLabel] || { icon: Activity, label: block.rawLabel, color: '#6366f1' };
  const Icon   = meta.icon;
  const accent = meta.color;

  const isCrossed = block.rawLabel !== canonicalLabel && block.rawLabel.includes('(');
  const subtitle  = isCrossed ? block.rawLabel.match(/\((.+?)\)/)?.[1] : null;

  const header = (count) => (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', marginBottom: 8, borderRadius: 10, backgroundColor: `${accent}0e`, border: `1px solid ${accent}20` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 26, height: 26, borderRadius: 7, backgroundColor: `${accent}20`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon size={13} color={accent} strokeWidth={2} />
        </div>
        <div>
          <span style={{ fontFamily: "'Syne',sans-serif", fontSize: 12, fontWeight: 700, color: accent, textTransform: 'uppercase', letterSpacing: '0.07em' }}>{meta.label}</span>
          {subtitle && <div style={{ fontSize: 10, color: C.textMuted, marginTop: 1 }}>{subtitle}</div>}
        </div>
      </div>
      {count != null && (
        <span style={{ fontSize: 11, fontWeight: 600, color: accent, backgroundColor: `${accent}15`, borderRadius: 20, padding: '2px 10px', fontFamily: "'JetBrains Mono',monospace", border: `1px solid ${accent}25` }}>
          {count} résultat{count > 1 ? 's' : ''}
        </span>
      )}
    </div>
  );

  if (block.type === 'empty') return (
    <div style={{ marginBottom: 8 }}>
      {header(0)}
      <div style={{ padding: '10px 14px', borderRadius: 10, backgroundColor: C.cardBg, border: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', gap: 8 }}>
        <Circle size={14} color={C.textMuted} />
        <span style={{ fontSize: 13, color: C.textMuted, fontStyle: 'italic' }}>Aucun résultat</span>
      </div>
    </div>
  );

  if (block.type === 'stats') {
    if (canonicalLabel === 'STATS-SUMMARY') return (
      <div style={{ marginBottom: 8 }}>{header(null)}<StatsSummaryBlock stats={block.stats} C={C} /></div>
    );
    return (
      <div style={{ marginBottom: 8 }}>
        {header(null)}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {Object.entries(block.stats).map(([k, v]) => (
            <div key={k} style={{ flex: '1 1 100px', padding: '10px 12px', borderRadius: 10, backgroundColor: C.cardBg, border: `1px solid ${C.border}`, textAlign: 'center' }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: C.textPrimary, fontFamily: "'JetBrains Mono',monospace" }}>{v}</div>
              <div style={{ fontSize: 10, color: C.textMuted, marginTop: 3, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{k}</div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (block.type === 'manager-delayed') {
    const managers = block.managers || [];
    return (
      <div style={{ marginBottom: 8 }}>
        {header(managers.length)}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {managers.map((mgr, i) => <ManagerDelayedCard key={i} manager={mgr} C={C} />)}
        </div>
      </div>
    );
  }

  if (block.type === 'rows') {
    const rows = block.rows;
    const bilanLine = block.bilanLine || null; // FIX: récupérer la ligne résumé

    const renderRow = (row, i) => {
      if (canonicalLabel === 'EMPLOYEES')        return <EmployeeCard key={i} row={row} C={C} />;
      if (canonicalLabel === 'LEAVE-REQUESTS')   return <LeaveCard    key={i} row={row} C={C} />;
      if (canonicalLabel === 'TASKS')            return <TaskCard     key={i} row={row} C={C} />;
      if (canonicalLabel === 'PROJECTS')         return <ProjectCard  key={i} row={row} C={C} />;
      if (canonicalLabel === 'KPIS')             return <KpiCard      key={i} row={row} C={C} />;
      if (canonicalLabel === 'ISSUES')           return <IssueCard    key={i} row={row} C={C} />;
      if (canonicalLabel === 'TASKS-BY-MANAGER' || canonicalLabel === 'STATS-BY-MANAGER')
                                                 return <ManagerCard  key={i} row={row} C={C} />;
      return <GenericCard key={i} row={row} C={C} />;
    };

    const isGrid = canonicalLabel === 'EMPLOYEES' && rows.length > 3;

    return (
      <div style={{ marginBottom: 8 }}>
        {header(rows.length)}

        {/* FIX: bandeau résumé bilan congés */}
        {bilanLine && canonicalLabel === 'LEAVE-REQUESTS' && (
          <div style={{
            padding: '8px 14px',
            marginBottom: 8,
            borderRadius: 8,
            backgroundColor: 'rgba(244,63,94,0.08)',
            border: '1px solid rgba(244,63,94,0.2)',
            fontSize: 12.5,
            fontWeight: 600,
            color: '#f43f5e',
            fontFamily: "'Instrument Sans',sans-serif",
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}>
            <CalendarOff size={13} strokeWidth={2} />
            {bilanLine}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: isGrid ? 'repeat(2,1fr)' : '1fr', gap: 6 }}>
          {rows.map((row, i) => renderRow(row, i))}
        </div>
      </div>
    );
  }

  return null;
};

// ═══════════════════════════════════════════════════════
// MESSAGE CONTENT
// ═══════════════════════════════════════════════════════
const MessageContent = ({ text, darkMode, C }) => {
  if (!text || typeof text !== 'string') text = String(text ?? '');

  const lines    = text.split('\n');
  const sections = [];
  let block      = null;

  for (const line of lines) {
    if (/^===\s*.+\s*===$/.test(line)) {
      if (block) sections.push(block);
      block = { type: 'block', lines: [line] };
    } else if (block) {
      block.lines.push(line);
    } else {
      if (!sections.length || sections[sections.length - 1].type !== 'text') sections.push({ type: 'text', lines: [] });
      sections[sections.length - 1].lines.push(line);
    }
  }
  if (block) sections.push(block);

  return (
    <div>
      {sections.map((section, si) => {
        if (section.type === 'block') {
          const raw = section.lines.join('\n');
          if (/^===\s*STATS-MANAGER-DELAYED/i.test(raw)) {
            const parsed = parseManagerDelayedBlock(raw);
            if (parsed) return <BlockRenderer key={si} block={parsed} darkMode={darkMode} C={C} />;
          }
          const parsed = parseBlock(raw);
          if (parsed) return <BlockRenderer key={si} block={parsed} darkMode={darkMode} C={C} />;
          return <pre key={si} style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11.5, color: C.textPrimary, whiteSpace: 'pre-wrap', margin: '4px 0', lineHeight: 1.6 }}>{section.lines.join('\n')}</pre>;
        }
        const content = section.lines.join('\n').trim();
        if (!content) return null;
        return (
          <div key={si} style={{ marginBottom: 6 }}>
            {section.lines.map((line, li) => {
              if (!line.trim()) return <div key={li} style={{ height: 6 }} />;
              const numbered = line.match(/^(\d+)\.\s+(.+)/);
              if (numbered) return (
                <div key={li} style={{ display: 'flex', gap: 8, marginBottom: 4, alignItems: 'flex-start' }}>
                  <span style={{ width: 20, height: 20, borderRadius: '50%', flexShrink: 0, marginTop: 1, backgroundColor: `${C.accent}18`, color: C.accent, fontSize: 11, fontWeight: 700, fontFamily: "'JetBrains Mono',monospace", display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{numbered[1]}</span>
                  <span style={{ fontSize: 13.5, color: C.textPrimary, fontFamily: "'Instrument Sans',sans-serif", lineHeight: 1.6 }}>
                    {numbered[2].split(/(\*\*[^*]+\*\*)/).map((p, j) => p.startsWith('**') && p.endsWith('**') ? <strong key={j} style={{ fontWeight: 600, color: C.accent }}>{p.slice(2,-2)}</strong> : p)}
                  </span>
                </div>
              );
              return (
                <div key={li} style={{ fontSize: 13.5, color: C.textPrimary, fontFamily: "'Instrument Sans',sans-serif", lineHeight: 1.65, marginBottom: 2 }}>
                  {line.split(/(\*\*[^*]+\*\*)/).map((p, j) => p.startsWith('**') && p.endsWith('**') ? <strong key={j} style={{ fontWeight: 600, color: C.accent }}>{p.slice(2,-2)}</strong> : p)}
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};

// ═══════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════
const decodeJWT = (token) => {
  try { return JSON.parse(atob(token.split('.')[1].replace(/-/g,'+').replace(/_/g,'/'))); }
  catch { return null; }
};
const getRoleConfig = (role) => {
  const r = (role || '').toLowerCase();
  if (r === 'ceo')      return { label: 'CEO · Directeur', color: '#c4b5fd', bg: 'rgba(196,181,253,0.12)', dot: '#a78bfa' };
  if (r === 'manager')  return { label: 'Manager',         color: '#67e8f9', bg: 'rgba(103,232,249,0.1)',  dot: '#22d3ee' };
  if (r === 'rh')       return { label: 'RH',              color: '#fda4af', bg: 'rgba(253,164,175,0.1)',  dot: '#fb7185' };
  if (r === 'employee') return { label: 'Employé',         color: '#86efac', bg: 'rgba(134,239,172,0.1)',  dot: '#4ade80' };
  return { label: role || 'Utilisateur', color: '#93c5fd', bg: 'rgba(147,197,253,0.1)', dot: '#60a5fa' };
};
const getUserFromJWT = () => {
  const token = localStorage.getItem('token');
  if (token) {
    const p = decodeJWT(token);
    if (p) {
      // Convert "nadia.hamdi" → "Nadia Hamdi"
      const name = (p.name || p.sub || 'Utilisateur')
        .split('.')
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');
      return { name, role: p.role || 'user', email: p.email || '' };
    }
  }
  return null;
};

// ═══════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════
const AIAssistant = ({ onClose, user: userProp }) => {
const [conversations, setConversations] = useState(() => {
  try {
    const userId = getUserId();
    const saved = localStorage.getItem(`erp_chat_conversations_${userId}`);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed?.length) return parsed;
    }
  } catch {}
  return [makeNewConversation()];
});

const [activeConvId, setActiveConvId] = useState(() => {
  try {
    const userId = getUserId();
    const saved = localStorage.getItem(`erp_chat_conversations_${userId}`);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed?.length) return parsed[0].id;
    }
  } catch {}
  return conversations?.[0]?.id ?? Date.now();
});
  const activeConv  = conversations.find(c => c.id === activeConvId);
  const messages    = activeConv?.messages || [];

  const [input, setInput]               = useState('');
  const [isTyping, setIsTyping]         = useState(false);
  const [expandState, setExpandState]   = useState('normal');
  const [darkMode, setDarkMode]         = useState(true);
  const [currentUser]                   = useState(() => userProp || getUserFromJWT() || { name: 'Ahmed Trabelsi', role: 'ceo', email: '' });
  const [searchQuery, setSearchQuery]   = useState('');
  const [isListening, setIsListening]   = useState(false);
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [micError, setMicError]         = useState('');
  const [inputFocused, setInputFocused] = useState(false);
  useEffect(() => {
  try {
    localStorage.setItem('erp_chat_conversations', JSON.stringify(conversations));

  } catch {}
}, [conversations]);

  const messagesEndRef  = useRef(null);
  const fileInputRef    = useRef(null);
  const recognitionRef  = useRef(null);
  const lastExchangeRef = useRef({});

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isTyping]);

  const updateConv = (id, fn) => setConversations(prev => prev.map(c => c.id === id ? fn(c) : c));
  const addMessage = (convId, msg) => updateConv(convId, c => {
    const msgs = [...c.messages, msg];
    const firstUser = msgs.find(m => m.role === 'user');
    const title = firstUser ? (firstUser.content.length > 34 ? firstUser.content.slice(0,34)+'…' : firstUser.content) : c.title;
    return { ...c, messages: msgs, title, preview: msg.role === 'user' ? msg.content.slice(0,55) : c.preview, date: 'Maintenant' };
  });

  const createNewConversation = () => {
    const conv = makeNewConversation();
    setConversations(prev => [conv, ...prev]);
    setActiveConvId(conv.id);
    setInput('');
  };

  const deleteConversation = (id, e) => {
    e.stopPropagation();
    setConversations(prev => {
      const rest = prev.filter(c => c.id !== id);
      if (!rest.length) { const fresh = makeNewConversation(); setActiveConvId(fresh.id); return [fresh]; }
      if (id === activeConvId) setActiveConvId(rest[0].id);
      return rest;
    });
  };

  const startListening = useCallback(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { setMicError('Non supporté.'); setTimeout(() => setMicError(''), 3000); return; }
    const r = new SR(); r.lang = 'fr-FR'; r.continuous = false; r.interimResults = true;
    r.onstart  = () => setIsListening(true);
    r.onresult = (e) => setInput(Array.from(e.results).map(x => x[0].transcript).join(''));
    r.onerror  = (e) => { setIsListening(false); setMicError('Erreur : '+e.error); setTimeout(() => setMicError(''),3000); };
    r.onend    = () => setIsListening(false);
    recognitionRef.current = r; r.start();
  }, []);

  const stopListening = useCallback(() => { recognitionRef.current?.stop(); setIsListening(false); }, []);
  const toggleMic = () => isListening ? stopListening() : startListening();

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files).map(f => ({ name: f.name, size: (f.size/1024).toFixed(1)+' KB', type: f.type.startsWith('image/') ? 'image' : 'file' }));
    setAttachedFiles(prev => [...prev, ...files]);
    e.target.value = '';
  };

  const sendMessage = async (text) => {
    const msg = text || input.trim();
    if (!msg && attachedFiles.length === 0) return;
    const userMsg = { id: Date.now(), role: 'user', content: msg, files: [...attachedFiles], time: new Date().toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'}) };
    addMessage(activeConvId, userMsg);
    setInput(''); setAttachedFiles([]); setIsTyping(true);
    const reply = await getBotResponse(msg || 'fichier', lastExchangeRef.current);
    lastExchangeRef.current = { user: msg, assistant: reply };
    addMessage(activeConvId, { id: Date.now()+1, role: 'bot', content: reply, time: new Date().toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'}) });
    setIsTyping(false);
  };

  const cycleExpand = () => setExpandState(s => s==='normal'?'wide':s==='wide'?'fullscreen':'normal');
  const filteredConvs = conversations.filter(c =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase()) || c.preview.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const containerStyle =
    expandState === 'fullscreen' ? { width: '96vw', height: '94vh' } :
    expandState === 'wide'       ? { width: '1020px', height: '680px' } :
                                   { width: '860px', height: '660px' };

  const C = darkMode ? {
    bg: '#0c0d12', surface: '#111318', border: 'rgba(255,255,255,0.07)', sidebar: '#0e0f15',
    textPrimary: '#eeeef5', textSecondary: 'rgba(238,238,245,0.6)', textMuted: 'rgba(238,238,245,0.38)',
    accent: '#6366f1', accentGlow: 'rgba(99,102,241,0.28)', accentSubtle: 'rgba(99,102,241,0.1)', accentText: '#818cf8',
    botBubble: '#14151c', botBorder: 'rgba(255,255,255,0.07)',
    userBubble: 'linear-gradient(135deg,#4f46e5,#6366f1)',
    inputBg: '#0e0f15', inputBorder: 'rgba(255,255,255,0.09)', inputFocus: '#6366f1',
    online: '#34d399', online2: 'rgba(52,211,153,0.2)',
    cardBg: 'rgba(255,255,255,0.03)', cardHover: 'rgba(255,255,255,0.055)',
    tagBg: 'rgba(255,255,255,0.08)',
    shadow: '0 0 0 1px rgba(255,255,255,0.04),0 24px 80px rgba(0,0,0,0.85)',
    timeColor: 'rgba(238,238,245,0.25)',
  } : {
    bg: '#f7f6f3', surface: '#ffffff', border: 'rgba(0,0,0,0.08)', sidebar: '#f0ede7',
    textPrimary: '#111118', textSecondary: 'rgba(17,17,24,0.65)', textMuted: 'rgba(17,17,24,0.42)',
    accent: '#4f46e5', accentGlow: 'rgba(79,70,229,0.2)', accentSubtle: 'rgba(79,70,229,0.08)', accentText: '#4338ca',
    botBubble: '#ffffff', botBorder: 'rgba(0,0,0,0.08)',
    userBubble: 'linear-gradient(135deg,#4f46e5,#6366f1)',
    inputBg: '#efece7', inputBorder: 'rgba(0,0,0,0.14)', inputFocus: '#4f46e5',
    online: '#059669', online2: 'rgba(5,150,105,0.1)',
    cardBg: '#fafaf8', cardHover: '#f3f1ee',
    tagBg: 'rgba(0,0,0,0.06)',
    shadow: '0 0 0 1px rgba(0,0,0,0.07),0 24px 80px rgba(0,0,0,0.15)',
    timeColor: 'rgba(17,17,24,0.35)',
  };

  const rc = getRoleConfig(currentUser.role);
  const displayName = currentUser.name.length > 20 ? currentUser.name.slice(0,20)+'…' : currentUser.name;

  return (
    <div style={{ position:'fixed',inset:0,zIndex:1000, backgroundColor:'rgba(0,0,0,0.65)',backdropFilter:'blur(12px)', display:'flex',alignItems:'center',justifyContent:'center', fontFamily:"'Instrument Sans',system-ui,sans-serif" }}>
      <style>{`
        @keyframes slideUp{from{opacity:0;transform:translateY(24px) scale(0.96)}to{opacity:1;transform:none}}
        @keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
        @keyframes typingPulse{0%,60%,100%{transform:translateY(0);opacity:.35}30%{transform:translateY(-5px);opacity:1}}
        @keyframes onlinePulse{0%,100%{opacity:1}50%{opacity:.5}}
        @keyframes micPulse{0%,100%{box-shadow:0 0 0 0 rgba(99,102,241,.5)}50%{box-shadow:0 0 0 8px rgba(99,102,241,0)}}
        .erp-scroll::-webkit-scrollbar{width:3px}
        .erp-scroll::-webkit-scrollbar-track{background:transparent}
        .erp-scroll::-webkit-scrollbar-thumb{background:${darkMode?'rgba(255,255,255,0.1)':'rgba(0,0,0,0.12)'};border-radius:2px}
        .conv-item{transition:background .13s;cursor:pointer;border-radius:10px}
        .conv-item:hover{background:${C.accentSubtle}!important}
        .conv-item:hover .del-btn{opacity:1!important}
        .del-btn{opacity:0;transition:opacity .13s;background:none;border:none;cursor:pointer;padding:3px;border-radius:5px;display:flex;align-items:center;color:${C.textMuted}}
        .del-btn:hover{color:#f87171!important;background:rgba(239,68,68,0.1)!important}
        .pill{transition:all .18s;cursor:pointer}
        .pill { cursor: default !important; }  /* supprimer le hover actif */
        .icon-btn{transition:all .15s;cursor:pointer;background:none;border:none;border-radius:9px;padding:9px;display:flex;align-items:center}
        .icon-btn:hover{background:${C.accentSubtle}!important;color:${C.accentText}!important}
        .send-btn{transition:all .2s cubic-bezier(.34,1.56,.64,1)}
        .send-btn:hover:not(:disabled){transform:scale(1.07)}
        .send-btn:active:not(:disabled){transform:scale(0.95)}
        .close-btn:hover{background:rgba(239,68,68,0.15)!important;color:#f87171!important}
        .new-conv-btn{transition:all .18s}
        .new-conv-btn:hover{opacity:.85!important;transform:translateY(-1px)!important}
        .msg-bubble{animation:fadeIn .22s cubic-bezier(.16,1,.3,1) both}
        .bot-bubble{max-width:min(90%,740px)}
      `}</style>

      <div style={{ ...containerStyle, display:'flex', borderRadius:20, overflow:'hidden', boxShadow:C.shadow, border:`1px solid ${C.border}`, animation:'slideUp .32s cubic-bezier(.16,1,.3,1)', transition:'width .35s cubic-bezier(.16,1,.3,1),height .35s cubic-bezier(.16,1,.3,1)', backgroundColor:C.bg }}>

        {/* ── SIDEBAR ── */}
        <div style={{ width:232, flexShrink:0, display:'flex', flexDirection:'column', backgroundColor:C.sidebar, borderRight:`1px solid ${C.border}`, position:'relative' }}>
          <div style={{ position:'absolute', inset:0, pointerEvents:'none', backgroundImage:`radial-gradient(circle at 1px 1px,${darkMode?'rgba(255,255,255,0.022)':'rgba(0,0,0,0.022)'} 1px,transparent 0)`, backgroundSize:'22px 22px' }} />
          <div style={{ position:'relative', zIndex:1, display:'flex', flexDirection:'column', height:'100%' }}>
            <div style={{ padding:'20px 18px 16px', borderBottom:`1px solid ${C.border}` }}>
              <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:16 }}>
                <div style={{ width:36, height:36, borderRadius:10, background:`linear-gradient(135deg,${C.accent},#818cf8)`, display:'flex', alignItems:'center', justifyContent:'center', boxShadow:`0 4px 14px ${C.accentGlow}`, flexShrink:0 }}>
                  <BarChart2 size={17} color="#fff" strokeWidth={2} />
                </div>
                <div>
                  <div style={{ fontFamily:"'Syne',sans-serif", fontSize:14, fontWeight:700, color:C.textPrimary, lineHeight:1 }}>ERP Assistant</div>
                  <div style={{ fontSize:10, color:C.textMuted, marginTop:3, letterSpacing:'0.06em', textTransform:'uppercase' }}>Intelligence IA</div>
                </div>
              </div>
              <button className="new-conv-btn" onClick={createNewConversation} style={{ display:'flex', alignItems:'center', justifyContent:'center', gap:7, width:'100%', background:`linear-gradient(135deg,${C.accent},#818cf8)`, color:'#fff', border:'none', borderRadius:10, padding:'9px 14px', fontFamily:"'Instrument Sans',sans-serif", fontSize:12.5, fontWeight:600, cursor:'pointer', boxShadow:`0 4px 16px ${C.accentGlow}` }}>
                <Plus size={13} strokeWidth={2.5} /> Nouvelle conversation
              </button>
              <div style={{ display:'flex', alignItems:'center', gap:8, marginTop:10, backgroundColor:C.inputBg, border:`1px solid ${C.inputBorder}`, borderRadius:9, padding:'8px 11px' }}>
                <Search size={13} color={C.textMuted} strokeWidth={2} />
                <input style={{ background:'none', border:'none', outline:'none', fontSize:13, color:C.textPrimary, width:'100%', fontFamily:"'Instrument Sans',sans-serif" }} placeholder="Rechercher..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)} />
              </div>
            </div>
            <div className="erp-scroll" style={{ flex:1, overflowY:'auto', padding:'12px 10px 8px' }}>
              <div style={{ fontSize:10, fontWeight:700, color:C.textMuted, textTransform:'uppercase', letterSpacing:'0.1em', padding:'0 8px 8px', fontFamily:"'Syne',sans-serif" }}>Historique ({filteredConvs.length})</div>
              {filteredConvs.map(conv => {
                const isActive = activeConvId === conv.id;
                return (
                  <div key={conv.id} className="conv-item" onClick={() => setActiveConvId(conv.id)} style={{ display:'flex', alignItems:'center', gap:8, padding:'9px 10px', marginBottom:2, backgroundColor: isActive ? C.accentSubtle : 'transparent', borderLeft:`2px solid ${isActive ? C.accent : 'transparent'}` }}>
                    <div style={{ flex:1, overflow:'hidden', minWidth:0 }}>
                      <div style={{ display:'flex', justifyContent:'space-between', gap:4, marginBottom:3 }}>
                        <span style={{ fontFamily:"'Instrument Sans',sans-serif", fontSize:13, fontWeight: isActive?600:500, color: isActive?C.accentText:C.textPrimary, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis', flex:1 }}>{conv.title}</span>
                        <span style={{ fontSize:10, color:C.textMuted, flexShrink:0, fontFamily:"'JetBrains Mono',monospace" }}>{conv.date}</span>
                      </div>
                      {conv.preview && <span style={{ fontSize:11.5, color:C.textMuted, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis', display:'block' }}>{conv.preview}</span>}
                    </div>
                    <button className="del-btn" onClick={(e) => deleteConversation(conv.id,e)} title="Supprimer"><Trash2 size={12}/></button>
                  </div>
                );
              })}
            </div>
            <div style={{ padding:'12px 14px', borderTop:`1px solid ${C.border}`, backgroundColor: darkMode?'rgba(0,0,0,0.2)':'rgba(0,0,0,0.03)' }}>
              <div style={{ display:'flex', alignItems:'center', gap:10 }}>
                <div style={{ width:36, height:36, borderRadius:'50%', flexShrink:0, backgroundColor:rc.bg, display:'flex', alignItems:'center', justifyContent:'center', fontSize:14, fontWeight:700, color:rc.color, border:`2px solid ${rc.color}`, boxShadow:`0 0 10px ${rc.bg}` }}>{currentUser.name[0]?.toUpperCase()||'U'}</div>
                <div style={{ flex:1, minWidth:0 }}>
                  <div style={{ fontFamily:"'Instrument Sans',sans-serif", fontSize:13, fontWeight:600, color:C.textPrimary, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{displayName}</div>
                  <div style={{ fontSize:11, fontWeight:500, color:rc.color, marginTop:2, display:'flex', alignItems:'center', gap:5 }}>
                    <span style={{ width:6, height:6, borderRadius:'50%', backgroundColor:rc.dot, display:'inline-block', animation:'onlinePulse 2.5s infinite' }} />
                    {rc.label}
                  </div>
                </div>
                <button className="icon-btn" style={{ color:C.textSecondary }}><Settings size={15} strokeWidth={1.8}/></button>
              </div>
            </div>
          </div>
        </div>

        {/* ── MAIN PANEL ── */}
        <div style={{ flex:1, display:'flex', flexDirection:'column', backgroundColor:C.bg, minWidth:0 }}>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 20px', height:62, flexShrink:0, backgroundColor:C.surface, borderBottom:`1px solid ${C.border}` }}>
            <div style={{ display:'flex', alignItems:'center', gap:14 }}>
              <div style={{ position:'relative' }}>
                <div style={{ width:42, height:42, borderRadius:13, background:`linear-gradient(135deg,${C.accent},#818cf8)`, display:'flex', alignItems:'center', justifyContent:'center', boxShadow:`0 4px 14px ${C.accentGlow}` }}><Bot size={20} color="#fff" strokeWidth={1.8}/></div>
                <div style={{ position:'absolute', bottom:-1, right:-1, width:11, height:11, borderRadius:'50%', backgroundColor:C.online, border:`2px solid ${C.surface}`, boxShadow:`0 0 8px ${C.online2}` }} />
              </div>
              <div>
                <div style={{ fontFamily:"'Syne',sans-serif", fontSize:16, fontWeight:700, color:C.textPrimary }}>Assistant IA ERP</div>
                <div style={{ fontSize:12, color:C.online, fontWeight:500, display:'flex', alignItems:'center', gap:5 }}>
                  <span style={{ display:'inline-block', width:6, height:6, borderRadius:'50%', backgroundColor:C.online, animation:'onlinePulse 2s infinite' }}/>
                  En ligne · Répond instantanément
                </div>
              </div>
            </div>
            <div style={{ display:'flex', alignItems:'center', gap:2 }}>
              {[
                { icon: darkMode?Sun:Moon, title: darkMode?'Mode clair':'Mode sombre', action: ()=>setDarkMode(d=>!d) },
                { icon: expandState==='fullscreen'?Minimize2:Maximize2, title:'Agrandir', action: cycleExpand },
              ].map(({icon:Icon,title,action},i) => (
                <button key={i} className="icon-btn" onClick={action} title={title} style={{ color: darkMode?'rgba(238,238,245,0.55)':'rgba(17,17,24,0.5)' }}><Icon size={18} strokeWidth={1.8}/></button>
              ))}
              <button className="icon-btn close-btn" onClick={onClose} title="Fermer" style={{ marginLeft:4, color: darkMode?'rgba(238,238,245,0.45)':'rgba(17,17,24,0.45)' }}><X size={18} strokeWidth={2}/></button>
            </div>
          </div>

          {micError && <div style={{ backgroundColor:darkMode?'rgba(239,68,68,0.1)':'#fef2f2', color:'#f87171', padding:'8px 20px', fontSize:12, borderBottom:'1px solid rgba(239,68,68,0.2)', fontFamily:"'JetBrains Mono',monospace" }}>⚠ {micError}</div>}

          <div className="erp-scroll" style={{ flex:1, overflowY:'auto', padding:'28px 24px 20px', display:'flex', flexDirection:'column', gap:16, backgroundColor:C.bg, backgroundImage: darkMode ? 'radial-gradient(ellipse 80% 50% at 50% -10%,rgba(99,102,241,0.07) 0%,transparent 60%)' : 'radial-gradient(ellipse 80% 50% at 50% -10%,rgba(99,102,241,0.035) 0%,transparent 60%)' }}>
            {messages.map(msg => (
              <div key={msg.id} className="msg-bubble" style={{ display:'flex', justifyContent: msg.role==='user'?'flex-end':'flex-start', alignItems:'flex-start', gap:10 }}>
                {msg.role === 'bot' && (
                  <div style={{ width:34, height:34, borderRadius:10, flexShrink:0, marginTop:2, background:`linear-gradient(135deg,${C.accent},#818cf8)`, display:'flex', alignItems:'center', justifyContent:'center', boxShadow:`0 2px 10px ${C.accentGlow}` }}><Bot size={16} color="#fff" strokeWidth={2}/></div>
                )}
                <div className={msg.role==='bot'?'bot-bubble':''} style={{
                  maxWidth: msg.role==='user'?'68%':undefined,
                  ...(msg.role==='user' ? { background:C.userBubble, color:'#fff', borderRadius:'18px 18px 4px 18px', boxShadow:`0 4px 20px ${C.accentGlow}`, padding:'13px 17px' }
                    : { backgroundColor:C.botBubble, color:C.textPrimary, borderRadius:'18px 18px 18px 4px', border:`1px solid ${C.botBorder}`, boxShadow: darkMode?'0 2px 14px rgba(0,0,0,0.35)':'0 2px 14px rgba(0,0,0,0.07)', padding:'14px 16px' }),
                }}>
                  {msg.files?.length > 0 && (
                    <div style={{ display:'flex', flexWrap:'wrap', gap:5, marginBottom:10 }}>
                      {msg.files.map((f,i) => (
                        <div key={i} style={{ display:'flex', alignItems:'center', gap:4, backgroundColor:'rgba(255,255,255,0.15)', borderRadius:6, padding:'3px 9px', border:'1px solid rgba(255,255,255,0.2)' }}>
                          {f.type==='image'?<ImageIcon size={11}/>:<FileText size={11}/>}
                          <span style={{ fontSize:11, fontFamily:"'JetBrains Mono',monospace" }}>{f.name}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {msg.role==='bot'
                    ? <MessageContent text={msg.content} darkMode={darkMode} C={C} />
                    : <div style={{ fontFamily:"'Instrument Sans',sans-serif", fontSize:14.5, lineHeight:1.65 }}>{msg.content}</div>
                  }
                  <div style={{ fontSize:11, marginTop:8, textAlign:'right', fontFamily:"'JetBrains Mono',monospace", color: msg.role==='user'?'rgba(255,255,255,0.4)':C.timeColor, display:'flex', alignItems:'center', justifyContent:'flex-end', gap:4 }}>
                    <Clock size={10} strokeWidth={2}/>{msg.time}
                  </div>
                </div>
                {msg.role==='user' && (
                  <div style={{ width:34, height:34, borderRadius:10, flexShrink:0, marginTop:2, backgroundColor:rc.bg, display:'flex', alignItems:'center', justifyContent:'center', fontSize:13, fontWeight:700, color:rc.color, border:`1.5px solid ${rc.color}44`, boxShadow:`0 2px 8px ${rc.bg}` }}>{currentUser.name[0]?.toUpperCase()||'U'}</div>
                )}
              </div>
            ))}
            {isTyping && (
              <div className="msg-bubble" style={{ display:'flex', alignItems:'flex-end', gap:10 }}>
                <div style={{ width:34, height:34, borderRadius:10, flexShrink:0, background:`linear-gradient(135deg,${C.accent},#818cf8)`, display:'flex', alignItems:'center', justifyContent:'center', boxShadow:`0 2px 10px ${C.accentGlow}` }}><Bot size={16} color="#fff" strokeWidth={2}/></div>
                <div style={{ backgroundColor:C.botBubble, border:`1px solid ${C.botBorder}`, borderRadius:'18px 18px 18px 4px', padding:'15px 20px', boxShadow: darkMode?'0 2px 12px rgba(0,0,0,0.3)':'0 2px 12px rgba(0,0,0,0.06)', display:'flex', alignItems:'center', gap:5 }}>
                  {[0,140,280].map(d => <span key={d} style={{ width:6, height:6, borderRadius:'50%', backgroundColor:C.accentText, display:'inline-block', animation:`typingPulse 1.4s ${d}ms infinite ease-in-out` }}/>)}
                </div>
              </div>
            )}
            <div ref={messagesEndRef}/>
          </div>

          <div style={{ padding:'10px 20px', backgroundColor:C.surface, borderTop:`1px solid ${C.border}` }}>
            <div style={{ display:'flex', alignItems:'center', gap:10, flexWrap:'wrap' }}>
              <span style={{ display:'flex', alignItems:'center', gap:5, fontFamily:"'Syne',sans-serif", fontSize:10.5, fontWeight:700, color:C.textMuted, textTransform:'uppercase', letterSpacing:'0.08em', whiteSpace:'nowrap' }}>
                <Sparkles size={11} color={C.accentText}/> Idées
              </span>
              <div style={{ display:'flex', gap:6, flexWrap:'wrap' }}>
                {SUGGESTIONS.map(s => (
                  <span key={s} className="pill" style={{
                    backgroundColor: C.accentSubtle,
                    color: C.accentText,
                    border: `1px solid ${C.accent}25`,
                    borderRadius: 20,
                    padding: '5px 13px',
                    fontFamily: "'Instrument Sans',sans-serif",
                    fontSize: 12.5,
                    fontWeight: 500,
                    cursor: 'default',        // ← plus de pointer
                    userSelect: 'none',       // ← pas sélectionnable
                    display: 'inline-block',
  }}>
    {s}
  </span>
))}
              </div>
            </div>
          </div>

          {attachedFiles.length > 0 && (
            <div style={{ padding:'8px 20px', display:'flex', flexWrap:'wrap', gap:6, backgroundColor:C.surface, borderTop:`1px solid ${C.border}` }}>
              {attachedFiles.map((f,i) => (
                <div key={i} style={{ display:'flex', alignItems:'center', gap:6, backgroundColor:C.accentSubtle, border:`1px solid ${C.accent}25`, borderRadius:8, padding:'4px 10px' }}>
                  {f.type==='image'?<ImageIcon size={12} color={C.accentText}/>:<FileText size={12} color={C.accentText}/>}
                  <span style={{ fontSize:12, color:C.textPrimary, fontFamily:"'JetBrains Mono',monospace" }}>{f.name}</span>
                  <span style={{ fontSize:10, color:C.textMuted }}>({f.size})</span>
                  <button onClick={() => setAttachedFiles(p => p.filter((_,j)=>j!==i))} style={{ background:'none', border:'none', cursor:'pointer', padding:0, display:'flex' }}><XCircle size={13} color={C.textMuted}/></button>
                </div>
              ))}
            </div>
          )}

          <div style={{ display:'flex', alignItems:'center', gap:8, padding:'14px 16px', backgroundColor:C.surface, borderTop:`1px solid ${C.border}` }}>
            <input ref={fileInputRef} type="file" multiple style={{ display:'none' }} onChange={handleFileChange} accept="image/*,.pdf,.doc,.docx,.xlsx,.txt"/>
            <button className="icon-btn" onClick={() => fileInputRef.current?.click()} style={{ color: attachedFiles.length>0?C.accentText:C.textMuted }}><Paperclip size={19} strokeWidth={1.8}/></button>
            <button className="icon-btn" onClick={toggleMic} style={{ background: isListening?C.accentSubtle:'none', color: isListening?C.accentText:C.textMuted, animation: isListening?'micPulse 1.5s infinite':'none' }}><Mic size={19} strokeWidth={1.8}/></button>
            <div style={{ flex:1, borderRadius:12, border:`1.5px solid ${inputFocused?C.inputFocus:C.inputBorder}`, backgroundColor:C.inputBg, boxShadow: inputFocused?`0 0 0 3px ${C.accentSubtle}`:'none', transition:'all .2s' }}>
              <input style={{ display:'block', width:'100%', padding:'12px 18px', fontFamily:"'Instrument Sans',sans-serif", fontSize:14.5, outline:'none', background:'none', border:'none', color:C.textPrimary, boxSizing:'border-box' }}
                placeholder={isListening?'🎙 Écoute en cours...':'Posez votre question...'}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key==='Enter' && !e.shiftKey && sendMessage()}
                onFocus={() => setInputFocused(true)}
                onBlur={() => setInputFocused(false)}
              />
            </div>
            <button className="send-btn" onClick={() => sendMessage()} disabled={!input.trim() && attachedFiles.length===0}
              style={{ width:46, height:46, borderRadius:12, border:'none', flexShrink:0, background:(input.trim()||attachedFiles.length>0)?`linear-gradient(135deg,${C.accent},#818cf8)`:(darkMode?'rgba(255,255,255,0.05)':'rgba(0,0,0,0.07)'), cursor:(input.trim()||attachedFiles.length>0)?'pointer':'default', display:'flex', alignItems:'center', justifyContent:'center', boxShadow:(input.trim()||attachedFiles.length>0)?`0 4px 14px ${C.accentGlow}`:'none' }}>
              <Send size={18} strokeWidth={2.2} color={(input.trim()||attachedFiles.length>0)?'#fff':(darkMode?'rgba(255,255,255,0.22)':'rgba(17,17,24,0.28)')}/>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIAssistant;