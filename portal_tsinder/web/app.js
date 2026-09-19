"use strict";
const $ = id => document.getElementById(id);
let token = "", currentView = "overview";
const presets = {
  evaluate: [{}, "M04: геометрия, stress-energy, приливные нагрузки и независимые gates."],
  geodesic: [{a:1,start_l:-5,beta:0.6,angular_fraction:0,kind:"timelike",duration:20,steps:2000}, "Геодезическая в фиксированной метрике. Обратная реакция payload не включена."],
  wave: [{model:"M04",points:201,extent:10,duration:6,ell:0,damping:0,cfl:0.5,initial:"gaussian"}, "Линейное тестовое поле; отражающие границы. Не нелинейная эволюция пространства-времени."],
  wave_convergence: [{}, "Три сетки; точное решение волнового уравнения на плоском фоне."],
  quantum: [{theta:1.1,phi:0.7,depolarizing:0}, "Полный трёхкубитный протокол. Требуются два классических бита; материю не переносит."],
  qei: [{tau0_s:1e-6}, "Только свободное безмассовое скалярное поле, Minkowski, Lorentzian sampling."],
  qei_pulse: [{rho:-1e-40,half_duration_s:1e-6,tau0_s:1e-6}, "Сравнение назначенного импульса с частной QEI; не построение квантового состояния."],
  control: [{duration_s:30,target:0.4}, "Детерминированная симуляция PID и обычного колебательного аналога."],
  transmission_line: [{frequencies:[1000000,2000000,3000000,4000000,5000000],length_m:1,L_H_m:2.5e-7,C_F_m:1e-10,R_ohm_m:0.1}, "Пассивная RLGC линия: S21, фаза, групповая задержка."],
  metrology: [{csv_text:"frequency_hz,s21_real,s21_imag\n1000000,0.99950656,-0.03141076\n2000000,0.99802673,-0.06279052\n3000000,0.99556196,-0.09410831\n"}, "Импорт CSV. Данные примера синтетические; для реальных измерений замените trace."],
  nr_constraints: [{text:"resolution_h,H_L2,M_L2\n0.1,0.01,0.02\n0.05,0.0025,0.005\n0.025,0.000625,0.00125\n"}, "Анализ внешних норм. Пример синтетический; не Einstein Toolkit solver."],
  causal_graph: [{nodes:["A","B"],edges:[{from:"A",to:"B",time_s:-2},{from:"B",to:"A",time_s:1}]}, "Поиск отрицательного цикла в конечном графе; не доказательство глобальной причинности."],
  worldline: [{samples:[[0,0,0,0],[1,1000,0,0],[2,2000,0,0]]}, "Кусочно-инерциальное интегрирование собственных часов."],
  symbolic: [{model:"M04"}, "Вывод Christoffel, Ricci и Einstein из метрики; проверка contracted Bianchi. Может занять несколько секунд."]
};
async function api(path, options={}) {
  const response = await fetch(path, {...options,headers:{Authorization:`Bearer ${token}`, ...(options.body?{"Content-Type":"application/json"}:{}),...options.headers}});
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try { message = (await response.json()).detail || message; } catch (_) {}
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return response;
}
const get = async p => (await api(p)).json();
const post = async (p,b) => (await api(p,{method:"POST",body:JSON.stringify(b)})).json();
function error(e) { $("error").textContent=e.message||String(e); $("error").hidden=false; }
async function task(button, action) {
  $("error").hidden=true;
  if(button) button.disabled=true;
  try { return await action(); } catch(e) { error(e); } finally { if(button) button.disabled=false; }
}
function element(tag, text, className) {
  const node=document.createElement(tag);
  if(text!==undefined) node.textContent=String(text);
  if(className) node.className=className;
  return node;
}
function badge(text) { return element("span",text,`badge ${text}`); }
function table(container, headings, rows) {
  container.replaceChildren(); container.classList.remove("empty");
  const t=element("table"), head=element("thead"), tr=element("tr");
  headings.forEach(h=>tr.append(element("th",h))); head.append(tr); t.append(head);
  const body=element("tbody");
  rows.forEach(row=>{const r=element("tr"); row.forEach(v=>{const d=element("td"); d.append(v instanceof Node?v:document.createTextNode(String(v??"—")));r.append(d)});body.append(r)});
  t.append(body);container.append(t);
}
function fmt(v) { return typeof v==="number" ? (Math.abs(v)>1e5 || (Math.abs(v)<0.001&&v!==0) ? v.toExponential(4):Number(v.toPrecision(6)).toString()) : String(v); }
function metric(container, title, value) { const d=element("div",undefined,"metric");d.append(element("small",title),element("b",fmt(value)));container.append(d); }
function chart(container, rows, xKey, curves) {
  container.replaceChildren();container.classList.remove("empty");
  if(!rows.length){container.textContent="Нет данных";return;}
  const ns="http://www.w3.org/2000/svg",svg=document.createElementNS(ns,"svg");
  svg.setAttribute("viewBox","0 0 650 260");svg.setAttribute("role","img");svg.setAttribute("aria-label",`График ${curves.map(c=>c.label).join(', ')}`);
  const make=(tag,attrs,text)=>{const e=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));if(text!==undefined)e.textContent=text;svg.append(e);return e};
  const xs=rows.map(r=>r[xKey]); const ys=rows.flatMap(r=>curves.map(c=>r[c.key])).filter(Number.isFinite);
  if(!ys.length) return;
  const xmin=Math.min(...xs),xmax=Math.max(...xs);let ymin=Math.min(...ys),ymax=Math.max(...ys);
  const padding=(ymax-ymin||1)*.1;ymin-=padding;ymax+=padding;
  const X=x=>60+(x-xmin)/(xmax-xmin||1)*570,Y=y=>220-(y-ymin)/(ymax-ymin)*185;
  for(let i=0;i<5;i++){const y=ymin+i*(ymax-ymin)/4;make("line",{x1:60,y1:Y(y),x2:630,y2:Y(y),stroke:"#293b46"});make("text",{x:50,y:Y(y)+4,fill:"#819ba9","text-anchor":"end","font-size":10},fmt(y));}
  curves.forEach((curve,i)=>{make("polyline",{points:rows.filter(r=>Number.isFinite(r[curve.key])).map(r=>`${X(r[xKey])},${Y(r[curve.key])}`).join(" "),fill:"none",stroke:curve.color,"stroke-width":2});make("text",{x:60+i*180,y:16,fill:curve.color,"font-size":11},curve.label)});
  make("text",{x:60,y:245,fill:"#819ba9","font-size":10},fmt(xmin));make("text",{x:630,y:245,fill:"#819ba9","font-size":10,"text-anchor":"end"},`${fmt(xmax)} ${xKey}`);
  container.append(svg);
}
function displayEvaluation(run) {
  const r=run.result;$("geometry-status").textContent="FORMAL PASS";$("candidate-hash").textContent=run.input_sha.slice(0,16);
  for(const id of ["overview-chart","geometry-chart"])chart($(id),r.profile,"l_m",[{key:"r_m",color:"#77d6ca",label:"r(l), м"}]);
  const m=$("metrics");m.replaceChildren();metric(m,"Плотность в горловине, J/m³",r.diagnostics.throat_stress.rho_J_m3);metric(m,"NEC, J/m³",r.diagnostics.throat_stress.radial_NEC_J_m3);metric(m,"Безопасный reduced margin, s",r.causality.safe_margin_s);metric(m,"Приливное ускорение, m/s²",r.diagnostics.tidal.transverse_m_s2);
  table($("gates"),["ID","Проверка","Статус","Значение"],r.gates.map(g=>[g.gate_id,g.title,badge(g.status),g.value===null?"—":`${fmt(g.value)} ${g.unit||""}`]));
}
async function experiment(kind,parameters) { const run=await post("/api/runs",{kind,parameters});if(kind==="evaluate")displayEvaluation(run);await refreshCount();return run; }
async function refreshCount() { const runs=await get("/api/runs");$("run-count").textContent=runs.length+(runs.length===100?"+":"");return runs; }
function choosePreset(){const k=$("experiment-kind").value;$("experiment-config").value=JSON.stringify(presets[k][0],null,2);$("experiment-note").textContent=presets[k][1];}
async function view(name) {
  currentView=name;document.querySelectorAll(".view").forEach(s=>s.hidden=s.id!==name);
  document.querySelectorAll("nav button").forEach(b=>b.classList.toggle("active",b.dataset.view===name));
  $("page-title").textContent=document.querySelector(`[data-view="${name}"] span`).textContent;
  if(name==="registry"){
    const [models,layers]=await Promise.all([get("/api/catalog/models"),get("/api/catalog/layers")]);
    table($("models-table"),["ID","Модель","Реализация","Граница"],models.map(m=>[m.id,m.name,m.implementation,m.limitation]));
    table($("layers-table"),["ID","Слой","Модуль","Статус реализации"],layers.map(l=>[l.id,l.name,l.module,l.status]));
  }
  if(name==="audit")await audit();
  if(name==="control")await refreshController();
}
async function download(id,kind) {
  const response=await api(`/api/runs/${id}/${kind}`),blob=await response.blob(),url=URL.createObjectURL(blob);
  const a=element("a");a.href=url;a.download=`portal-${id}.${kind==="report"?"html":"zip"}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function audit(){
  const [runs,log]=await Promise.all([refreshCount(),get("/api/audit")]);
  $("audit-status").textContent=`Целостность: ${log.verification.status} · Событий: ${log.verification.events_checked} · Head: ${log.verification.head_sha256.slice(0,24)}`;
  table($("runs-table"),["Запуск","Модуль","Время UTC","Результат","Экспорт"],runs.map(r=>{
    const actions=element("div",undefined,"actions");for(const [k,label]of [["export","ZIP"],["report","HTML"]]){const b=element("button",label);b.onclick=()=>task(b,()=>download(r.id,k));actions.append(b)}
    return[r.id.slice(0,12),r.kind,r.created_at.slice(0,19),r.result_sha.slice(0,16),actions];}));
  table($("events-table"),["№","Время","Событие","Данные"],log.events.map(e=>[e.seq,e.created_at.slice(0,19),e.kind,JSON.stringify(e.payload)]));
}
async function refreshController(){
  const r=await get("/api/controller");$("control-state").textContent=r.state;$("control-state").className=`badge ${r.state}`;$("control-reason").textContent=r.reason;
  chart($("control-chart"),r.trace,"t_s",[{key:"x",color:"#77d6ca",label:"Отклик"},{key:"target",color:"#edbd75",label:"Уставка"},{key:"u",color:"#819cce",label:"Управление"}]);
  const m=$("control-metrics");m.replaceChildren();metric(m,"Drive (симуляция)",r.drive);metric(m,"Возраст данных, s",r.sensor_age_s);metric(m,"Reduced safe margin, s",r.guard.safe_margin_s);metric(m,"Физический выход","Недоступен");
}
$("login").showModal();
$("login-form").onsubmit=async e=>{e.preventDefault();token=$("token").value.trim();try{await refreshCount();$("login").close();$("token").value="";$("connection").textContent="Локальный сеанс";$("login-error").textContent="";}catch(err){token="";$("login-error").textContent=err.message;}};
$("login").addEventListener("cancel",e=>e.preventDefault());
$("logout").onclick=()=>{token="";$("connection").textContent="Требуется вход";$("login").showModal();};
document.querySelectorAll("nav button").forEach(b=>b.onclick=()=>task(b,()=>view(b.dataset.view)));
$("baseline").onclick=()=>task($("baseline"),()=>experiment("evaluate",{}));
$("candidate-form").onsubmit=e=>{e.preventDefault();const p=Object.fromEntries([...new FormData(e.target)].map(([k,v])=>[k,Number(v)]));task(e.target.querySelector("button"),()=>experiment("evaluate",p));};
Object.keys(presets).forEach(k=>$("experiment-kind").append(element("option",k)));choosePreset();$("experiment-kind").onchange=choosePreset;
$("config-file").onchange=async e=>{const f=e.target.files[0];if(f){if(f.size>1000000){error(new Error("Конфигурация больше 1 MB"));return;}$("experiment-config").value=await f.text();}};
$("experiment-run").onclick=()=>task($("experiment-run"),async()=>{
  const kind=$("experiment-kind").value,run=await experiment(kind,JSON.parse($("experiment-config").value)),r=run.result;$("experiment-id").textContent=run.id.slice(0,16);$("experiment-result").textContent=JSON.stringify(r,null,2);
  const c=$("experiment-chart");c.replaceChildren();
  if(kind==="wave")chart(c,r.x.map((x,i)=>({x,psi:r.final[i]})),"x",[{key:"psi",color:"#77d6ca",label:"Финальный профиль ψ"}]);
  else if(kind==="geodesic")chart(c,r.path,"coordinate_time_s",[{key:"l_m",color:"#77d6ca",label:"l(t), м"}]);
  else if(kind==="control")chart(c,r.trace,"time_s",[{key:"position",color:"#77d6ca",label:"Отклик"},{key:"drive",color:"#edbd75",label:"Управление"}]);
  else if(r.samples)chart(c,r.samples,"frequency_hz",[{key:"group_delay_s",color:"#77d6ca",label:"Групповая задержка, s"}]);
  else{c.textContent="Полный результат приведён ниже";c.classList.add("empty");}
});
document.querySelectorAll("[data-command]").forEach(b=>b.onclick=()=>task(b,async()=>{await post("/api/controller",{action:b.dataset.command});await refreshController();}));
$("setpoint-form").onsubmit=e=>{e.preventDefault();task(null,async()=>{await post("/api/controller",{action:"setpoint",value:Number($("setpoint").value)});await refreshController();});};
$("inject-fault").onclick=()=>task($("inject-fault"),async()=>{await post("/api/controller/fault",{kind:$("fault-kind").value});await refreshController();});
$("refresh-audit").onclick=()=>task($("refresh-audit"),audit);
$("save-control").onclick=()=>task($("save-control"),async()=>{await post("/api/controller/snapshot",{});await view("audit");});
let polling=false;
setInterval(async()=>{if(token&&currentView==="control"&&!polling){polling=true;try{await refreshController();}catch(e){error(e)}finally{polling=false}}},1000);
