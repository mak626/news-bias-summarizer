// A transparent, local intent router demonstrating a schema-driven generative UI.
// Production can supply the same lens/article schema from the analysis backend.
const intentRules = [
  ['language', /language|hindi|english|tamil|malayalam|linguistic|regional/i],
  ['government', /government|alignment|scrutini|administration/i],
  ['ownership', /owner|corporate|independent|fund|media group/i],
  ['emotion', /emotion|anger|fear|sensational|outrage|tone|intensity/i],
  ['gaps', /gap|omit|omission|missing context|not covered|blind spot/i],
  ['evidence', /evidence|proof|document|claim|verify|fact|citation/i],
  ['people', /people|person|voices|resident|expert|stakeholder|who/i],
  ['political', /politic|party|policy|framing|bias|support|critical/i]
];
const intentPanel = document.createElement('div');
intentPanel.innerHTML = `<div class="intent-box"><div class="intent-caption"><strong>What would you like to compare?</strong></div><form class="intent-form" id="intent-form"><input id="intent-input" aria-label="What perspective would you like to explore?" placeholder="What’s missing from this story?" maxlength="180"><button type="submit">Explore</button></form><div class="intent-presets"><button data-intent="Whose voices lead the coverage?">Whose voices?</button><button data-intent="Show Hindi and English coverage">Language mix</button><button data-intent="Show the evidence quality">Check evidence</button></div></div><p class="intent-status" id="intent-status" role="status"></p>`;
document.querySelector('.lens-heading').after(intentPanel);
function applyIntent(query){
  const match = intentRules.find(([,rule]) => rule.test(query));
  if(!query.trim()) { document.querySelector('#intent-status').textContent='Ask about framing, people, language, ownership, government, emotion, coverage gaps, or evidence.'; return; }
  if(!match) { document.querySelector('#intent-status').textContent='This demo recognises eight lenses. Try “missing voices”, “coverage gaps”, or “government framing”.'; return; }
  chooseLens(match[0]);
  document.querySelector('#intent-status').innerHTML = `<strong>${esc(lens().title)}</strong> · ${selectedMedia().length} articles`;
  document.querySelector('#intent-input').value=query;
}
document.querySelector('#intent-form').addEventListener('submit',e=>{e.preventDefault();applyIntent(document.querySelector('#intent-input').value);});
document.addEventListener('click',e=>{const button=e.target.closest('button');if(button?.dataset.intent)applyIntent(button.dataset.intent);});
document.addEventListener('error',e=>{if(e.target instanceof HTMLImageElement){const img=e.target;img.hidden=true;img.parentElement.classList.add('image-unavailable');}},true);
