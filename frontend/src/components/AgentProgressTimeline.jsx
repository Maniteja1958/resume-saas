import { CheckCircle2, CircleDot, Loader2, XCircle } from 'lucide-react';

export default function AgentProgressTimeline({ events, progress, error }) {
  return (
    <section className="card progress-card">
      <div className="section-head">
        <div>
          <p className="eyebrow">LangGraph-style agent trace</p>
          <h2>Live Analysis Progress</h2>
        </div>
        <span className="progress-number">{Math.round(progress || 0)}%</span>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${progress || 0}%` }} />
      </div>
      {error && <div className="error-box">{error}</div>}
      <div className="timeline">
        {events.length === 0 && (
          <div className="timeline-item muted">
            <Loader2 className="spin" size={18} /> Waiting for agent events...
          </div>
        )}
        {events.map((event, index) => {
          const icon = event.type === 'error' ? <XCircle size={18} /> : event.type === 'done' || event.type?.includes('completed') ? <CheckCircle2 size={18} /> : event.type === 'heartbeat' ? <CircleDot size={18} /> : <Loader2 className="spin" size={18} />;
          return (
            <div className={`timeline-item ${event.type}`} key={`${event.type}-${index}`}>
              <span className="timeline-icon">{icon}</span>
              <div>
                <strong>{event.message}</strong>
                {event.payload?.agent && <small>{event.payload.agent}</small>}
                {event.payload?.reason && <small>{event.payload.reason}</small>}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
