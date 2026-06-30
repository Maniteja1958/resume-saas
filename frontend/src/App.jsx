import { useRef, useState } from 'react';
import { BrainCircuit, FileText, Globe2, History, Layers3, Loader2, UploadCloud } from 'lucide-react';
import { API_BASE, createAnalysis, fetchJobDescription, getAnalysis } from './api.js';
import AgentProgressTimeline from './components/AgentProgressTimeline.jsx';
import ResultDashboard from './components/ResultDashboard.jsx';
import HistoryDashboard from './components/HistoryDashboard.jsx';
import ComparePanel from './components/ComparePanel.jsx';
import BatchAnalyzer from './components/BatchAnalyzer.jsx';

export default function App() {
  const [activeTab, setActiveTab] = useState('analyze');
  const [file, setFile] = useState(null);
  const [jobDescription, setJobDescription] = useState('');
  const [jobUrl, setJobUrl] = useState('');
  const [analysisId, setAnalysisId] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [events, setEvents] = useState([]);
  const [progress, setProgress] = useState(0);
  const [loading, setLoading] = useState(false);
  const [fetchingUrl, setFetchingUrl] = useState(false);
  const [error, setError] = useState(null);

  const eventSourceRef = useRef(null);
  const streamFinishedRef = useRef(false);
  const pollingTimerRef = useRef(null);

  async function handleFetchUrl() {
    if (!jobUrl.trim()) return;
    setFetchingUrl(true);
    setError(null);
    try {
      const result = await fetchJobDescription(jobUrl.trim());
      setJobDescription(result.text);
    } catch (err) {
      setError(formatJobFetchError(err.message));
    } finally {
      setFetchingUrl(false);
    }
  }

  async function handleAnalyze() {
    if (!file) return;

    setLoading(true);
    setError(null);
    setAnalysis(null);
    setEvents([]);
    setProgress(0);
    streamFinishedRef.current = false;
    eventSourceRef.current?.close();
    if (pollingTimerRef.current) clearInterval(pollingTimerRef.current);

    try {
      const created = await createAnalysis({ file, jobDescription, targetMissingCount: 3 });
      setAnalysisId(created.analysis_id);
      startEventStream(created.analysis_id);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  function startEventStream(id) {
    const source = new EventSource(`${API_BASE}/analyses/${id}/events`);
    eventSourceRef.current = source;

    source.onopen = () => {
      setError(null);
    };

    source.addEventListener('agent_update', (event) => {
      const data = JSON.parse(event.data);
      if (data.type !== 'heartbeat') {
        setEvents((prev) => appendUniqueEvent(prev, data));
      }
      if (typeof data.progress === 'number') setProgress((prev) => Math.max(prev, data.progress));
    });

    source.addEventListener('done', async (event) => {
      const data = JSON.parse(event.data);
      streamFinishedRef.current = true;
      setEvents((prev) => appendUniqueEvent(prev, data));
      setProgress(100);
      source.close();
      await loadFinalAnalysis(id);
    });

    source.addEventListener('agent_error', (event) => {
      let message = 'Analysis failed';
      try {
        const data = JSON.parse(event.data);
        message = data.message || message;
        setEvents((prev) => appendUniqueEvent(prev, data));
      } catch (_) {}
      streamFinishedRef.current = true;
      source.close();
      setError(message);
      setLoading(false);
    });

    source.onerror = () => {
      // Browsers may fire onerror when a stream is closed or interrupted.
      // Do not show a false failure after we already received the done event.
      if (streamFinishedRef.current) return;

      source.close();
      setError('Live progress stream disconnected, so the UI is polling the backend for the final result...');
      startPollingForResult(id);
    };
  }

  async function loadFinalAnalysis(id) {
    try {
      const final = await getAnalysis(id);
      setAnalysis(final);
      if (final.agent_trace?.length) setEvents(final.agent_trace);
      setProgress(100);
      setError(null);
    } catch (err) {
      setError(`Analysis completed, but fetching the result failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function startPollingForResult(id) {
    if (pollingTimerRef.current) clearInterval(pollingTimerRef.current);
    let attempts = 0;

    pollingTimerRef.current = setInterval(async () => {
      attempts += 1;
      try {
        const doc = await getAnalysis(id);
        if (doc.agent_trace?.length) {
          setEvents(doc.agent_trace);
          const lastProgress = [...doc.agent_trace].reverse().find((e) => typeof e.progress === 'number')?.progress;
          if (typeof lastProgress === 'number') setProgress((prev) => Math.max(prev, lastProgress));
        }

        if (doc.status === 'completed') {
          streamFinishedRef.current = true;
          clearInterval(pollingTimerRef.current);
          setAnalysis(doc);
          setProgress(100);
          setError(null);
          setLoading(false);
        }

        if (doc.status === 'failed') {
          streamFinishedRef.current = true;
          clearInterval(pollingTimerRef.current);
          setError(doc.errors?.[0]?.message || 'Analysis failed on the backend.');
          setLoading(false);
        }
      } catch (_) {
        // Keep polling for a short time. The analysis may not be persisted yet.
      }

      if (attempts >= 75) {
        clearInterval(pollingTimerRef.current);
        setError('Analysis is taking longer than expected. Open History or check the backend terminal logs.');
        setLoading(false);
      }
    }, 1000);
  }

  function openAnalysisFromHistory(item) {
    setAnalysis(item);
    setAnalysisId(item.analysis_id);
    setActiveTab('analyze');
    setEvents(item.agent_trace || []);
    setProgress(100);
    setError(null);
  }

  return (
    <main className="app-shell">
      <div className="bg-grid" />
      <header className="hero">
        <div className="brand"><BrainCircuit size={34} /><span>AuraAnalyze</span></div>
        <p className="eyebrow">agentic resume intelligence SaaS</p>
        <h1>Complete resume analysis website with separate frontend and backend.</h1>
        <p className="hero-copy">Upload a resume, stream autonomous agent progress, score semantic ATS fit, track history, compare versions, and export PDF reports.</p>
      </header>

      <nav className="tabs">
        <button className={activeTab === 'analyze' ? 'active' : ''} onClick={() => setActiveTab('analyze')}><UploadCloud size={16} /> Analyze</button>
        <button className={activeTab === 'history' ? 'active' : ''} onClick={() => setActiveTab('history')}><History size={16} /> History</button>
        <button className={activeTab === 'compare' ? 'active' : ''} onClick={() => setActiveTab('compare')}><FileText size={16} /> Compare</button>
        <button className={activeTab === 'batch' ? 'active' : ''} onClick={() => setActiveTab('batch')}><Layers3 size={16} /> Batch</button>
      </nav>

      {activeTab === 'analyze' && (
        <div className="main-grid">
          <section className="card upload-card">
            <div className="section-head"><div><p className="eyebrow">input</p><h2>Upload Resume</h2></div></div>
            <label className="dropzone">
              <input type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files?.[0] || null)} />
              <UploadCloud size={44} />
              <strong>{file ? file.name : 'Drop or choose resume file'}</strong>
              <span>PDF, DOCX, or TXT</span>
            </label>

            <div className="url-row">
              <input value={jobUrl} onChange={(e) => setJobUrl(e.target.value)} placeholder="Paste job posting URL" />
              <button className="btn ghost" onClick={handleFetchUrl} disabled={fetchingUrl}>{fetchingUrl ? <Loader2 className="spin" size={16} /> : <Globe2 size={16} />} Fetch JD</button>
            </div>
            <textarea value={jobDescription} onChange={(e) => setJobDescription(e.target.value)} placeholder="Paste job description here, or fetch from URL above..." />
            <button className="btn wide" onClick={handleAnalyze} disabled={!file || loading}>{loading ? <Loader2 className="spin" size={18} /> : <BrainCircuit size={18} />} Run Agentic Analysis</button>
            {error && <div className="error-box">{error}</div>}
          </section>

          <AgentProgressTimeline events={events} progress={progress} error={null} />
        </div>
      )}

      {activeTab === 'analyze' && analysis && <ResultDashboard analysis={analysis} onAnalysisUpdate={setAnalysis} />}
      {activeTab === 'history' && <HistoryDashboard onOpenAnalysis={openAnalysisFromHistory} />}
      {activeTab === 'compare' && <ComparePanel />}
      {activeTab === 'batch' && <BatchAnalyzer />}

      <footer className="footer">Backend: FastAPI · Frontend: React/Vite · Streaming: SSE · Storage: MongoDB-ready</footer>
    </main>
  );
}

function appendUniqueEvent(events, event) {
  const key = `${event.type}-${event.message}-${event.progress}-${event.ts || event.created_at || ''}`;
  const exists = events.some((item) => `${item.type}-${item.message}-${item.progress}-${item.ts || item.created_at || ''}` === key);
  return exists ? events : [...events, event];
}

function formatJobFetchError(message = '') {
  if (message.includes('403') || message.toLowerCase().includes('forbidden')) {
    return 'This job board blocked automatic job-description fetching with 403 Forbidden. This is normal for sites like Wellfound, LinkedIn, and Indeed. Please copy the job description from the page, paste it into the text box, and run analysis.';
  }
  return `${message} You can still paste the job description manually and run analysis.`;
}
