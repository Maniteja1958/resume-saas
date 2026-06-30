import { useEffect, useState } from 'react';
import { Plus, RefreshCw, X } from 'lucide-react';
import { rescore } from '../api.js';

export default function ResumeSkillEditor({ analysis, onRescored }) {
  const [skills, setSkills] = useState([]);
  const [newSkill, setNewSkill] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setSkills(analysis?.parsed_resume?.skills || []);
  }, [analysis?.analysis_id]);

  if (!analysis) return null;

  function addSkill() {
    const skill = newSkill.trim();
    if (!skill) return;
    if (!skills.some((s) => s.toLowerCase() === skill.toLowerCase())) {
      setSkills([...skills, skill]);
    }
    setNewSkill('');
  }

  async function handleRescore() {
    setLoading(true);
    try {
      const resumeData = { ...analysis.parsed_resume, skills };
      const result = await rescore({ analysisId: analysis.analysis_id, resumeData, jobDescription: analysis.job_description_text });
      onRescored?.({ ...analysis, parsed_resume: resumeData, ...result });
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card">
      <div className="section-head">
        <div>
          <p className="eyebrow">editable parser output</p>
          <h2>Resume Skill Editor</h2>
        </div>
        <button className="btn secondary" onClick={handleRescore} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} /> Re-score
        </button>
      </div>
      <div className="tag-cloud editable">
        {skills.map((skill) => (
          <button key={skill} className="tag tag-button" onClick={() => setSkills(skills.filter((s) => s !== skill))}>
            {skill} <X size={13} />
          </button>
        ))}
      </div>
      <div className="inline-form">
        <input value={newSkill} onChange={(e) => setNewSkill(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addSkill()} placeholder="Add skill, e.g. Kafka" />
        <button className="btn ghost" onClick={addSkill}><Plus size={16} /> Add</button>
      </div>
    </section>
  );
}
