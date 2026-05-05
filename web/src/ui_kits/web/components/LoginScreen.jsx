function LoginScreen({ onLogin }) {
  const [username, setUsername] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [error, setError]     = React.useState('');

  function submit(e) {
    e.preventDefault();
    if (!username || !password) {
      setError('Lütfen kullanıcı adı ve parola girin.');
      return;
    }
    // matches POC/web/src/components/LoginPage.tsx hardcoded creds
    if (username === 'alpbek' && password === '1234') {
      onLogin(username);
    } else {
      setError('Geçersiz kullanıcı adı veya parola.');
    }
  }

  return (
    <div className="login-bg">
      <form className="login-card" onSubmit={submit}>
        <div className="login-brand">
          <img src="../../assets/favicon.svg" alt="" />
          <div className="word">Matemant<span className="accent">ı</span>k</div>
        </div>
        <p className="login-tagline">Adım adım birlikte çözelim.</p>

        <div>
          <div className="field-label">Kullanıcı adı</div>
          <input className="input" value={username}
                 onChange={e => setUsername(e.target.value)}
                 placeholder="alpbek" autoFocus />
        </div>
        <div>
          <div className="field-label">Parola</div>
          <input className="input" type="password" value={password}
                 onChange={e => setPassword(e.target.value)}
                 placeholder="••••" />
        </div>

        {error && <p className="error-text">{error}</p>}

        <button type="submit" className="btn btn-primary btn-lg" style={{ marginTop: 4 }}>
          Giriş yap
        </button>
        <p style={{ fontSize: 12, color: 'var(--fg-3)', textAlign: 'center', margin: 0 }}>
          İpucu: <code style={{ fontFamily: 'var(--font-mono)' }}>alpbek</code> / <code style={{ fontFamily: 'var(--font-mono)' }}>1234</code>
        </p>
      </form>
    </div>
  );
}

window.LoginScreen = LoginScreen;
