/* Shared, data-driven coverage components for the edition and story pages. */
window.IndiaCoverage = (() => {
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const groups = {
    alignment: [
      {id:'opposition',label:'Opposition / critical',short:'Opposition',tone:'opposition'},
      {id:'mixed',label:'Mixed / contextual',short:'Mixed',tone:'balanced'},
      {id:'ruling',label:'Ruling party / official',short:'Ruling side',tone:'ruling'},
      {id:'unclear',label:'Unclear / insufficient evidence',short:'Unclear',tone:'unrated'}
    ],
    focus: [
      {id:'rights',label:'Rights & scrutiny',short:'Rights',tone:'opposition'},
      {id:'context',label:'Context & impacts',short:'Context',tone:'balanced'},
      {id:'official',label:'Official response',short:'Official',tone:'ruling'}
    ]
  };
  const get = id => indiaEdition.stories.find(story => story.id === id);
  const path = id => `story.html?id=${encodeURIComponent(id)}`;
  const counts = (story, lens='alignment') => groups[lens].map(group => ({...group,count:story.reports.filter(report => report[lens] === group.id).length}));
  function bar(story, lens='alignment', interactive=false, selected='all') {
    const parts = counts(story,lens).filter(group => group.count);
    const description = parts.map(group => `${group.count} ${group.label}`).join(', ');
    return `<div class="india-spectrum ${interactive?'is-interactive':''}" ${interactive?'role="group"':'role="img"'} aria-label="${escape(description)}">${parts.map(group => {
      const attrs = `class="${group.tone}" style="--portion:${group.count}"`;
      return interactive ? `<button type="button" ${attrs} data-report-filter="${group.id}" aria-pressed="${selected===group.id}" aria-label="Show ${group.count} ${escape(group.label)} reports"><span>${group.count}</span> ${group.short}</button>` : `<span ${attrs}><b>${group.count}</b><span>${group.short}</span></span>`;
    }).join('')}</div>`;
  }
  function legend(story,lens='alignment') {
    return `<div class="india-legend">${counts(story,lens).map(group=>`<span><i class="${group.tone}"></i>${group.count} ${escape(group.short.toLowerCase())}</span>`).join('')}</div>`;
  }
  const illustrations = {
    protest: `<rect x="34" y="27" width="105" height="65" rx="5"/><path d="M86 92v38M47 45h77M55 58h61M58 73h57"/><rect x="239" y="43" width="85" height="57" rx="5"/><path d="M280 100v34M251 63h60M254 79h53"/><circle cx="57" cy="162" r="18"/><circle cx="117" cy="150" r="21"/><circle cx="185" cy="171" r="19"/><circle cx="254" cy="153" r="20"/><circle cx="313" cy="173" r="17"/><path d="M30 221v-23q27-32 54 0v23M87 221v-37q30-33 60 0v37M157 221v-14q28-32 57 0v14M224 221v-34q30-32 60 0v34M287 221v-13q26-30 51 0v13"/>`,
    diplomacy: `<path d="M81 163q-29-58 3-96t70-16q30 10 48 34t40 24q27 0 46 24"/><circle cx="180" cy="125" r="88"/><ellipse cx="180" cy="125" rx="42" ry="88"/><path d="M98 91h164M92 127h177M103 165h152"/><rect x="222" y="149" width="92" height="61" rx="6"/><circle cx="240" cy="171" r="6"/><path d="M255 170h43M236 188h62"/>`,
    saudi: `<path d="M29 206h306M46 206v-50h35v50M106 206v-81h45v81M180 206V84h38v122M263 206V51l28-23 28 23v155M291 30v114M265 114h51M277 59h28"/><path d="M68 87l40-22 40 22v32l-40 24-40-24zM90 100l13 13 25-30"/>`,
    economy: `<path d="M37 206h286M56 94l122-58 123 58zM64 113h233M70 190h222M84 114v74M129 114v74M176 114v74M222 114v74M271 114v74"/><circle cx="280" cy="190" r="38"/><path d="M264 173h30M264 184h30M273 173q25 11 0 23l21 17"/>`,
    markets: `<path d="M45 43v166h278M76 183l48-56 41 24 55-70 36 23 52-55M280 49h28v29"/><path d="M80 59v23M131 67v34M182 43v36M234 53v25"/>`
  };
  function visual(story,cls='') {
    if(story.photo) return `<figure class="india-photo ${cls}"><img src="${escape(story.photo.url)}" alt="${escape(story.photo.alt)}" loading="lazy" data-news-image><figcaption>${escape(story.photo.credit)} <a href="${escape(story.photo.source)}" target="_blank" rel="noopener noreferrer">Source ↗</a></figcaption></figure>`;
    return `<div class="india-art ${escape(story.art)} ${cls}" aria-label="Illustration: ${escape(story.category)}" role="img"><span class="art-location">${escape(story.place)}</span><svg viewBox="0 0 360 250" aria-hidden="true"><g>${illustrations[story.art]||illustrations.economy}</g></svg><span class="art-caption">Editorial illustration</span></div>`;
  }
  function card(story,lens='alignment') {
    return `<article class="india-story-card">${visual(story)}<div class="india-card-content"><div class="india-card-meta"><span>${escape(story.category)} <i>·</i> ${escape(story.date)}</span><a href="${path(story.id)}">${story.reports.length} reviewed ${story.reports.length===1?'report':'reports'} ↗</a></div><h3><a href="${path(story.id)}">${escape(story.title)}</a></h3><p>${escape(story.dek)}</p><div class="india-card-coverage"><div class="india-bar-label"><span>${lens==='alignment'?'Toward India’s central government':'What leads the coverage'}</span><span>Reviewed sample</span></div>${bar(story,lens)}${legend(story,lens)}</div>${sourceBadges(story,lens)}<a class="india-compare-link" href="${path(story.id)}">Compare reporting <span aria-hidden="true">→</span></a></div></article>`;
  }
  function sourceBadges(story,lens='alignment') {
    const labels={opposition:'Opposition / critical',mixed:'Mixed',ruling:'Ruling / official',unclear:'Unclear',rights:'Rights & scrutiny',context:'Context',official:'Official response'};
    return `<div class="india-source-preview"><div class="india-source-preview-label"><span>${lens==='alignment'?'Sources & framing':'Sources & focus'}</span><span>Tap to see why ↗</span></div><div class="india-source-badges">${story.reports.map(report=>{const group=groups[lens].find(g=>g.id===report[lens]);return `<a class="india-source-chip" href="${path(story.id)}#${escape(report.id)}" aria-label="${escape(report.publisher)}: ${escape(group.label)}. Read the assessment" title="${escape(report.why)}"><span class="india-chip-mark ${group.tone}" aria-hidden="true">${escape(report.initials)}</span><span class="india-chip-copy"><strong>${escape(report.publisher)}</strong><span><i class="${group.tone}"></i>${escape(labels[group.id])}</span></span></a>`;}).join('')}</div></div>`;
  }
  const sourceFor = (story,id) => story.reports.find(report=>report.id===id);
  function sourceLink(story,item,label='Source ↗') {
    const url=item.url||sourceFor(story,item.source)?.url;
    return url?`<a href="${escape(url)}" target="_blank" rel="noopener noreferrer">${escape(label)}</a>`:'';
  }
  return {escape,groups,get,path,counts,bar,legend,visual,card,sourceBadges,sourceFor,sourceLink};
})();
