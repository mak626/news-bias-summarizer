// The edition and story pages share one source dataset and coverage components.
(async () => {
  const feed = document.querySelector('#news-grid');
  let edition;
  try { edition=await NewsApi.loadEdition(); }
  catch (error) {
    feed.innerHTML=`<div class="india-empty"><h3>Coverage API unavailable</h3><p>Start the web API on port 8001, then reload this page.</p></div>`;
    console.error(error); return;
  }
  const ui = IndiaCoverage;
  const filters = {category:new URLSearchParams(location.search||'').get('topic')==='narendra-modi'?'Narendra Modi':'All',query:'',lens:'alignment'};
  const lead=ui.get(edition.meta.lead_story_id)||edition.stories[0];
  const leadPath=ui.path(lead.id);
  document.querySelector('#lead-story-link').href=leadPath;
  document.querySelector('#india-hero-preview').innerHTML=`<span class="india-eyebrow">One story. Different frames.</span><h2>${ui.escape(lead.title)}</h2><p>${lead.reports.length} reviewed reports · ${ui.escape(lead.date)}</p>${ui.bar(lead)}${ui.legend(lead)}<a class="text-link" href="${ui.path(lead.id)}">Read across the coverage →</a>`;
  document.querySelector('.edition-row').innerHTML=`<span>Sources checked ${ui.escape(edition.checked)}</span><span>Latest reviewed reports through ${ui.escape(edition.through)}</span>`;
  function render() {
    const isModi=filters.category==='Narendra Modi';
    const stories = indiaEdition.stories.filter(story => (filters.category==='All'||(isModi?(story.topics||[]).includes('narendra-modi'):story.category===filters.category)) && `${story.title} ${story.dek} ${story.place} ${story.category} ${story.reports.map(report=>report.publisher).join(' ')}`.toLowerCase().includes(filters.query));
    feed.innerHTML = stories.length ? stories.map(story=>ui.card(story,filters.lens)).join('') : '<div class="india-empty">No stories match. Try another topic or search.</div>';
    document.querySelector('#india-result-count').textContent = `${stories.length} ${stories.length===1?'story':'stories'}`;
    document.querySelector('.snapshot-label').textContent=`${indiaEdition.stories.length} stories · Source-backed comparisons`;
    document.querySelector('.india-edition .title-row h2').textContent=isModi?'Narendra Modi: across the coverage':'See how the story is covered';
    document.querySelectorAll('[data-india-category]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.indiaCategory===filters.category)));
    document.querySelectorAll('[data-india-lens]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.indiaLens===filters.lens)));
  }
  const categories=['All',...edition.meta.categories,'Narendra Modi'];
  document.querySelector('#india-controls').innerHTML = `<div class="india-feed-toolbar"><div class="india-lens-switch" role="group" aria-label="Coverage lens"><button data-india-lens="alignment" aria-pressed="true"><span aria-hidden="true">▥</span> Government framing</button><button data-india-lens="focus" aria-pressed="false"><span aria-hidden="true">◉</span> Coverage focus</button></div><label class="india-search"><span aria-hidden="true">⌕</span><input type="search" id="india-search" placeholder="Search stories or sources" aria-label="Search India coverage"></label></div><div class="india-feed-topics"><div role="group" aria-label="India news topic">${categories.map(category=>`<button data-india-category="${category}" aria-pressed="${category===filters.category}">${category==='All'?'All stories':category}</button>`).join('')}</div><span id="india-result-count"></span></div><p class="india-lens-note">Compare the article’s framing, then tap a source to read the evidence.</p>`;
  document.querySelector('#india-controls').addEventListener('click',event=>{
    const button=event.target.closest('button');if(!button)return;
    if(button.dataset.indiaCategory)filters.category=button.dataset.indiaCategory;
    if(button.dataset.indiaLens)filters.lens=button.dataset.indiaLens;
    render();
  });
  document.querySelector('#india-search').addEventListener('input',event=>{filters.query=event.target.value.trim().toLowerCase();render();});
  document.querySelectorAll('#hook-button, #perspective-button').forEach(button=>button.addEventListener('click',()=>{
    if(window.NewsPageTransition)window.NewsPageTransition.navigate(leadPath);
    else location.href=leadPath;
  }));
  render();
})();
