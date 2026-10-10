import { useState, useEffect, useCallback } from 'react';
import independentLogo from '@/assets/independent.png';
import { PARSE_ARTICLE_MESSAGE } from '@/utils/parsers';
import './App.css';

const BACKEND_URL = 'http://localhost:8000';
const ANALYZE_API_URL = `${BACKEND_URL}/api/v1/analyze`;
const PORTAL_URL = `${BACKEND_URL}/web/index.html`;

interface ErrorState {
  title: string;
  message: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

/**
 * Self-contained fallback parser injected via `scripting.executeScript`
 * (runs in the page, so it can't close over popup-scope imports).
 */
function parseArticleInPage(): string | null {
  try {
    const parsed = new URL(window.location.href);
    const host = parsed.hostname.replace(/^www\./, '').toLowerCase();

    // 1. Indian Express specific selectors
    if (host.includes('indianexpress.com')) {
      const title =
        document.querySelector('h1[itemprop="headline"]')?.textContent?.trim() ?? '';
      const synopsis =
        document.querySelector('h2[itemprop="description"]')?.textContent?.trim() ?? '';
      const combined = [title, synopsis].filter(Boolean).join(' ');
      if (combined) return combined;
    }

    // 2. Generic news headline & synopsis extraction
    const headline =
      document.querySelector('meta[property="og:title"]')?.getAttribute('content')?.trim() ||
      document.querySelector('meta[name="twitter:title"]')?.getAttribute('content')?.trim() ||
      document.querySelector('article h1, main h1, h1[itemprop="headline"], h1')?.textContent?.trim() ||
      document.title.replace(/\s*[-|–—].*$/, '').trim();

    const synopsis =
      document.querySelector('meta[property="og:description"]')?.getAttribute('content')?.trim() ||
      document.querySelector('meta[name="description"]')?.getAttribute('content')?.trim() ||
      document.querySelector('h2[itemprop="description"], article h2, p')?.textContent?.trim() ||
      '';

    const text = [headline, synopsis].filter(Boolean).join(' ').trim();
    return text || null;
  } catch {
    return null;
  }
}

function App() {
  const [isLoading, setIsLoading] = useState(false);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);
  const [error, setError] = useState<ErrorState | null>(null);

