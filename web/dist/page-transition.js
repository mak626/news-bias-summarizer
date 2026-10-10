(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const status = document.createElement('div');
  status.className = 'page-transition-status';
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  status.innerHTML = '<span>Opening report</span>';
  document.body.insertAdjacentElement('afterend', status);

  const navigate = destination => {
    status.classList.add('is-visible');
    document.body.classList.add('page-leaving');
    if (reduced.matches) location.assign(destination);
    else setTimeout(() => location.assign(destination), 170);
  };
  window.NewsPageTransition = {navigate};

  const isStoryLink = anchor => {
    if (!anchor || anchor.target || anchor.hasAttribute('download')) return false;
    const url = new URL(anchor.href, location.href);
    return url.origin === location.origin && /\/story\.html$/.test(url.pathname);
  };

  document.addEventListener('click', event => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const anchor = event.target.closest('a[href]');
    if (!isStoryLink(anchor)) return;
    event.preventDefault();
    navigate(anchor.href);
  });

  addEventListener('pageshow', () => {
    document.body.classList.remove('page-leaving');
    status.classList.remove('is-visible');
  });
})();
