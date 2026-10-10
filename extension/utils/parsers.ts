export type ArticleParser = 'indian-express' | 'unknown';

export const PARSE_ARTICLE_MESSAGE = 'NONPARTISAN_PARSE_ARTICLE';

/**
 * Decide which parser handles a URL.
 * Add new outlets here as `case` branches (e.g. 'the-hindu', 'toi', ...).
 */
export function getArticleParser(url: string): ArticleParser {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.replace(/^www\./, '').toLowerCase();
    switch (host) {
      case 'indianexpress.com':
        if (parsed.pathname.startsWith('/article/')) {
          return 'indian-express';
        }
        return 'unknown';
      default:
        return 'unknown';
    }
  } catch {
    return 'unknown';
  }
}

/** Extract `<h1 itemprop="headline">` + `<h2 itemprop="description">` and combine. */
export function parseIndianExpressArticle(doc: Document): string | null {
  const title =
    doc.querySelector('h1[itemprop="headline"]')?.textContent?.trim() ?? '';
  const synopsis =
    doc.querySelector('h2[itemprop="description"]')?.textContent?.trim() ?? '';
  const combined = [title, synopsis].filter(Boolean).join(' ');
  return combined || null;
}

/** Fallback extractor for generic news articles across the web. */
export function parseGenericArticle(doc: Document): string | null {
  const title =
    doc.querySelector('meta[property="og:title"]')?.getAttribute('content')?.trim() ||
    doc.querySelector('meta[name="twitter:title"]')?.getAttribute('content')?.trim() ||
    doc.querySelector('article h1, main h1, h1')?.textContent?.trim() ||
    doc.title?.trim() ||
    '';

  const synopsis =
    doc.querySelector('meta[property="og:description"]')?.getAttribute('content')?.trim() ||
    doc.querySelector('meta[name="description"]')?.getAttribute('content')?.trim() ||
    '';

  const combined = [title, synopsis].filter(Boolean).join(' ');
  return combined || null;
}

/** Switch-case dispatch: pick a parser for the URL and run it against the DOM. */
export function parseArticle(url: string, doc: Document): string | null {
  switch (getArticleParser(url)) {
    case 'indian-express':
      return parseIndianExpressArticle(doc) || parseGenericArticle(doc);
    default:
      return parseGenericArticle(doc);
  }
}

