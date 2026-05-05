function AppShell({ username, onLogout }) {
  const [subject, setSubject] = React.useState(null);
  const [question, setQuestion] = React.useState(null);

  const subjects  = window.MOCK_SUBJECTS;
  const allQs     = window.MOCK_QUESTIONS;
  const questions = subject ? allQs.filter(q => q.subject_name === subject) : [];

  function handleSubject(s) {
    setSubject(s);
    setQuestion(null);
  }
  function handlePick(id) {
    const q = questions.find(q => q.id === id) ?? null;
    setQuestion(q);
  }

  return (
    <div className="app-shell">
      <window.UserAvatar username={username} onLogout={onLogout} />
      <window.QuestionPanel
        question={question}
        subjects={subjects}
        onSubjectChange={handleSubject}
        questions={questions}
        onPickQuestion={handlePick}
      />
      <window.VisualPanel question={question} />
      <window.SolutionPanel question={question} />
    </div>
  );
}

function App() {
  const [user, setUser] = React.useState(null);
  if (!user) return <window.LoginScreen onLogin={setUser} />;
  return <AppShell username={user} onLogout={() => setUser(null)} />;
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
