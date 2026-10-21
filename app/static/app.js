const headers = {"Content-Type":"application/json", "X-API-Key":"demo-key"};
const pretty = (v) => JSON.stringify(v, null, 2);
async function createCase(){
  const r = await fetch('/api/cases',{method:'POST',headers,body:JSON.stringify({external_ref:ref.value,title:title.value})});
  caseOut.textContent=pretty(await r.json());
}
async function ingest(){
  const r = await fetch(`/api/cases/${caseId.value}/documents`,{method:'POST',headers,body:JSON.stringify({filename:filename.value,text:docText.value})});
  docOut.textContent=pretty(await r.json());
}
async function ask(){
  const r = await fetch(`/api/cases/${caseId.value}/answer`,{method:'POST',headers,body:JSON.stringify({question:question.value,limit:6})});
  answerOut.textContent=pretty(await r.json());
}
