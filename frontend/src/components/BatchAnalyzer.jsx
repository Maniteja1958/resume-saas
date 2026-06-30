import { useState } from 'react';
import { Layers3, Loader2 } from 'lucide-react';
import { analyzeBatch } from '../api.js';

export default function BatchAnalyzer() {
  const [file, setFile] = useState(null);
  const [jobsText, setJobsText] = useState(defaultJobs);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function runBatch() {
    setError(null);
    setLoading(true);
    try {
      const jobs = JSON.parse(jobsText);
      setResult(await analyzeBatch({ file, jobs }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card">
      <div className="section-head"><div><p className="eyebrow">one resume many companies</p><h2>Batch JD Analyzer</h2></div></div>
      <label className="file-mini">Resume<input type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files?.[0])} /><span>{file?.name || 'Choose file'}</span></label>
      <textarea className="json-area" value={jobsText} onChange={(e) => setJobsText(e.target.value)} />
      <button className="btn" onClick={runBatch} disabled={!file || loading}>{loading ? <Loader2 className="spin" size={16} /> : <Layers3 size={16} />} Rank JDs</button>
      {error && <div className="error-box">{error}</div>}
      {result && <div className="batch-results">{result.ranked_matches.map((match) => <article className="rank-card" key={`${match.rank}-${match.company}`}><span>#{match.rank}</span><h3>{match.company}</h3><p>{match.title}</p><strong>{match.fit_score}% fit</strong><div className="tag-cloud small">{match.top_missing_skills.map((s) => <span className="tag warn" key={s}>{s}</span>)}</div></article>)}</div>}
    </section>
  );
}

const defaultJobs = JSON.stringify([
  { "company": "Company A", "title": "Backend Engineer", "text": "We need Python, FastAPI, PostgreSQL, Docker, Kubernetes, REST API and CI/CD experience." },
  { "company": "Company B", "title": "Frontend Engineer", "text": "We need React, TypeScript, CSS, GraphQL and component architecture experience." },
  { "company": "Company C", "title": "DevOps Engineer", "text": "We need AWS, Docker, Kubernetes, Terraform, CI/CD pipelines and Linux." }
], null, 2);
