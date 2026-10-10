import { useState } from 'react';
import independentLogo from '@/assets/independent.png';
import { PARSE_ARTICLE_MESSAGE } from '@/utils/parsers';
import './App.css';

const SITE_URL = 'https://nonpartisan.ink';

/**
 * Self-contained fallback parser injected via `scripting.executeScript`
 * (runs in the page, so it can't close over popup-scope imports —
 * the switch-case is intentionally inlined here).
 */
function parseArticleInPage(): string | null {
  let parser: 'indian-express' | 'unknown' = 'unknown';
  try {
    const parsed = new URL(window.location.href);
    const host = parsed.hostname.replace(/^www\./, '').toLowerCase();
    switch (host) {
      case 'indianexpress.com':
        if (parsed.pathname.startsWith('/article/')) {
          parser = 'indian-express';
        }
        break;
      default:
        parser = 'unknown';
        break;
    }
  } catch {
    parser = 'unknown';
  }

  switch (parser) {
    case 'indian-express': {
      const title =
        document
          .querySelector('h1[itemprop="headline"]')
          ?.textContent?.trim() ?? '';
      const synopsis =
        document
          .querySelector('h2[itemprop="description"]')
          ?.textContent?.trim() ?? '';
      return [title, synopsis].filter(Boolean).join(' ') || null;
    }
    default:
      return null;
  }
}

function App() {
  const [isLoading, setIsLoading] = useState(false);

  const handleViewAllPerspectives = async () => {
    setIsLoading(true);
    try {
      // Grab the current tab so we can parse what the user is about to read.
      const tabs = await browser.tabs.query({
        active: true,
        currentWindow: true,
      });
      const tab = tabs[0];

      let articleText: string | null = null;

      if (tab?.id !== undefined) {
        // 1. Preferred path: ask the content script (registered on Indian Express pages).
        try {
          const response = (await browser.tabs.sendMessage(tab.id, {
            type: PARSE_ARTICLE_MESSAGE,
          })) as { text?: string | null };
          articleText = response?.text ?? null;
        } catch {
          // 2. Fallback: no content script on this tab — inject the parser directly.
          try {
            const [result] = await browser.scripting.executeScript({
              target: { tabId: tab.id },
              func: parseArticleInPage,
            });
            articleText = (result?.result as string | null) ?? null;
          } catch {
            articleText = null;
          }
        }
      }

      console.log('[Nonpartisan] article text:', articleText);
    } catch {
      console.log('[Nonpartisan] article text:', null);
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
          {isLoading ? 'Reading…' : 'View all perspectives'}
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
