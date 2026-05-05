function UserAvatar({ username, onLogout }) {
  const [open, setOpen] = React.useState(false);
  return (
    <div className="avatar-wrap">
      <button className="avatar-btn"
              onClick={() => setOpen(o => !o)}
              onBlur={() => setTimeout(() => setOpen(false), 180)}>
        {username[0]?.toUpperCase()}
      </button>
      {open && (
        <div className="avatar-menu">
          <div className="username">{username}</div>
          <button onMouseDown={onLogout}>Çıkış yap</button>
        </div>
      )}
    </div>
  );
}

function QuestionPanel({ question, subjects, onSubjectChange, questions, onPickQuestion }) {
  const [typed, setTyped] = React.useState('');
  React.useEffect(() => {
    if (!question) { setTyped(''); return; }
    setTyped('');
    const text = question.question_text;
    let i = 0;
    const t = setInterval(() => {
      i++;
      setTyped(text.slice(0, i));
      if (i >= text.length) clearInterval(t);
    }, 18);
    return () => clearInterval(t);
  }, [question]);

  const isTyping = question && typed.length < question.question_text.length;

  return (
    <div className="panel-card area-question">
      <div className="panel-head">
        <span className="panel-title">Soru</span>
        <div className="selector-row" style={{ flex: 1, justifyContent: 'flex-end' }}>
          <select className="select" defaultValue=""
                  onChange={e => onSubjectChange(e.target.value)}>
            <option value="" disabled>Konu seçin</option>
            {subjects.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          {questions.length > 0 && (
            <select className="select" defaultValue=""
                    onChange={e => onPickQuestion(Number(e.target.value))}>
              <option value="" disabled>Soru seçin</option>
              {questions.map(q => <option key={q.id} value={q.id}>Soru {q.id}</option>)}
            </select>
          )}
        </div>
      </div>
      <div className="panel-body">
        {question
          ? <p className="q-text">
              {typed}
              {isTyping && <span className="caret" />}
            </p>
          : <p className="placeholder">Bir konu ve soru seçerek başlayalım.</p>}
      </div>
    </div>
  );
}

function VisualPanel({ question }) {
  return (
    <div className="panel-card area-visual">
      <div className="panel-head">
        <span className="panel-title">Görsel</span>
        <span className="panel-eyebrow">SVG</span>
      </div>
      <div className="panel-body" style={{ padding: 0 }}>
        <div className="visual-canvas">
          {question?.visual_path ? (
            <img src={`../../assets/${question.visual_path}`}
                 alt="Question visual"
                 style={{ maxWidth: '100%', maxHeight: '100%' }} />
          ) : (
            <p className="placeholder" style={{ padding: 24 }}>
              {question ? 'Bu soru için görsel yok.' : 'Bir soru seçildiğinde burada görselleştireceğiz.'}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function SolutionPanel({ question }) {
  const [revealed, setRevealed] = React.useState(0);
  React.useEffect(() => { setRevealed(0); }, [question]);

  const steps = question?.solution_steps ?? [];
  const allRevealed = revealed >= steps.length;

  return (
    <div className="panel-card area-solution">
      <div className="panel-head">
        <span className="panel-title">Çözüm</span>
        <span className="panel-eyebrow">{revealed} / {steps.length || '—'}</span>
      </div>
      <div className="panel-body">
        {steps.length === 0
          ? <p className="placeholder">Adımları görmek için bir soru seçin.</p>
          : <div className="step-list">
              {steps.slice(0, revealed).map((s, i) => (
                <div key={i} className={"step " + (i < revealed - 1 ? 'done' : '')}>
                  <span className="num">{i + 1}</span>
                  <span className="desc">{s.description}</span>
                  <span className="expr">{s.expression}</span>
                </div>
              ))}
            </div>}
      </div>
      <div className="panel-foot">
        <span style={{ fontSize: 12, color: 'var(--fg-3)' }}>
          {steps.length > 0
            ? (allRevealed ? 'Tüm adımlar gösterildi.' : 'Hazır olduğunda devam edin.')
            : ' '}
        </span>
        <button className="btn btn-primary"
                onClick={() => setRevealed(r => r + 1)}
                disabled={allRevealed || steps.length === 0}>
          {allRevealed ? 'Tamamlandı' : 'Sonraki Adım'}
        </button>
      </div>
    </div>
  );
}

window.UserAvatar = UserAvatar;
window.QuestionPanel = QuestionPanel;
window.VisualPanel = VisualPanel;
window.SolutionPanel = SolutionPanel;
