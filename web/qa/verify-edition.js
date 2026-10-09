// Run with macOS JavaScriptCore from the repository root:
// /System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc web/qa/verify-edition.js
var window=globalThis;
function assert(condition,message){if(!condition)throw new Error(message);}
load('web/dist/news-data.js');
load('web/dist/india-components.js');
const ui=IndiaCoverage;
assert(indiaEdition.stories.length===8,'Expected eight sourced stories');
assert(indiaEdition.stories[3].id==='starlink-india','Starlink must be the fourth story');
const ids=new Set(),reportIds=new Set();
for(const story of indiaEdition.stories){
  assert(!ids.has(story.id),'Duplicate story id');ids.add(story.id);
  assert(story.reports.length>0,`${story.id}: no reports`);
  assert(new Set(story.reports.map(r=>r.origin)).size===story.reports.length,`${story.id}: syndicated duplicates inflate the count`);
  for(const report of story.reports){
    assert(!reportIds.has(report.id),'Duplicate report id');reportIds.add(report.id);
    assert(/^https:\/\//.test(report.url),`${report.id}: missing source URL`);
    assert(report.evidence&&report.why&&report.access,`${report.id}: missing assessment evidence`);
    assert(ui.groups.alignment.some(g=>g.id===report.alignment),`${report.id}: invalid party framing`);
    assert(ui.groups.focus.some(g=>g.id===report.focus),`${report.id}: invalid coverage focus`);
  }
  for(const claim of story.claims)assert(ui.sourceFor(story,claim.source),`${story.id}: broken claim reference`);
  for(const perspective of story.perspectives)assert(perspective.url||ui.sourceFor(story,perspective.source),`${story.id}: broken perspective reference`);
  for(const lens of ['alignment','focus']){
    assert(ui.counts(story,lens).reduce((total,g)=>total+g.count,0)===story.reports.length,`${story.id}: wrong bar total`);
    const html=ui.card(story,lens);
    assert(html.includes(ui.path(story.id))&&!/undefined|NaN/.test(html),`${story.id}: broken card`);
    for(const report of story.reports)assert(html.includes(`${ui.path(story.id)}#${report.id}`),`${report.id}: missing source assessment link`);
  }
}
assert(ui.counts(ui.get('delhi-protest')).find(g=>g.id==='ruling').count===1,'Protest ruling-side count');
assert(ui.counts(ui.get('delhi-protest')).find(g=>g.id==='opposition').count===1,'Protest opposition-side count');
assert(ui.get('us-green-cards').reports.every(r=>!['ruling','opposition'].includes(r.alignment)),'Visa story should not invent party alignment');
assert(ui.get('saudi-advisory').reports.every(r=>!['ruling','opposition'].includes(r.alignment)),'Saudi story should not invent party alignment');

// A minimal DOM exercises actual render/event handlers without third-party dependencies.
function createDocument(){
  const nodes={};
  function node(selector){return nodes[selector]||(nodes[selector]={innerHTML:'',textContent:'',listeners:{},addEventListener(type,handler){this.listeners[type]=handler;},setAttribute(){},scrollIntoView(){}});}
  return {nodes,querySelector:node,querySelectorAll(){return [];},title:''};
}
var document,location,navigator={};
var URLSearchParams=class{constructor(query){this.query=query;}get(key){const match=this.query.match(new RegExp('[?&]'+key+'=([^&]*)'));return match?decodeURIComponent(match[1]):null;}};
function click(target,dataset,panel=false){target.listeners.click({target:{closest(){return {dataset,id:'',closest(){return panel?{}:null;}};}}});}
for(const story of indiaEdition.stories){
  document=createDocument();location={search:'?id='+story.id,href:'http://localhost:4173/'+ui.path(story.id)};
  load('web/dist/story.js');
  const root=document.querySelector('#story-page');
  assert(root.innerHTML.includes(story.title),`${story.id}: detail title missing`);
  assert(document.querySelector('#report-count').textContent===`${story.reports.length} of ${story.reports.length} reports`,`${story.id}: initial detail count`);
  for(const lens of ['alignment','focus']){
    click(root,{storyLens:lens});
    for(const group of ui.groups[lens]){
      click(root,{reportFilter:group.id},true);
      const expected=story.reports.filter(r=>r[lens]===group.id);
      const html=document.querySelector('#report-list').innerHTML;
      assert(document.querySelector('#report-count').textContent===`${expected.length} of ${story.reports.length} reports`,`${story.id}: wrong filtered count`);
      if(!expected.length)assert(html.includes('No assessed reports in this group'),`${story.id}: missing empty state`);
      for(const report of story.reports)assert(html.includes(`id="${report.id}"`)===expected.includes(report),`${story.id}: incorrect report in filter`);
    }
    click(root,{reportFilter:'all'});
  }
}
document=createDocument();location={search:'?id=unknown'};load('web/dist/story.js');
assert(document.querySelector('#story-page').innerHTML.includes('Story not found'),'Unknown story fallback');
document=createDocument();location={};load('web/dist/news.js');
assert(document.querySelector('#india-result-count').textContent==='8 stories','Initial feed count');
click(document.querySelector('#india-controls'),{indiaCategory:'Economy'});
assert(document.querySelector('#india-result-count').textContent==='4 stories','Economy filter count');
click(document.querySelector('#india-controls'),{indiaCategory:'Narendra Modi'});
assert(document.querySelector('#india-result-count').textContent==='1 story','Narendra Modi topic count');
click(document.querySelector('#india-controls'),{indiaCategory:'All'});
document.querySelector('#india-search').listeners.input({target:{value:'Saudi'}});
assert(document.querySelector('#india-result-count').textContent==='1 story','Search result count');
document.querySelector('#india-search').listeners.input({target:{value:'no match'}});
assert(document.querySelector('#news-grid').innerHTML.includes('No stories match'),'Search empty state');
for(const file of ['app.js','news-data.js','india-components.js','news.js','story.js','theme.js','adaptive.js'])new Function(readFile('web/dist/'+file));
print(`PASS: ${ids.size} stories, ${reportIds.size} source reports; both lenses, every filter, search, invalid route and JavaScript syntax verified.`);
