import { PARSE_ARTICLE_MESSAGE, parseArticle } from '@/utils/parsers';

export default defineContentScript({
  matches: ['*://*.indianexpress.com/*'],
  main() {
    browser.runtime.onMessage.addListener((message: unknown) => {
      if (
        typeof message === 'object' &&
        message !== null &&
        (message as { type?: string }).type === PARSE_ARTICLE_MESSAGE
      ) {
        const text = parseArticle(window.location.href, document);
        console.log('[Nonpartisan] parsed article:', text);
        return Promise.resolve({ text });
      }
    });
  },
});
