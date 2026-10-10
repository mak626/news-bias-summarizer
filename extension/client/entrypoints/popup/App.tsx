import { useState } from 'react';
import independentLogo from '@/assets/independent.png';
import { PARSE_ARTICLE_MESSAGE } from '@/utils/parsers';
import './App.css';

const SITE_URL = 'https://nonpartisan.ink';
const SUMMARIZE_API_URL = 'http://localhost:8008/';

/** Pull the news-group id out of the API response (JSON object, JSON string, or plain text). */
function extractNewsGroupId(raw: string): string | null {
  const trimmed = raw.trim().replace(/^"|"$/g, '');
  if (!trimmed) return null;
  try {
    const data: unknown = JSON.parse(trimmed);
    if (typeof data === 'string' && data.trim()) return data.trim();
    if (typeof data === 'object' && data !== null) {
      const record = data as Record<string, unknown>;
      for (const key of ['id', 'news_group_id', 'group_id', 'groupId', 'newsGroupId']) {
        const value = record[key];
        if (typeof value === 'string' && value.trim()) return value.trim();
        if (typeof value === 'number') return String(value);
      }
    }
  } catch {
    // Not JSON — treat the raw body as the id itself.
  }
  return trimmed || null;
}

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

      if (!articleText) {
        console.warn('[Nonpartisan] no article text found on this page.');
        return;
      }

      // Send the parsed text for summarization; the API returns a news-group id.
      const response = await fetch(SUMMARIZE_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: articleText }),
      });
      if (!response.ok) {
        throw new Error(`Summarize API failed with status ${response.status}`);
      }
      const newsGroupId = extractNewsGroupId(await response.text());
      if (!newsGroupId) {
        throw new Error('Summarize API returned an empty id');
      }

      await browser.tabs.create({
        url: `${SITE_URL}/news-group/${newsGroupId}`,
      });
    } catch (error) {
      console.error('[Nonpartisan] failed to load perspectives:', error);
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
