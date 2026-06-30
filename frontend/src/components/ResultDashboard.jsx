import { Download, ExternalLink, Target, Zap } from 'lucide-react';
import { API_BASE } from '../api.js';
import RadarChart from './RadarChart.jsx';
import ResumeSkillEditor from './ResumeSkillEditor.jsx';
import RoleComparison from './RoleComparison.jsx';

export default function ResultDashboard({ analysis, onAnalysisUpdate }) {
  if (!analysis) return null;

  const roles = analysis.predicted_roles?.predictions || [];
  const gaps = analysis.skill_gaps || {};
  const certs = analysis.certifications?.recommendations || [];
  const ats = analysis.ats_report || {};
  const scores = analysis.scores || {};

  return (
    <div className="results-stack">
      <section className="score-grid">
        <MetricCard label="ATS Score" value={`${scores.ats_score ?? ats.ats_score ?? 0}/100`} icon={<Zap />} accent="purple" />
        <MetricCard label="Top Role" value={scores.top_role || roles[0]?.role_name || 'N/A'} icon={<Target />} accent="green" />
        <MetricCard label="Role Match" value={`${scores.top_role_match || roles[0]?.match_percentage || 0}%`} icon={<Target />} accent="blue" />
        <MetricCard label="Skill Gaps" value={scores.gap_count ?? gaps.missing_skills?.length ?? 0} icon={<Zap />} accent="orange" />
      </section>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="eyebrow">downloadable deliverable</p>
            <h2>Executive Report</h2>
          </div>
          <a className="btn" href={`${API_BASE}/report/${analysis.analysis_id}`} target="_blank" rel="noreferrer">
            <Download size={16} /> Export PDF Report
          </a>
        </div>
        <p className="muted">Analysis ID: {analysis.analysis_id}</p>
      </section>

      <section className="grid-2">
        <div className="card">
          <div className="section-head"><div><p className="eyebrow">semantic ats</p><h2>ATS Match Evidence</h2></div></div>
          <div className="tag-cloud">
            {(ats.matched_keywords || []).map((k) => <span className="tag good" key={k}>{k}</span>)}
            {(ats.missing_keywords || []).map((k) => <span className="tag warn" key={k}>{k}</span>)}
          </div>
          <ul className="clean-list">
            {(ats.suggestions || []).map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
        <div className="card">
          <div className="section-head"><div><p className="eyebrow">skill vector</p><h2>Radar Fit Chart</h2></div></div>
          <RadarChart skillVector={ats.skill_vector || []} />
        </div>
      </section>

      <section className="card">
        <div className="section-head"><div><p className="eyebrow">agent prediction</p><h2>Predicted Roles</h2></div></div>
        <div className="role-grid">
          {roles.map((role) => (
            <article className="role-card" key={role.role_name}>
              <div className="role-score">{role.match_percentage}%</div>
              <h3>{role.role_name}</h3>
              <p className="muted">Matched</p>
              <div className="tag-cloud small">{(role.matched_skills || []).map((s) => <span className="tag good" key={s}>{s}</span>)}</div>
            </article>
          ))}
        </div>
      </section>

      <RoleComparison roles={roles} />

      <section className="grid-2">
        <div className="card">
          <div className="section-head"><div><p className="eyebrow">gap analyzer</p><h2>Skill Gaps</h2></div></div>
          <p className="muted">Target role: {gaps.target_role}</p>
          <h4>Missing</h4>
          <div className="tag-cloud">{(gaps.missing_skills || []).map((s) => <span className="tag warn" key={s}>{s}</span>)}</div>
          <h4>Strong</h4>
          <div className="tag-cloud">{(gaps.strong_skills || []).map((s) => <span className="tag good" key={s}>{s}</span>)}</div>
          <pre className="plan">{gaps.improvement_plan}</pre>
        </div>
        <div className="card">
          <div className="section-head"><div><p className="eyebrow">certificate hunter</p><h2>Certifications</h2></div></div>
          <div className="cert-list">
            {certs.length === 0 && <p className="muted">No certifications needed because no major gaps were found.</p>}
            {certs.map((cert, i) => (
              <a className="cert-card" href={cert.url} key={`${cert.skill}-${i}`} target="_blank" rel="noreferrer">
                <strong>{cert.title}</strong>
                <span>{cert.skill} · {cert.platform} · {cert.duration_estimate}</span>
                <ExternalLink size={14} />
              </a>
            ))}
          </div>
        </div>
      </section>

      <ResumeSkillEditor analysis={analysis} onRescored={(updated) => onAnalysisUpdate?.({ ...analysis, ...updated })} />
    </div>
  );
}

function MetricCard({ label, value, icon, accent }) {
  return (
    <article className={`metric-card ${accent}`}>
      <span>{icon}</span>
      <p>{label}</p>
      <strong>{value}</strong>
    </article>
  );
}
