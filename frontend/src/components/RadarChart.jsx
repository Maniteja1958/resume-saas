export default function RadarChart({ skillVector = [] }) {
  if (!skillVector.length) {
    return <div className="empty-state">No semantic skill vector available yet.</div>;
  }

  const size = 280;
  const center = size / 2;
  const radius = 100;
  const points = skillVector.slice(0, 8);
  const axes = points.map((_, i) => {
    const angle = -Math.PI / 2 + (i * 2 * Math.PI) / points.length;
    return { x: center + Math.cos(angle) * radius, y: center + Math.sin(angle) * radius, angle };
  });

  const polygon = (key) =>
    points
      .map((item, i) => {
        const value = Math.max(0, Math.min(1, item[key] || 0));
        const angle = axes[i].angle;
        return `${center + Math.cos(angle) * radius * value},${center + Math.sin(angle) * radius * value}`;
      })
      .join(' ');

  return (
    <div className="radar-wrap">
      <svg viewBox={`0 0 ${size} ${size}`} className="radar-svg">
        {[0.25, 0.5, 0.75, 1].map((level) => (
          <polygon
            key={level}
            points={axes.map((a) => `${center + Math.cos(a.angle) * radius * level},${center + Math.sin(a.angle) * radius * level}`).join(' ')}
            fill="none"
            stroke="rgba(255,255,255,.11)"
          />
        ))}
        {axes.map((a, i) => (
          <g key={i}>
            <line x1={center} y1={center} x2={a.x} y2={a.y} stroke="rgba(255,255,255,.12)" />
            <text x={center + Math.cos(a.angle) * (radius + 24)} y={center + Math.sin(a.angle) * (radius + 24)} textAnchor="middle" dominantBaseline="middle">
              {points[i].skill.slice(0, 12)}
            </text>
          </g>
        ))}
        <polygon points={polygon('jd_importance')} fill="rgba(78,222,163,.16)" stroke="#4edea3" strokeWidth="2" />
        <polygon points={polygon('resume_strength')} fill="rgba(192,193,255,.22)" stroke="#c0c1ff" strokeWidth="2" />
      </svg>
      <div className="legend"><span className="dot green" /> JD requirement <span className="dot purple" /> Resume strength</div>
    </div>
  );
}
