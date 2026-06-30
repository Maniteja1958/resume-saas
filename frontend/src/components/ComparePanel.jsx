import { useState } from 'react';
import { GitCompare, Loader2 } from 'lucide-react';
import { compareResumes } from '../api.js';

export default function ComparePanel() {
  const [fileA, setFileA] = useState(null);
  const [fileB, setFileB] = useState(null);
  const [jobDescription, setJobDescription] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function runCompare() {
    setError(null);
    setLoading(true);
    try {
      setResult(await compareResumes({ fileA, fileB, jobDescription }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card">
      <div className="section-head">
        <div><p className="eyebrow">resume v1 vs v2</p><h2>Comparison Dashboard</h2></div>
      </div>
      <div className="grid-2">
        <label className="file-mini">Resume A<input type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFileA(e.target.files?.[0])} /><span>{fileA?.name || 'Choose file'}</span></label>
        <label className="file-mini">Resume B<input type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFileB(e.target.files?.[0])} /><span>{fileB?.name || 'Choose file'}</span></label>
      </div>
      <textarea value={jobDescription} onChange={(e) => setJobDescription(e.target.value)} placeholder="Optional target job description for fair comparison" />
      <button className="btn" onClick={runCompare} disabled={!fileA || !fileB || loading}>
        {loading ? <Loader2 className="spin" size={16} /> : <GitCompare size={16} />} Compare Resumes
      </button>
      {error && <div className="error-box">{error}</div>}
      {result && <DiffView result={result} />}
    </section>
  );
}

function DiffView({ result }) {
  const diff = result.diff;
  return (
    <div className="diff-view">
      <div className="score-delta">
        <span>ATS Delta</span>
        <strong className={diff.ats_score_delta >= 0 ? 'positive' : 'negative'}>{diff.ats_score_delta >= 0 ? '+' : ''}{diff.ats_score_delta}</strong>
      </div>
      <div className="grid-2">
        <DiffList title="Skills Added" items={diff.skills_added} good />
        <DiffList title="Skills Removed" items={diff.skills_removed} />
        <DiffList title="Missing Keywords Resolved" items={diff.missing_keywords_resolved} good />
        <DiffList title="New Missing Keywords" items={diff.new_missing_keywords} />
      </div>
      <h3>Role Match Improvement</h3>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Role</th><th>Before</th><th>After</th><th>Delta</th></tr></thead>
          <tbody>{diff.role_match_delta.map((r) => <tr key={r.role_name}><td>{r.role_name}</td><td>{r.before}%</td><td>{r.after}%</td><td>{r.delta >= 0 ? '+' : ''}{r.delta}</td></tr>)}</tbody>
        </table>
      </div>
    </div>
  );
}

function DiffList({ title, items, good }) {
  return <div><h4>{title}</h4><div className="tag-cloud">{items.length ? items.map((i) => <span className={`tag ${good ? 'good' : 'warn'}`} key={i}>{i}</span>) : <span className="muted">None</span>}</div></div>;
}
