try { document.documentElement.dataset.theme = localStorage.getItem('nonpartisan-theme') === 'light' ? 'light' : 'dark'; } catch {}
document.addEventListener('DOMContentLoaded', () => {
  const button = document.querySelector('#theme-toggle');
  function syncTheme() {
    const dark = document.documentElement.dataset.theme !== 'light';
    button.setAttribute('aria-label', dark ? 'Switch to white theme' : 'Switch to dark theme');
    button.setAttribute('aria-pressed', String(dark));
    document.querySelector('#theme-label').textContent = dark ? 'Dark' : 'White';
  }
  button.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('nonpartisan-theme',next); } catch {}
    syncTheme();
  });
  syncTheme();
});
