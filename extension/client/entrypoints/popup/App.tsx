import { useState } from 'react';
import independentLogo from '@/assets/independent.png';
import './App.css';

const SITE_URL = 'https://nonpartisan.ink';

function App() {
  const [isLoading, setIsLoading] = useState(false);

  const handleViewAllPerspectives = async () => {
    setIsLoading(true);
    try {
      // Grab the current tab so we can pass what the user is about to read.
      const tabs = await browser.tabs.query({
        active: true,
        currentWindow: true,
      });
      const currentUrl = tabs[0]?.url;
      const target =
        currentUrl && /^https?:\/\//.test(currentUrl)
          ? `${SITE_URL}/?url=${encodeURIComponent(currentUrl)}`
          : SITE_URL;
      await browser.tabs.create({ url: target });
    } catch {
      // Fallback if tabs permission / API is unavailable.
      window.open(SITE_URL, '_blank', 'noopener,noreferrer');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="np-popup">
      <header className="np-header">
        <a
          href={SITE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="np-brand"
          aria-label="Open Nonpartisan website"
        >
          <img
            src={independentLogo}
            className="np-logo"
            alt="Nonpartisan logo"
          />
          <span className="np-name">Nonpartisan</span>
        </a>
      </header>

      <main className="np-main">
        <h1 className="np-title">Read beyond the headline.</h1>
        <p className="np-subtitle">
          Click to see all the different perspective of what you are about to
          read.
        </p>
        <button
          type="button"
          className="np-button"
          onClick={handleViewAllPerspectives}
          disabled={isLoading}
        >
          {isLoading ? 'Opening…' : 'View all perspectives'}
        </button>
      </main>

      <footer className="np-footer">
        <a href={SITE_URL} target="_blank" rel="noopener noreferrer">
          nonpartisan.ink
        </a>
      </footer>
    </div>
  );
}

export default App;
