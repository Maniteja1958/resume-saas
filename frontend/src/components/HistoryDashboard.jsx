import { useEffect, useState } from 'react';
import { Download, RefreshCw } from 'lucide-react';
import { API_BASE, getAnalysis, getHistory } from '../api.js';

export default function HistoryDashboard({ onOpenAnalysis }) {
  const [history, setHistory] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      setHistory(await getHistory());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function open(id) {
    const analysis = await getAnalysis(id);
    onOpenAnalysis?.(analysis);
  }

  return (
    <section className="card">
      <div className="section-head">
        <div>
          <p className="eyebrow">mongodb history</p>
          <h2>History Dashboard</h2>
        </div>
        <button className="btn secondary" onClick={load}><RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh</button>
      </div>
      <ScoreSparkline items={history.items} />
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Date</th><th>File</th><th>Top Role</th><th>ATS</th><th>Gaps</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {history.items.map((item) => (
              <tr key={item.analysis_id}>
                <td>{new Date(item.created_at).toLocaleString()}</td>
                <td>{item.filename}</td>
                <td>{item.top_role}</td>
                <td><strong>{item.ats_score}</strong></td>
                <td>{item.gap_count}</td>
                <td className="actions">
                  <button className="link-button" onClick={() => open(item.analysis_id)}>View</button>
                  <a className="link-button" href={`${API_BASE}/report/${item.analysis_id}`} target="_blank" rel="noreferrer"><Download size={14} /> PDF</a>
                </td>
              </tr>
            ))}
            {history.items.length === 0 && <tr><td colSpan="6" className="muted">No history yet. Run an analysis first.</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ScoreSparkline({ items }) {
  const data = [...items].reverse().slice(-12);
  if (data.length < 2) return <div className="empty-state">Run at least two analyses to see a score trend.</div>;
  const w = 520;
  const h = 120;
  const max = 100;
  const points = data.map((item, i) => {
    const x = (i / Math.max(data.length - 1, 1)) * (w - 24) + 12;
    const y = h - 20 - ((item.ats_score || 0) / max) * (h - 36);
    return `${x},${y}`;
  });
  return (
    <div className="spark-wrap">
      <svg viewBox={`0 0 ${w} ${h}`}>
        <polyline points={points.join(' ')} fill="none" stroke="#c0c1ff" strokeWidth="3" />
        {points.map((p, i) => {
          const [x, y] = p.split(',');
          return <circle key={i} cx={x} cy={y} r="4" fill="#4edea3" />;
        })}
      </svg>
      <p className="muted">ATS score trend across resume versions</p>
    </div>
  );
}
