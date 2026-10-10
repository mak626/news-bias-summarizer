(async()=>{
  const $=selector=>document.querySelector(selector);
  const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const palette=['#f9e2af','#89b4fa','#eba0ac'];
  const icons={political:'◈',people:'♙',language:'文',ownership:'▦',government:'⌂',emotion:'◉',gaps:'◫',evidence:'◇'};
  let dataset;
  try { dataset=await NewsApi.loadLab(); }
  catch(error){
    $('#stories').innerHTML='<div class="empty-state">Lens API unavailable. Start the web API on port 8001 and reload.</div>';
    $('#lens-viz').innerHTML='<div class="empty-state">Unable to load comparison data.</div>';
    console.error(error);return;
  }
  const dimensions=dataset.meta.lenses;
  const stories=dataset.stories;
  const categoryBar=document.querySelector('.topics');
  categoryBar.innerHTML=['All stories',...dataset.meta.categories].map(category=>`<button class="${category==='All stories'?'active':''}" data-category="${esc(category)}">${esc(category)}</button>`).join('');
  const state={story:stories[0]?.id,lens:dimensions[0]?.id,group:null,category:'All stories',query:''};
  const current=()=>stories.find(story=>story.id===state.story);
  const lens=()=>dimensions.find(item=>item.id===state.lens);
  const articles=()=>current()?.articles||[];

  function openDialog(title,body){$('#dialog-eyebrow').textContent=title;$('#dialog-body').innerHTML=body;$('#detail-dialog').showModal();}
  function groupIndex(article,dimension){return dimension.labels.indexOf(article.classifications[dimension.id]);}
  function coverageCounts(story){const d=dimensions.find(item=>item.id==='government');return d.labels.map(label=>story.articles.filter(article=>article.classifications.government===label).length);}
  function coverageSummary(story){const counts=coverageCounts(story),labels=['Supportive','Mixed','Critical'];return `<div class="coverage-summary"><div class="coverage-summary-top"><span>Coverage split</span><span>${story.article_count} reports</span></div><div class="coverage-bar">${counts.map((count,index)=>count?`<i class="${['supportive','mixed','critical'][index]}" style="--share:${count}"></i>`:'').join('')}</div><div class="coverage-labels">${counts.map((count,index)=>`<span>${count} ${labels[index].toLowerCase()}</span>`).join('')}</div></div>`;}
  function coverageBoard(story){const counts=coverageCounts(story),labels=['Supportive','Mixed','Critical'],government=dimensions.find(item=>item.id==='government');return `<section class="coverage-board"><div class="coverage-board-head"><div><span class="coverage-kicker">Story coverage</span><h3>How the reports frame it</h3></div><span>${story.article_count} reports</span></div><p>Each segment represents a sampled report. Select one to inspect it through the government lens.</p><div class="coverage-bar coverage-bar-large">${counts.map((count,index)=>count?`<button class="${['supportive','mixed','critical'][index]}" data-coverage-group="${index}" style="--share:${count}">${count} ${labels[index].toLowerCase()}</button>`:'').join('')}</div><div class="coverage-report-list">${story.articles.map((article,index)=>{const group=groupIndex(article,government);return `<button data-coverage-group="${group}"><span class="coverage-report-index ${['supportive','mixed','critical'][group]}">${String.fromCharCode(65+index)}</span><span>${esc(article.publisher)}</span><small>${labels[group]}</small></button>`;}).join('')}</div></section>`;}

  function renderStories(){
    const query=state.query.toLowerCase();
    const visible=stories.filter(story=>(state.category==='All stories'||story.category===state.category)&&`${story.title} ${story.summary} ${story.category}`.toLowerCase().includes(query));
    $('#story-count').textContent=`${visible.length} ${visible.length===1?'story':'stories'}`;
    $('#stories').innerHTML=visible.length?visible.map(story=>`<button class="story-card ${story.id===state.story?'selected':''}" data-story="${story.id}" aria-pressed="${story.id===state.story}"><img class="story-card-image" src="${esc(story.image.url)}" alt="${esc(story.image.alt)} — illustrative" loading="lazy"><div class="story-card-content"><div class="card-meta"><span>${esc(story.category)}</span></div><h3>${esc(story.title)}</h3><p class="desc">${esc(story.description)}</p>${coverageSummary(story)}<div class="card-bottom"><span>${story.article_count} media sources</span><span>${new Set(story.articles.map(article=>article.classifications.political)).size} framing groups</span></div></div></button>`).join(''):'<div class="empty-state">No sample stories match.</div>';
  }

  function renderComparison(){
    const story=current();if(!story)return;
    document.querySelector('.comparison-photo')?.remove();document.querySelector('.signal-tags')?.remove();document.querySelector('.coverage-board')?.remove();
    const figure=document.createElement('figure');figure.className='comparison-photo';figure.innerHTML=`<img src="${esc(story.image.url)}" alt="${esc(story.image.alt)}"><figcaption>Illustrative photo · ${esc(story.image.credit)}${story.image.source_url?` · <a href="${esc(story.image.source_url)}" target="_blank" rel="noopener noreferrer">Source</a>`:''}${story.image.license_url?` · <a href="${esc(story.image.license_url)}" target="_blank" rel="noopener noreferrer">${esc(story.image.license)}</a>`:''}</figcaption>`;$('.story-head').prepend(figure);
    $('#story-meta').innerHTML=`<span class="category">${esc(story.category)}</span><span class="fixture">Fictional example</span>`;
    $('#story-title').textContent=story.title;$('#story-summary').textContent=story.summary;
    $('#story-summary').insertAdjacentHTML('afterend',`<div class="signal-tags"><button data-lens="people">Whose voices are missing?</button><button data-lens="language">${new Set(story.articles.map(article=>article.language)).size} languages in the mix</button><button data-lens="evidence">${story.articles.filter(article=>article.classifications.evidence==='Primary document').length} link a primary document</button></div>${coverageBoard(story)}`);
    $('#source-avatars').innerHTML=story.articles.slice(0,3).map(article=>`<span>${esc(article.initials)}</span>`).join('');
    $('#source-count').textContent=`${story.article_count} articles · ${new Set(story.articles.map(article=>article.owner)).size} owner groups`;
    $('#fact-room').innerHTML=`<h3>Claims and context</h3><div class="fact-grid"><div class="fact-block"><span>Commonly reported</span><p>${esc(story.commonly_reported)}</p></div><div class="fact-block"><span>Disputed</span><p>${esc(story.disputed)}</p></div><div class="fact-block"><span>Less widely covered</span><p>${esc(story.less_widely_covered)}</p></div></div>`;
    renderLens();
  }

  function renderLens(){
    const dimension=lens(),sample=articles();if(!dimension)return;
    $('#lens-tabs').innerHTML=dimensions.map(item=>`<button role="tab" aria-selected="${item.id===dimension.id}" tabindex="${item.id===dimension.id?0:-1}" class="${item.id===dimension.id?'selected':''}" data-lens="${item.id}"><span aria-hidden="true">${icons[item.id]||'◇'}</span>${esc(item.name)}</button>`).join('');
    const counts=dimension.labels.map((label,index)=>dimension.id==='gaps'?sample.filter(article=>article.contexts_included.length===3-index).length:sample.filter(article=>groupIndex(article,dimension)===index).length);
    const percentages=counts.map(count=>sample.length?Math.round(count/sample.length*100):0);
    let chart;
    if(dimension.id==='gaps') chart=`<div class="gap-rows">${current().contexts.map(context=>`<div class="gap-row"><span>${esc(context)}</span><div>${sample.map(article=>`<i class="${article.contexts_included.includes(context)?'on':''}"></i>`).join('')}</div></div>`).join('')}</div>`;
    else if(dimension.id==='evidence'||dimension.id==='ownership') chart=`<div class="evidence-grid">${dimension.labels.map((label,index)=>`<button class="evidence-tile" data-group="${index}" style="--color:${palette[index]}"><b>${counts[index]}<small> / ${sample.length}</small></b><span>${esc(label)}</span></button>`).join('')}</div>`;
    else chart=`<div class="spectrum">${dimension.labels.map((label,index)=>counts[index]?`<button data-group="${index}" class="${state.group===index?'chosen':''}" style="--color:${palette[index]};--size:${counts[index]}">${percentages[index]}%</button>`:'').join('')}</div>`;
    $('#lens-viz').innerHTML=`<div class="lens-insight"><div class="insight-top"><div class="insight-title">${esc(dimension.title)}</div><span class="count-tag">${sample.length} articles</span></div><p class="insight-description">${esc(dimension.description)}</p>${chart}<div class="legend">${dimension.labels.map((label,index)=>`<button data-group="${index}" aria-pressed="${state.group===index}"><i class="swatch" style="--color:${palette[index]}"></i>${esc(label)} · ${counts[index]}</button>`).join('')}</div></div>`;
    const visible=sample.filter(article=>state.group===null||groupIndex(article,dimension)===state.group);
    $('#media-title').textContent=`Media by ${dimension.name.toLowerCase()}`;$('#media-total').textContent=`${visible.length} of ${sample.length} sources`;$('#clear-filter').hidden=state.group===null;
    $('#media-groups').innerHTML=dimension.labels.map((label,index)=>{if(state.group!==null&&state.group!==index)return '';const members=sample.filter(article=>groupIndex(article,dimension)===index);return `<div class="media-group" style="--color:${palette[index]}"><div class="group-title"><span>${esc(label)}</span><span>${members.length} sources</span></div><div class="media-members">${members.map(article=>`<button class="media-item" data-media="${esc(article.id)}"><span class="monogram">${esc(article.initials)}</span><span><span class="media-name">${esc(article.publisher)}</span><span class="media-meta" style="display:block">${esc(article.language)} · View evidence</span></span></button>`).join('')}</div></div>`;}).join('');
  }

  function inspectMedia(id){const article=articles().find(item=>item.id===id),dimension=lens();if(!article)return;openDialog('Source detail · fictional publisher',`<div><strong>${esc(article.publisher)}</strong><div class="media-meta">${esc(article.language)} · ${esc(article.owner)}</div></div><h2 class="dialog-title">${esc(article.headline)}</h2><div class="detail-block"><h4>${esc(dimension.title)}</h4><span class="pill">${esc(article.classifications[dimension.id])}</span><div class="quote-box">“${esc(article.excerpt)}”</div></div><div class="detail-block"><h4>Context included</h4>${current().contexts.map(context=>`<span class="pill">${article.contexts_included.includes(context)?'✓':'—'} ${esc(context)}</span>`).join('')}</div>`);}
  function claimsDialog(){const story=current();openDialog('Claim comparison',`<h2 class="dialog-title">What agrees. What differs.</h2><div class="claim"><span class="status">Commonly reported</span><p>${esc(story.commonly_reported)}</p></div><div class="claim contested"><span class="status">Disputed</span><p>${esc(story.disputed)}</p></div><div class="claim"><span class="status">Less widely covered</span><p>${esc(story.less_widely_covered)}</p></div>`);}
  function methodDialog(){openDialog('Our methodology',`<h2 class="dialog-title">How coverage is compared</h2><p class="dialog-intro">${esc(dataset.meta.methodology)}</p><div class="detail-block"><h4>Prototype scope</h4><p>${esc(dataset.meta.notice)}</p></div>`);}

  document.addEventListener('click',event=>{const button=event.target.closest('button');if(!button)return;if(button.dataset.story){state.story=button.dataset.story;state.group=null;renderStories();renderComparison();}else if(button.dataset.coverageGroup!==undefined){state.lens='government';state.group=Number(button.dataset.coverageGroup);renderLens();$('#lens').scrollIntoView({behavior:'smooth'});}else if(button.dataset.lens){state.lens=button.dataset.lens;state.group=null;renderLens();}else if(button.dataset.group!==undefined){const group=Number(button.dataset.group);state.group=state.group===group?null:group;renderLens();}else if(button.dataset.media){inspectMedia(button.dataset.media);}else if(button.dataset.category){state.category=button.dataset.category;document.querySelectorAll('[data-category]').forEach(item=>item.classList.toggle('active',item.dataset.category===state.category));renderStories();}else if(button.dataset.modal==='method')methodDialog();else if(button.dataset.modal==='extension')openDialog('Browser companion · planned','<h2 class="dialog-title">A wider view, wherever you read.</h2><p class="dialog-intro">The browser companion is planned for a future release.</p>');else if(button.id==='clear-filter'){state.group=null;renderLens();}else if(button.id==='close-dialog')$('#detail-dialog').close();else if(button.id==='claims-button')claimsDialog();});
  $('#search').addEventListener('input',event=>{state.query=event.target.value;renderStories();});
  $('#detail-dialog').addEventListener('click',event=>{if(event.target===$('#detail-dialog'))event.target.close();});
  renderStories();renderComparison();
})();