  const checkHealth = useCallback(async (): Promise<boolean> => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);
      const res = await fetch(`${BACKEND_URL}/health`, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (res.ok) {
        setIsBackendOnline(true);
        return true;
      } else {
        setIsBackendOnline(false);
        return false;
      }
    } catch {
      setIsBackendOnline(false);
      return false;
    }
  }, []);

  useEffect(() => {
    checkHealth().then((online) => {
      if (!online) {
        setError({
          title: 'Backend Unavailable',
          message: `Cannot reach backend at ${BACKEND_URL}. Please start the backend service.`,
          action: {
            label: 'Check Connection',
            onClick: () => {
              setError(null);
              checkHealth().then((nowOnline) => {
                if (!nowOnline) {
                  setError({
                    title: 'Backend Unavailable',
                    message: `Cannot reach backend at ${BACKEND_URL}. Ensure it is running on port 8000.`,
                  });
                }
              });
            },
          },
        });
      }
    });
  }, [checkHealth]);

  const handleViewAllPerspectives = async () => {
    setError(null);
    setIsLoading(true);
    try {
      // Grab the current active tab to parse the active news article
      const tabs = await browser.tabs.query({
        active: true,
        currentWindow: true,
      });
      const tab = tabs[0];

      let articleText: string | null = null;

      if (tab?.id !== undefined) {
        // 1. Preferred path: ask the content script
        try {
          const response = (await browser.tabs.sendMessage(tab.id, {
            type: PARSE_ARTICLE_MESSAGE,
          })) as { text?: string | null };
          articleText = response?.text ?? null;
        } catch {
          // 2. Fallback: no content script on this tab — inject the parser directly
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

      console.log('[Nonpartisan] parsed article query:', articleText);

      if (!articleText) {
        console.warn('[Nonpartisan] no article text found on this page.');
        setError({
          title: 'No Article Detected',
          message: 'Unable to detect a news article on this page. Navigate to an article and try again.',
        });
        return;
      }

      // Send the query to backend /api/v1/analyze
      let response: Response;
      try {
        response = await fetch(ANALYZE_API_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: articleText }),
        });
      } catch (fetchErr) {
        setIsBackendOnline(false);
        setError({
          title: 'Backend Unavailable',
          message: `Backend is unreachable at ${BACKEND_URL}. Please start the server.`,
          action: {
            label: 'Retry',
            onClick: () => handleViewAllPerspectives(),
          },
        });
        return;
      }

      if (!response.ok) {
        setIsBackendOnline(false);
        let detail = '';
        try {
          const data = await response.json();
          detail = data.detail || data.message || '';
        } catch {}
        setError({
          title: 'Analysis Error',
          message: detail ? `Server error: ${detail}` : `Backend error (status ${response.status}). Please try again.`,
          action: {
            label: 'Retry',
            onClick: () => handleViewAllPerspectives(),
          },
        });
        return;
      }

      setIsBackendOnline(true);
      const data = await response.json();
      console.log('[Nonpartisan] backend response:', data);

      // Extract the target redirection URL
      const targetUrl =
        data.web_url ||
        (data.redirect_url ? `${BACKEND_URL}/web${data.redirect_url}` : null) ||
        (data.id ? `${BACKEND_URL}/web/story.html?id=${data.id}` : null);

      if (!targetUrl) {
        setError({
          title: 'Invalid Response',
          message: 'Backend succeeded but did not return a valid web redirection URL.',
        });
        return;
      }

      // Redirect user to the web story view
      await browser.tabs.create({
        url: targetUrl,
      });
    } catch (error) {
      console.error('[Nonpartisan] failed to load perspectives:', error);
      setError({
        title: 'Error',
        message: error instanceof Error ? error.message : 'An unexpected error occurred.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="np-popup">
      <header className="np-header">
        <a
          href={PORTAL_URL}
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

        <div
          className={`np-status-badge ${
            isBackendOnline === true
              ? 'is-online'
              : isBackendOnline === false
              ? 'is-offline'
              : 'is-checking'
          }`}
          title={
            isBackendOnline === true
              ? `Backend connected (${BACKEND_URL})`
              : isBackendOnline === false
              ? `Backend disconnected (${BACKEND_URL})`
              : 'Checking backend status...'
          }
        >
          <span className="np-status-dot" />
          <span className="np-status-text">
            {isBackendOnline === true
              ? 'Online'
              : isBackendOnline === false
              ? 'Offline'
              : 'Connecting'}
          </span>
        </div>
      </header>

      <main className="np-main">
        <h1 className="np-title">Read beyond the headline.</h1>
        <p className="np-subtitle">
          Click to see all the different perspectives of what you are about to read.
        </p>

        {error && (
          <div className="np-alert" role="alert">
            <div className="np-alert-header">
              <svg
                className="np-alert-icon"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <strong className="np-alert-title">{error.title}</strong>
              <button
                type="button"
                className="np-alert-close"
                onClick={() => setError(null)}
                aria-label="Dismiss error notification"
              >
                &times;
              </button>
            </div>
            <p className="np-alert-message">{error.message}</p>
            {error.action && (
              <button
                type="button"
                className="np-alert-action"
                onClick={error.action.onClick}
                disabled={isLoading}
              >
                {error.action.label}
              </button>
            )}
          </div>
        )}

        <button
          type="button"
          className="np-button"
          onClick={handleViewAllPerspectives}
          disabled={isLoading}
        >
          {isLoading ? (
            <span className="np-button-content">
              <span className="np-spinner" />
              Reading…
            </span>
          ) : (
            'View all perspectives'
          )}
        </button>
      </main>

      <footer className="np-footer">
        <a href={PORTAL_URL} target="_blank" rel="noopener noreferrer">
          nonpartisan web portal
        </a>
      </footer>
    </div>
  );
}

export default App;
