import { useState } from 'react';

export default function RoleComparison({ roles = [] }) {
  const [selected, setSelected] = useState([]);
  if (roles.length < 2) return null;

  function toggle(role) {
    const name = role.role_name;
    setSelected((prev) => {
      if (prev.includes(name)) return prev.filter((r) => r !== name);
      if (prev.length >= 2) return [prev[1], name];
      return [...prev, name];
    });
  }

  const chosen = selected.map((name) => roles.find((r) => r.role_name === name)).filter(Boolean);

  return (
    <section className="card">
      <div className="section-head">
        <div>
          <p className="eyebrow">decision support</p>
          <h2>Side-by-side Role Comparison</h2>
        </div>
      </div>
      <div className="role-select-row">
        {roles.map((role) => (
          <button key={role.role_name} className={`role-pill ${selected.includes(role.role_name) ? 'active' : ''}`} onClick={() => toggle(role)}>
            {role.role_name}
          </button>
        ))}
      </div>
      {chosen.length === 2 && (
        <div className="comparison-grid">
          {chosen.map((role) => {
            const matched = new Set((role.matched_skills || []).map((s) => s.toLowerCase()));
            const missing = (role.required_skills || []).filter((s) => !matched.has(s.toLowerCase()));
            return (
              <div className="compare-column" key={role.role_name}>
                <h3>{role.role_name}</h3>
                <div className="big-score">{role.match_percentage}%</div>
                <p className="muted">Matched skills</p>
                <div className="tag-cloud small">{(role.matched_skills || []).map((s) => <span className="tag good" key={s}>{s}</span>)}</div>
                <p className="muted">Missing skills</p>
                <div className="tag-cloud small">{missing.map((s) => <span className="tag warn" key={s}>{s}</span>)}</div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
