/* API-only data client. No editorial/story fixtures live in the web bundle. */
window.NewsApi = (() => {
  const base = window.NEWS_API_BASE || (location.port === '8000' ? '' : `http://${location.hostname||'127.0.0.1'}:8000`);
  let editionPromise;
  let labPromise;

  async function get(path) {
    const response = await fetch(`${base}${path}`, {headers:{Accept:'application/json'}});
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
  }

  function indiaStory(item) {
    const image=item.image;
    return {
      id:item.id, category:item.category, topics:item.topics||[], place:item.place, date:item.date,
      title:item.title, dek:item.description, summary:item.summary, read:item.reading_time,
      takeaway:item.takeaway, art:image.kind,
      photo:{url:image.url,alt:image.alt,credit:image.credit,source:image.source_url||image.url},
      primary:item.primary_document,
      gaps:item.open_questions||[],
      claims:(item.claims||[]).map(x=>({status:x.status,text:x.text,source:x.report_id,url:x.source_url})),
      perspectives:(item.perspectives||[]).map(x=>({title:x.title,text:x.text,source:x.report_id,url:x.source_url})),
      reports:item.reports||[]
    };
  }

  async function loadEdition() {
    if (!editionPromise) editionPromise=(async()=>{
      const payload=await get('/api/v1/edition/content');
      const meta=payload.edition;
      window.indiaEdition={checked:meta.checked,through:meta.through,meta,stories:payload.stories.map(indiaStory)};
      return window.indiaEdition;
    })();
    return editionPromise;
  }

  async function loadLab() {
    if (!labPromise) labPromise=(async()=>{
      const payload=await get('/api/v1/lab/content');
      return {meta:payload.lab,stories:payload.stories};
    })();
    return labPromise;
  }

  return {base,get,loadEdition,loadLab};
})();
