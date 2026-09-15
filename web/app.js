'use strict';

const ACTIONS = ['search', 'open-lesson', 'open-decoy', 'study', 'answer-a', 'answer-b', 'answer-c', 'answer-d', 'back'];
const PAGE_INPUTS = {
  library: ['visual_sensory', 'central_other'], results: ['visual_sensory', 'central_complex'],
  lesson: ['learning_memory', 'central_other'], decoy: ['other_sensory'],
  quiz: ['learning_memory', 'central_complex'], result: ['descending', 'motor_efferent']
};
const DOMAIN_INPUT = {
  science: 'other_sensory', math: 'central_complex', ai: 'learning_memory',
  physics: 'visual_processing', philosophy: 'central_other', literature: 'visual_sensory', 'self-model': 'central_other'
};
const state = {task:0, page:'library', history:[], studied:false, done:false, passed:false, reward:0, step:0};
let graph, graphs, curriculum, policy, internetPage, running=false, watching=false;

const $ = id => document.getElementById(id);
const log = text => { $('log').textContent = `${text}\n${$('log').textContent}`.slice(0,9000); };
const say = text => { $('speech').textContent = text; };
const task = s => curriculum[s.task];
const esc = value => String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function blank(taskIndex=state.task){return {task:taskIndex,page:'library',history:[],studied:false,done:false,passed:false,reward:0,step:0};}
function resetState(render=true){Object.assign(state,blank());if(render){renderPage();updateTelemetry();}}

function taskSignal(t, length){
  const x=new Float64Array(length);let h=2166136261;
  for(const c of `${t.domain}:${t.title}:${t.id||t.source}:${t.question}`){h^=c.charCodeAt(0);h=Math.imul(h,16777619);}
  for(let i=0;i<length;i++){h=Math.imul(h^i,2246822519);x[i]=.04+((h>>>0)%100)/900;}
  return x;
}
function rawInput(s){
  const x=taskSignal(task(s),graph.groups.length);
  const excite=(name,value=1)=>{const i=graph.groups.indexOf(name);if(i>=0)x[i]+=value;};
  for(const name of PAGE_INPUTS[s.page])excite(name);
  excite(DOMAIN_INPUT[task(s).domain],.55);
  if(s.studied)excite('learning_memory',.75);
  excite('modulatory_endocrine',.25);
  return x;
}
function encode(s,topology=graph.weights,permutation=null){
  let x=rawInput(s);if(permutation){const moved=new Float64Array(x.length);for(let i=0;i<x.length;i++)moved[permutation[i]]=x[i];x=moved;}
  const original=x.slice();
  for(let hop=0;hop<4;hop++){const next=new Float64Array(x.length);for(let i=0;i<x.length;i++)for(let j=0;j<x.length;j++)next[j]+=x[i]*topology[i][j];for(let j=0;j<x.length;j++)x[j]=Math.tanh(.55*original[j]+1.8*next[j]);}
  return x;
}

function transition(s,action){
  const n={...s,history:[...s.history]};let reward=-.2,note='action had no useful effect';
  const go=page=>{n.history.push(n.page);n.page=page;};
  if(s.page==='library'&&action===0){go('results');reward=.5;note='searched local curriculum';}
  else if(s.page==='results'&&action===1){go('lesson');reward=1;note='opened attributed lesson';}
  else if(s.page==='results'&&action===2){go('decoy');reward=-1;note='opened irrelevant result';}
  else if(s.page==='lesson'&&action===3){go('quiz');n.studied=true;reward=2;note='encoded lesson then opened quiz';}
  else if(s.page==='quiz'&&action>=4&&action<=7){const choice=action-4;n.done=true;n.page='result';n.passed=choice===task(s).answer;reward=n.passed?10:-3;note=n.passed?'answer verified':'answer rejected';}
  else if(action===8&&n.history.length){n.page=n.history.pop();reward=0;note='went back';}
  n.reward+=reward;n.step+=1;
  if(n.step>=10&&!n.done){n.done=true;n.passed=false;reward-=2;n.reward-=2;note+='; timed out';}
  return {next:n,reward,note};
}

