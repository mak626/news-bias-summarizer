(async()=>{
  const root=document.querySelector('#story-page');
  const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  let edition;
  try{edition=await NewsApi.loadEdition();}
  catch(error){root.innerHTML='<div class="report-empty"><h1>Coverage API unavailable</h1><p>Start the web API on port 8001, then reload this page.</p></div>';console.error(error);return;}
  const id=new URLSearchParams(location.search).get('id');
  const story=edition.stories.find(item=>item.id===id);
  if(!story){root.innerHTML='<div class="report-empty"><h1>Story not found</h1><p><a href="index.html#headlines">Browse all reports</a></p></div>';return;}

  document.title=`${story.title} — nonpartisan.ink`;
  document.querySelector('.report-footer span').textContent=`Sources checked ${edition.checked}`;
  const alignmentLabels={opposition:'Opposition / critical',mixed:'Mixed / contextual',ruling:'Official / ruling-side',unclear:'Insufficient evidence'};
  const alignmentCounts=story.reports.reduce((counts,report)=>{counts[report.alignment]=(counts[report.alignment]||0)+1;return counts;},{});
  const assessed=story.reports.filter(report=>report.alignment!=='unclear');
  const notice=assessed.length
    ? {title:'Article-level framing assessments available',body:`${assessed.length} of ${story.reports.length} reviewed reports contain enough evidence for a framing assessment. Open each report to inspect the reasoning.`}
    : {title:'Not enough evidence to assess political framing',body:'The reviewed material does not establish a domestic party-political framing. This is not a verdict on factual accuracy.'};
  const fullCount=story.reports.filter(report=>/full/i.test(report.access)).length;
  const excerptCount=story.reports.length-fullCount;
  const voices=[...new Set(story.reports.flatMap(report=>report.voice.split(/,| and /).map(value=>value.trim())).filter(Boolean))];
  const reportById=id=>story.reports.find(report=>report.id===id);
  const itemLink=item=>item.url||reportById(item.source)?.url;
  const claims=story.claims.map(claim=>`<article class="content-claim"><span class="claim-state ${esc(claim.status.toLowerCase())}">${esc(claim.status)}</span><p>${esc(claim.text)}</p>${itemLink(claim)?`<a href="${esc(itemLink(claim))}" target="_blank" rel="noopener noreferrer">Read source ↗</a>`:''}</article>`).join('');
  const perspectives=story.perspectives.map(item=>`<article class="perspective-card"><h3>${esc(item.title)}</h3><p>${esc(item.text)}</p>${itemLink(item)?`<a href="${esc(itemLink(item))}" target="_blank" rel="noopener noreferrer">Inspect source ↗</a>`:''}</article>`).join('');
  const related=edition.stories.filter(item=>item.id!==story.id).slice(0,3).map(item=>`<a class="related-card" href="story.html?id=${encodeURIComponent(item.id)}"><span>${esc(item.category)} · ${esc(item.date)}</span><h3>${esc(item.title)}</h3><small>${item.reports.length} reviewed ${item.reports.length===1?'report':'reports'} →</small></a>`).join('');

  root.innerHTML=`
    <section class="report-titleblock"><h1>Source-by-source reporting</h1><p>What each report says — and what the evidence supports.</p></section>
    <section class="report-summary">
      <div class="report-summary-top">
        <div class="report-story-id"><figure><img src="${esc(story.photo.url)}" alt="${esc(story.photo.alt)}"><figcaption>${esc(story.photo.credit)}</figcaption></figure><div><span class="story-category">${esc(story.category)} · ${esc(story.place)}</span><h2>${esc(story.title)}</h2><p>${story.reports.length} reports reviewed <span>•</span> Updated ${esc(story.date)}</p></div></div>
        <div class="report-notice"><span>i</span><div><h3>${esc(notice.title)}</h3><p>${esc(notice.body)}</p></div></div>
      </div>
      <div class="report-facts"><strong>Coverage in this analysis</strong>${fullCount?`<span class="report-chip"><i>▤</i>${fullCount} full ${fullCount===1?'report':'reports'}</span>`:''}${excerptCount?`<span class="report-chip"><i>▤</i>${excerptCount} article ${excerptCount===1?'excerpt':'excerpts'}</span>`:''}<strong class="report-voice">Voices identified</strong><span class="report-chip"><i>♙</i>${esc(voices.slice(0,3).join(', ')||'Not specified')}</span></div>
    </section>
    <div class="reports-heading" id="reports"><h2>Reports reviewed (${story.reports.length})</h2><label class="reports-sort"><span>Sort by</span><select id="report-sort"><option value="date">Date (newest first)</option><option value="source">Source name</option><option value="framing">Framing assessment</option></select></label></div>
    <section class="report-list" aria-live="polite" aria-label="Reviewed reports"></section>
    <section class="story-content-grid">
      <div class="story-content-main">
        <article class="content-panel story-brief"><span class="content-kicker">The story in brief</span><h2>What is being reported</h2><p>${esc(story.summary)}</p><div class="takeaway-box"><strong>Keep in mind</strong><p>${esc(story.takeaway)}</p></div>${story.primary?`<a class="primary-document" href="${esc(story.primary.url)}" target="_blank" rel="noopener noreferrer">${esc(story.primary.label)} ↗</a>`:''}</article>
        <article class="content-panel"><span class="content-kicker">Claims & context</span><h2>Separate the accounts</h2><div class="claims-list">${claims||'<p>No individual claims are listed for this story.</p>'}</div></article>
        ${perspectives?`<article class="content-panel"><span class="content-kicker">Competing positions</span><h2>Different voices, one story</h2><div class="perspective-grid">${perspectives}</div></article>`:''}
      </div>
      <aside class="story-content-aside"><article class="questions-card"><span class="content-kicker">Questions still open</span><h2>What to look for next</h2><ul>${story.gaps.map(gap=>`<li>${esc(gap)}</li>`).join('')}</ul></article><article class="coverage-card"><span class="content-kicker">Assessment snapshot</span><h2>Framing in this sample</h2>${Object.entries(alignmentCounts).map(([key,count])=>`<div><span>${esc(alignmentLabels[key]||key)}</span><strong>${count}</strong></div>`).join('')}</article></aside>
    </section>
    <section class="related-reports"><div><span class="content-kicker">Keep widening the view</span><h2>Related coverage</h2></div><div class="related-grid">${related}</div></section>
    <section class="report-method" id="methodology"><h2>How to read these assessments</h2><p>${esc(edition.meta.methodology)} Confidence describes the strength of the framing inference, while evidence and original-report links let you inspect the basis for each assessment.</p></section>`;

  const list=document.querySelector('.report-list');
  const search=document.querySelector('#report-search');
  const sort=document.querySelector('#report-sort');
  let query='';

  function reportCard(report){
    const framing=alignmentLabels[report.alignment]||report.alignment;
    const sourceRole=report.sourceRole||report.host||report.origin||report.publisher;
    const key=`report-${report.id}`;
    return `<article class="source-report" id="${esc(report.id)}">
      <div class="source-report-head">
        <span class="source-mark">${esc(report.initials)}</span>
        <div class="source-meta"><h3>${esc(report.publisher)}</h3><p>${esc(report.date)} 2026${report.host?` · via ${esc(report.host)}`:''}</p></div>
        <span class="access-badge">${esc(report.access)}</span>
        <span class="source-role-badge">${esc(sourceRole)}</span>
        <a class="original-report" href="${esc(report.url)}" target="_blank" rel="noopener noreferrer">Open original report ↗</a>
      </div>
      <div class="source-report-main">
        <div class="source-report-copy"><h4>${esc(report.title)}</h4><p>${esc(report.evidence)}</p></div>
        <div class="framing-summary"><span class="framing-icon" aria-hidden="true">⚖</span><div><div class="framing-summary-title"><strong>Framing assessment</strong><span class="framing-badge">${esc(framing)}</span></div><p>${esc(report.why)}</p></div></div>
      </div>
      <div class="report-tabs" role="tablist" aria-label="${esc(report.publisher)} report details" data-report-tabs="${esc(key)}">
        <button type="button" role="tab" id="${esc(key)}-tab-evidence" aria-controls="${esc(key)}-panel-evidence" aria-selected="true" tabindex="0" data-report-tab="evidence">Key evidence</button>
        <button type="button" role="tab" id="${esc(key)}-tab-why" aria-controls="${esc(key)}-panel-why" aria-selected="false" tabindex="-1" data-report-tab="why">Why this matters</button>
        <button type="button" role="tab" id="${esc(key)}-tab-voices" aria-controls="${esc(key)}-panel-voices" aria-selected="false" tabindex="-1" data-report-tab="voices">Voices cited</button>
        <button type="button" role="tab" id="${esc(key)}-tab-source" aria-controls="${esc(key)}-panel-source" aria-selected="false" tabindex="-1" data-report-tab="source">About this source</button>
      </div>
      <section class="report-tab-panel" id="${esc(key)}-panel-evidence" role="tabpanel" aria-labelledby="${esc(key)}-tab-evidence" data-report-panel="evidence"><div class="evidence-quote"><span aria-hidden="true">“</span><div><strong>Evidence summary</strong><p>${esc(report.evidence)}</p><small>Paraphrased from ${esc(report.publisher)}, ${esc(report.date)} 2026</small></div></div><div class="evidence-context"><h5>Why this supports the assessment</h5><p>${esc(report.why)}</p><span>${esc(report.confidence)} confidence · ${esc(report.scope)}</span></div></section>
      <section class="report-tab-panel" id="${esc(key)}-panel-why" role="tabpanel" aria-labelledby="${esc(key)}-tab-why" data-report-panel="why" hidden><div class="tab-explanation"><h5>Why this matters</h5><p>${esc(report.why)}</p><p class="assessment-limits">This is an assessment of political framing in the reviewed material, not a verdict on factual accuracy.</p><span>${esc(report.confidence)} confidence · ${esc(report.scope)}</span></div></section>
      <section class="report-tab-panel" id="${esc(key)}-panel-voices" role="tabpanel" aria-labelledby="${esc(key)}-tab-voices" data-report-panel="voices" hidden><div class="tab-explanation"><h5>Voices cited in this report</h5><p>${esc(report.voice||'No cited voices are specified in the reviewed material.')}</p></div></section>
      <section class="report-tab-panel" id="${esc(key)}-panel-source" role="tabpanel" aria-labelledby="${esc(key)}-tab-source" data-report-panel="source" hidden><div class="tab-explanation"><h5>About this source</h5><p><strong>${esc(report.publisher)}</strong>${report.host?` · syndicated by ${esc(report.host)}`:''}</p><p>${esc(report.access)}. Source role: ${esc(sourceRole)}.</p><a href="${esc(report.url)}" target="_blank" rel="noopener noreferrer">Open the original report ↗</a></div></section>
    </article>`;
  }

  function activateReportTab(tab,focus=false){
    const card=tab.closest('.source-report');
    if(!card)return;
    card.querySelectorAll('[data-report-tab]').forEach(button=>{
      const active=button===tab;
      button.setAttribute('aria-selected',String(active));
      button.tabIndex=active?0:-1;
    });
    card.querySelectorAll('[data-report-panel]').forEach(panel=>{panel.hidden=panel.dataset.reportPanel!==tab.dataset.reportTab;});
    if(focus)tab.focus();
  }
  list.addEventListener('click',event=>{
    const tab=event.target.closest('[data-report-tab]');
    if(tab)activateReportTab(tab);
  });
  list.addEventListener('keydown',event=>{
    const tab=event.target.closest('[data-report-tab]');
    if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
    event.preventDefault();
    const tabs=[...tab.closest('[role="tablist"]').querySelectorAll('[role="tab"]')];
    const index=tabs.indexOf(tab);
    const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
    activateReportTab(tabs[next],true);
  });

  function render(){
    let reports=story.reports.filter(report=>`${report.publisher} ${report.title} ${report.evidence} ${report.voice}`.toLowerCase().includes(query));
    if(sort.value==='source')reports=[...reports].sort((a,b)=>a.publisher.localeCompare(b.publisher));
    if(sort.value==='framing')reports=[...reports].sort((a,b)=>(alignmentLabels[a.alignment]||a.alignment).localeCompare(alignmentLabels[b.alignment]||b.alignment));
    list.innerHTML=reports.length?reports.map(reportCard).join(''):'<div class="report-empty"><h3>No reports match your search</h3><p>Try a publisher, headline, voice, or evidence term.</p></div>';
  }
  search.addEventListener('input',event=>{query=event.target.value.trim().toLowerCase();render();});
  sort.addEventListener('change',render);
  render();
  if(location.hash){
    const target=document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if(target)setTimeout(()=>target.scrollIntoView({block:'center'}),120);
  }
})();