function seeded(seed){return()=>{seed=(seed+0x6D2B79F5)|0;let t=Math.imul(seed^(seed>>>15),1|seed);t=(t+Math.imul(t^(t>>>7),61|t))^t;return((t^(t>>>14))>>>0)/4294967296;};}
function makePolicy(seed=7){return{table:new Map(),rnd:seeded(seed)};}
function featureKey(f){return Array.from(f,x=>x.toFixed(4)).join(',');}
function qRow(p,f){const key=featureKey(f);if(!p.table.has(key))p.table.set(key,Float64Array.from({length:ACTIONS.length},()=>(p.rnd()-.5)*.002));return p.table.get(key);}
function qValues(p,f){return Array.from(qRow(p,f));}
function argmax(xs){let b=0;for(let i=1;i<xs.length;i++)if(xs[i]>xs[b])b=i;return b;}
function identityGraph(){return graph.weights.map((r,i)=>r.map((_,j)=>i===j?1:0));}
function permutation(seed=11){const a=[...Array(graph.groups.length).keys()],r=seeded(seed);for(let i=a.length-1;i;i--){const j=Math.floor(r()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}

function curriculumScore(p,topology,perm,indices){
  let passed=0;
  for(const ti of indices){const s=blank(ti);if(task(s).blinded)s.page='quiz';while(!s.done){const a=argmax(qValues(p,encode(s,topology,perm)));Object.assign(s,transition(s,a).next);}if(s.passed)passed++;}
  return passed;
}
function train(topology,perm=null,episodes=4000,seed=7){
  const p=makePolicy(seed),rnd=seeded(seed+99),starts=['library','results','lesson','quiz'],trainingIndices=curriculum.map((t,i)=>({t,i})).filter(x=>!x.t.blinded).map(x=>x.i),probeIndices=curriculum.map((t,i)=>({t,i})).filter(x=>x.t.blinded).map(x=>x.i);let firstAll=null;
  for(let ep=0;ep<episodes;ep++){
    const ti=trainingIndices[ep%trainingIndices.length],stage=starts[Math.floor(ep/trainingIndices.length)%starts.length];
    const s=blank(ti);s.page=stage;s.studied=stage==='quiz';
    while(!s.done){const f=encode(s,topology,perm),qs=qValues(p,f),epsilon=Math.max(.03,.4*(1-ep/episodes));const a=rnd()<epsilon?Math.floor(rnd()*ACTIONS.length):argmax(qs);const {next,reward}=transition(s,a),nf=encode(next,topology,perm),target=reward+(next.done?0:.92*Math.max(...qValues(p,nf))),error=Math.max(-4,Math.min(4,target-qs[a]));qRow(p,f)[a]+=.09*error;Object.assign(s,next);}
    if(firstAll===null&&ep%200===199&&curriculumScore(p,topology,perm,trainingIndices)===trainingIndices.length)firstAll=ep+1;
  }
  return {policy:p,score:curriculumScore(p,topology,perm,trainingIndices),total:trainingIndices.length,probeScore:curriculumScore(p,topology,perm,probeIndices),probeTotal:probeIndices.length,firstAll};
}

function renderPage(){
  if(watching){renderInternetPage();return;}
  const t=task(state);$('address').textContent=`sandbox://curriculum/${t.domain}/${state.page}`;$('task').textContent=`Goal: study “${t.title}” and answer its graded question.`;
  const options=t.options.map((o,i)=>`<button class="answer" data-action="${4+i}">${'ABCD'[i]}. ${esc(o)}</button>`).join('');
  const pages={
    library:`<h1>Gnat Academy</h1><p>Local curriculum index: science · mathematics · AI · physics · philosophy · literature.</p><input aria-label="Search" value="${state.step?esc(t.title):''}" placeholder="Search one lesson"><button data-action="0">Search curriculum</button>`,
    results:`<h1>Results for “${esc(t.title)}”</h1><div class="result"><a data-action="1">${esc(t.title)} — attributed lesson</a><p>${esc(t.source)} · ${t.web_derived?'untrusted web-derived memory':'curated local excerpt'}</p></div><div class="result"><a data-action="2">Opinion thread with no lesson</a><p>irrelevant.test · decoy fixture</p></div>`,
    lesson:`<h1>${esc(t.title)}</h1><p>${esc(t.lesson)}</p><p><small>Source label: ${esc(t.source)}. ${t.web_derived?'Self-supervised reconstruction fixture; source truth is not verified.':'Bundled local teaching fixture.'}</small></p><button data-action="3">Study and take quiz</button>`,
    decoy:`<h1>Unverified tangent</h1><p>This page does not contain the lesson.</p><button data-action="8">Go back</button>`,
    quiz:`<h1>Checkpoint</h1><p>${esc(t.question)}</p><div class="answers">${options}</div>`,
    result:`<h1>${state.passed?'Verified ✓':'Incorrect ✗'}</h1><p>${state.passed?'The deterministic grader accepted the answer.':`Correct answer: ${'ABCD'[t.answer]}. ${esc(t.options[t.answer])}`}</p><p>Episode return: <b>${state.reward.toFixed(1)}</b></p>`
  };
  $('page').innerHTML=pages[state.page];$('page').querySelectorAll('[data-action]').forEach(el=>el.onclick=()=>manual(+el.dataset.action));
}
function renderInternetPage(){
  const p=internetPage||{};$('address').textContent=p.url||'sandbox://real-web/waiting';$('task').textContent='LIVE: connectome-featured bandit selected this read-only page; text is untrusted and sanitized.';
  const links=(p.links||[]).slice(0,12).map(x=>`<li>${esc(x)}</li>`).join('');
  $('page').innerHTML=`<div class="live-badge">LIVE REAL WEB · READ ONLY</div><h1>${esc(p.title||'Waiting for next page')}</h1><p><b>subject:</b> ${esc(p.domain||'—')}</p><pre class="web-excerpt">${esc(p.excerpt||'The explorer has not produced a preview yet.')}</pre><h2>candidate links</h2><ul class="candidate-links">${links||'<li>none yet</li>'}</ul>`;
}
function updateTelemetry(){
  $('reward').textContent=state.reward.toFixed(1);$('step').textContent=state.step;$('success').textContent=state.done?(state.passed?'YES':'NO'):'—';if(graph)drawBrain(encode(state));
}
function animateFly(s){
  const body=document.querySelector('.fly-body');if(!body)return;
  const a=s.affect_proxies||{},arousal=Math.max(0,Math.min(1,+a.arousal||0)),novelty=Math.max(0,Math.min(1,+a.novelty_drive||0));
  body.style.setProperty('--buzz',`${Math.max(.055,.24-arousal*.17).toFixed(3)}s`);
  body.style.transform=`translate(${(novelty*10).toFixed(1)}px,${(-arousal*7).toFixed(1)}px) rotate(${(-10+(+s.prediction_error||0)*3).toFixed(1)}deg)`;
  $('fly-stage').style.boxShadow=`inset 0 0 ${8+arousal*24}px rgba(166,226,46,${.08+novelty*.28})`;
}
function applyAction(a){const out=transition(state,a);Object.assign(state,out.next);log(`step ${state.step}: ${ACTIONS[a]} | r=${out.reward.toFixed(1)} | ${out.note}`);say(a===0?'find lesson.':a===1?'source looks useful.':a===2?'noise. go back.':a===3?'store pattern. take test.':a>=4&&a<=7?`choose ${'ABCD'[a-4]}. grader decides.`:'backtrack.');renderPage();updateTelemetry();return out;}
function manual(a){if(!running)applyAction(a);}
async function runLearned(){if(!policy||running)return;watching=false;$('watch').textContent='Watch real web';running=true;resetState(false);if(task(state).blinded)state.page='quiz';renderPage();updateTelemetry();log(`evaluation: ${task(state).domain} / ${task(state).title}${task(state).blinded?' · HELD OUT':''}`);while(!state.done){const a=argmax(qValues(policy,encode(state)));applyAction(a);await new Promise(r=>setTimeout(r,500));}say(task(state).blinded?(state.passed?'held-out probe happened to pass; aggregate controls determine meaning.':'held-out probe failed; no self-inference is demonstrated.'):(state.passed?'checkpoint passed. i memorized this fixture; i did not understand all science.':'checkpoint failed. training or representation was insufficient.'));running=false;}

function drawBrain(activity){
  const c=$('brain'),ctx=c.getContext('2d'),W=c.width,H=c.height;ctx.clearRect(0,0,W,H);ctx.fillStyle='#060c09';ctx.fillRect(0,0,W,H);
  const column=name=>name.includes('sensory')||['olfactory','gustatory','mechanosensory','thermo_hygro'].includes(name)?0:['visual_processing','learning_memory','central_complex','central_other'].includes(name)?1:['descending','ascending','vnc_intrinsic'].includes(name)?2:3;
  const pos=graph.groups.map(name=>{const region=column(name),members=graph.groups.filter(x=>column(x)===region),k=members.indexOf(name);return{x:55+region*165,y:25+(k+1)*(310/(members.length+1))};});
  const edges=[];for(let i=0;i<graph.weights.length;i++)for(let j=0;j<graph.weights.length;j++){const w=Math.abs(graph.weights[i][j]);if(w>.055)edges.push([w,i,j]);}edges.sort((a,b)=>b[0]-a[0]);ctx.lineWidth=.7;for(const[,i,j]of edges.slice(0,170)){ctx.strokeStyle=graph.weights[i][j]<0?'#a8555555':'#2f855a55';ctx.beginPath();ctx.moveTo(pos[i].x,pos[i].y);ctx.lineTo(pos[j].x,pos[j].y);ctx.stroke();}
  for(let i=0;i<pos.length;i++){const a=Math.min(1,Math.abs(activity[i])*3),p=pos[i];ctx.beginPath();ctx.arc(p.x,p.y,3+a*6,0,Math.PI*2);ctx.fillStyle=`rgba(${80+Math.round(a*150)},${140+Math.round(a*100)},90,${.45+a*.55})`;ctx.fill();}
  ctx.fillStyle='#7aa58d';ctx.font='11px monospace';['SENSORY','CENTRAL','PATHWAYS','MOTOR / MOD'].forEach((x,i)=>ctx.fillText(x,15+i*165,14));
}

function trainSelected(){
  watching=false;$('watch').textContent='Watch real web';renderPage();const trainable=curriculum.filter(t=>!t.blinded).length,episodes=Math.max(4000,trainable*400);log(`training ${trainable} learnable memories; ${curriculum.length-trainable} probes withheld...`);const main=train(graph.weights,null,episodes),shuffled=train(graph.weights,permutation(),episodes),identity=train(identityGraph(),null,episodes);policy=main.policy;$('run').disabled=false;
  const fmt=x=>`${x.score}/${x.total} trained checkpoints; held-out self-model ${x.probeScore}/${x.probeTotal}; all-trained episode ${x.firstAll??'never'}`;
  log(`CONTROL no propagation: ${fmt(identity)}\nCONTROL shuffled labels: ${fmt(shuffled)}\n${graph.dataset}: ${fmt(main)}`);say('training done. self-model probes were withheld from learning.');
}
function neuronCount(g){return g.retained_neurons??g.source_neurons;}
function edgeCount(g){return g.kept_signed_edge_pairs??g.source_edges;}
function selectGraph(sex){graph=graphs[sex];policy=null;running=false;$('run').disabled=true;$('dataset').textContent=`${graph.dataset} · ${neuronCount(graph).toLocaleString()} nodes → 16 groups`;$('sex-pill').textContent=`${sex} controller · sandbox`;resetState();say(`loaded ${neuronCount(graph).toLocaleString()} ${sex} graph records.`);log(`${graph.dataset}: ${edgeCount(graph).toLocaleString()} retained edge pairs; retrain required`);}
function fillTasks(){
  const domain=$('domain').value,items=curriculum.map((t,i)=>({t,i})).filter(x=>domain==='all'||x.t.domain===domain);$('lesson').innerHTML=items.map(x=>`<option value="${x.i}">${esc(x.t.title)}</option>`).join('');state.task=items[0].i;resetState();
}

$('train').onclick=trainSelected;$('run').onclick=runLearned;$('watch').onclick=()=>{watching=!watching;$('watch').textContent=watching?'Back to curriculum':'Watch real web';renderPage();};$('reset').onclick=()=>{running=false;watching=false;$('watch').textContent='Watch real web';resetState();say('reset.');log('reset');};$('back').onclick=()=>watching?$('watch').click():manual(8);
$('sex').onchange=e=>selectGraph(e.target.value);$('domain').onchange=fillTasks;$('lesson').onchange=e=>{state.task=+e.target.value;resetState();};
$('talk-send').onclick=async()=>{const input=$('talk-input'),message=input.value.trim();if(!message)return;$('talk-output').textContent='thinking locally…';$('talk-send').disabled=true;try{const response=await fetch('/api/talk',{method:'POST',headers:{'Content-Type':'application/json','X-Nerdy-Fly':'dashboard'},body:JSON.stringify({message})});const body=await response.json();if(!response.ok)throw Error(body.error||response.status);$('talk-output').textContent=body.reply;input.value='';}catch(e){$('talk-output').textContent=`talk unavailable: ${e.message}`;}finally{$('talk-send').disabled=false;}};
$('talk-input').onkeydown=e=>{if(e.key==='Enter')$('talk-send').click();};
Promise.all([
  fetch('data/male_common_graph.json').then(r=>r.json()),fetch('data/female_common_graph.json').then(r=>r.json()),fetch('data/curriculum.json').then(r=>r.json()),fetch('data/discovered_lessons.json').then(r=>r.ok?r.json():[]),fetch('data/self_model_probes.json').then(r=>r.json())
]).then(([male,female,lessons,discovered,probes])=>{graphs={male,female};curriculum=[...lessons,...probes,...discovered];fillTasks();selectGraph('male');log(`${probes.length} blinded self-model probes + ${discovered.length} web-derived reconstruction memories loaded`);}).catch(e=>say(`environment failed: ${e.message}`));

async function refreshInternetStatus(){
  try{const stamp=Date.now(),responses=await Promise.all([fetch(`data/internet_status.json?t=${stamp}`),fetch(`data/internet_page.json?t=${stamp}`),fetch(`data/mock_mailbox.json?t=${stamp}`),fetch(`data/reasoning_status.json?t=${stamp}`)]);if(!responses[0].ok)throw Error(responses[0].status);const s=await responses[0].json(),el=$('internet');if(responses[1].ok)internetPage=await responses[1].json();el.classList.toggle('live',!!s.running);const values=Object.entries(s.learned_domain_values||{}).map(([k,v])=>`${k}:${v}`).join(' ');el.textContent=`real web ${s.running?'LIVE':'stopped'} · ${s.pages??0} pages · ${s.vocabulary??0} words · last ${s.domain??'—'} reward ${s.reward??'—'} · ${s.url??'no page yet'}${values?' · values '+values:''}`;$('decision').textContent=`step ${s.step??'—'} · ${s.decision_mode??'—'} · epsilon ${s.epsilon??'—'}\nselected ${s.domain??'—'} · predicted ${s.predicted_reward??'—'} · observed ${s.reward??'—'} · TD error ${s.prediction_error??'—'}\ncandidate values ${JSON.stringify(s.candidate_values||{})}\nconnectome features ${JSON.stringify(s.connectome_features||[])}`;const contract=s.autonomy_contract||{},autonomy=$('autonomy'),clean=contract.external_model_calls===0&&contract.operator_action_calls===0&&contract.host_code_execution===false;autonomy.classList.toggle('ok',clean);autonomy.innerHTML=`<strong>AUTONOMY ${clean?'VERIFIED':'CHECK'}</strong> · ${esc(contract.runtime||'unknown')} · model calls ${esc(contract.external_model_calls??'—')} · operator actions ${esc(contract.operator_action_calls??'—')} · host exec ${esc(contract.host_code_execution??'—')}<br>${esc(contract.controller_scope||'scope unavailable')}`;animateFly(s);const affect=Object.entries(s.affect_proxies||{});$('affect').innerHTML=affect.map(([name,value])=>`<div class="affect-item"><span>${esc(name.replaceAll('_',' '))}</span><div class="affect-track"><div class="affect-fill" style="width:${Math.max(0,Math.min(100,+value*100))}%"></div></div></div>`).join('')+`<div class="affect-note">${esc(s.affect_caveat||'')}</div>`;if(responses[2].ok){const messages=await responses[2].json();$('mailbox').innerHTML=messages.slice(-8).reverse().map(m=>`<article class="message"><b>${esc(m.subject)}</b><span>${esc(m.from)} → ${esc(m.to)} · ${esc(m.time)}</span><p>${esc(m.body)}</p></article>`).join('')||'No reports yet.';}if(responses[3].ok){const r=await responses[3].json();$('reasoning').innerHTML=`<b>${esc(r.model||'local model')}</b> · ${esc(r.running?'LIVE':'stopped')} · exact score ${esc(r.score??0)}/${esc(r.evaluated??0)} (${esc(r.accuracy??'—')})<br>${esc(r.summary||r.error||'waiting for first reflection')}<br><b>question:</b> ${esc(r.question||'—')}<br><span>${esc(r.attribution||'')}</span>`;if(r.speech)say(r.speech);}if(watching)renderInternetPage();}
  catch{$('internet').textContent='real-web explorer has not been started';}
}
refreshInternetStatus();setInterval(refreshInternetStatus,5000);
