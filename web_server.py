#!/usr/bin/env python3
"""
web_server.py — Tapo panel
  python web_server.py
  https://0.0.0.0:8083
"""
import os

from flask import Flask, render_template_string

import web_live_video
import web_ptz
import web_receive_voice
import web_record
import web_speak

CFG = {
    "camera_ip": "192.168.1.11",
    "camera_user": "admin",
    # RTSP / stream
    "camera_pass": "Test123",
    # ONVIF ContinuousMove (sənin işlək skriptin)
    "onvif_pass": "Test123",
    "cloud_pass": "Test123",
    "voices_dir": "./voices",
    "volume": 2.5,
    "onvif_port": 2020,
    "ptz_speed": 0.6,  # 0.1 slow .. 1.0 max
    "http_port": 8083,
    # video low-latency defaults
    "video_stream": "2",
    "video_width": 480,
    "video_q": 12,
    "video_fps": 10,
    "rtsp_transport": "udp",
}

web_live_video.init(CFG)
web_ptz.init(CFG)
web_receive_voice.init(CFG)
web_speak.init(CFG)
web_record.init(CFG)

app = Flask(__name__)
app.register_blueprint(web_live_video.bp)
app.register_blueprint(web_ptz.bp)
app.register_blueprint(web_receive_voice.bp)
app.register_blueprint(web_speak.bp)
app.register_blueprint(web_record.bp)

PAGE = r"""
<!DOCTYPE html>
<html lang="az">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<meta name="mobile-web-app-capable" content="yes"/>
<title>Tapo C211 Panel</title>
<style>
  :root { --bg:#0f1419; --card:#1a2332; --accent:#3b82f6; --ok:#22c55e; --danger:#ef4444; --text:#e7ecf3; --muted:#8b9bb4; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:system-ui,sans-serif; background:var(--bg); color:var(--text); }
  header { padding:12px 20px; background:#111827; border-bottom:1px solid #243044; display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
  header h1 { margin:0; font-size:1.1rem; }
  .badge { font-size:.75rem; background:#243044; padding:2px 8px; border-radius:999px; color:var(--muted); }
  main { display:grid; grid-template-columns:1fr 340px; gap:16px; padding:16px; max-width:1400px; margin:0 auto; }
  @media (max-width:900px){
    main{grid-template-columns:1fr; padding:10px; gap:12px;}
    header{padding:10px 12px;}
    .ptz{ grid-template-columns:repeat(3,72px); gap:10px; }
    .ptz button{ padding:16px; font-size:1.2rem; min-height:52px; }
    .btn-talk{ min-height:64px; font-size:1.05rem; touch-action:none; }
    .btn-rec{ min-height:52px; }
  }
  .chips{ display:flex; flex-wrap:wrap; gap:6px; margin:8px 0; }
  .chips button{
    padding:8px 12px; border-radius:999px; font-size:.8rem;
    background:#243044; border:1px solid #334155; color:var(--text);
  }
  .chips button.on{ background:var(--accent); border-color:#2563eb; }
  .safe-bottom{ padding-bottom: max(12px, env(safe-area-inset-bottom)); }
  .slider-row{ display:flex; align-items:center; gap:10px; margin:8px 0; font-size:.85rem; color:var(--muted); }
  .slider-row label{ min-width:4.5rem; }
  .slider-row input[type=range]{ flex:1; height:28px; accent-color:var(--accent); }
  .slider-row .val{ min-width:2.5rem; text-align:right; color:var(--text); }


  .card { background:var(--card); border-radius:12px; padding:14px; border:1px solid #243044; }
  .card h2 { margin:0 0 12px; font-size:.8rem; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; }
  .video-wrap { background:#000; border-radius:8px; overflow:hidden; aspect-ratio:16/9; }
  .video-wrap img { width:100%; height:100%; object-fit:contain; display:block; }
  .ptz { display:grid; grid-template-columns:repeat(3,64px); gap:8px; justify-content:center; }
  button {
    background:#243044; color:var(--text); border:1px solid #334155; border-radius:8px;
    padding:10px 14px; cursor:pointer; font-size:.9rem;
  }
  button:active { background:var(--accent); }
  button:disabled { opacity:.5; cursor:not-allowed; }
  .ptz .e { visibility:hidden; }
  .btn-ok { background:var(--ok); border-color:#16a34a; color:#052e16; font-weight:600; }
  .btn-danger { background:var(--danger); border-color:#b91c1c; color:#fff; font-weight:600; }
  .btn-talk { background:#f59e0b; border-color:#d97706; color:#1c1917; font-weight:700; min-height:48px; width:100%; }
  .btn-talk.active { background:#ef4444; border-color:#b91c1c; color:#fff; }
  .btn-rec { width:100%; font-weight:700; min-height:44px; }
  .btn-rec.on { background:var(--danger); border-color:#b91c1c; color:#fff; animation: pulse 1.2s infinite; }
  @keyframes pulse { 50% { opacity:.75; } }
  .voices { list-style:none; margin:0; padding:0; max-height:260px; overflow:auto; }
  .voices li { display:flex; gap:8px; align-items:center; padding:8px 0; border-bottom:1px solid #243044; font-size:.85rem; }
  .voices .name { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .status { font-size:.85rem; color:var(--muted); min-height:1.2em; margin-top:8px; }
  .row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-top:8px; }
  .toggle { display:flex; align-items:center; gap:8px; }
</style>
</head>
<body class="safe-bottom">
<header>
  <h1>Tapo C211</h1>
  <span class="badge">{{ ip }}</span>
  <span class="badge">:8083</span>
</header>
<main>
  <section class="card">
    <h2>Live video</h2>
    <div class="video-wrap"><img id="live" alt="live"/></div>
    <div class="chips" id="qChips">
      <button type="button" data-q="low">Low</button>
      <button type="button" data-q="med" class="on">Med</button>
      <button type="button" data-q="high">High</button>
      <button type="button" data-q="max">Max</button>
    </div>
    <div class="row">
      <label class="toggle"><input type="radio" name="vmode" value="snap" onchange="setVideoMode()"/> Snapshot</label>
      <label class="toggle"><input type="radio" name="vmode" value="mjpeg" checked onchange="setVideoMode()"/> MJPEG</label>
    </div>
    <div class="row">
      <label class="toggle"><input type="checkbox" id="listen"/> Kamera mic dinle</label>
      <span class="status" id="listenSt"></span>
    </div>
    <div class="slider-row">
      <label>Listen</label>
      <input type="range" id="volListen" min="0" max="3" step="0.05" value="1"/>
      <span class="val" id="volListenVal">1.0</span>
    </div>
  </section>

  <div style="display:flex;flex-direction:column;gap:16px;">
    <section class="card">
      <h2>PTZ (basılı saxla)</h2>
      <div class="ptz">
        <span class="e"></span>
        <button type="button" data-ptz="up">▲</button>
        <span class="e"></span>
        <button type="button" data-ptz="left">◀</button>
        <button type="button" onclick="ptzStop()">■</button>
        <button type="button" data-ptz="right">▶</button>
        <span class="e"></span>
        <button type="button" data-ptz="down">▼</button>
        <span class="e"></span>
      </div>
      <div class="slider-row">
        <label>Speed</label>
        <input type="range" id="ptzSpeed" min="0.1" max="1" step="0.05" value="0.6"/>
        <span class="val" id="ptzSpeedVal">0.60</span>
      </div>
      <div class="status" id="ptzst">WASD / oxlar — basılı saxla</div>
    </section>

    <section class="card">
      <h2>Bas-danish (mic → kamera)</h2>
      <button type="button" class="btn-talk" id="ptt">
        BASILI SAXLA — DANIS
      </button>
      <div class="slider-row">
        <label>Mic→Cam</label>
        <input type="range" id="volPtt" min="0.05" max="1.2" step="0.05" value="0.35"/>
        <span class="val" id="volPttVal">0.35</span>
      </div>
      <div class="status" id="pttSt"></div>
    </section>

    <section class="card">
      <h2>Record (kamera mic → voices/)</h2>
      <button type="button" class="btn-rec" id="btnRec" onclick="recToggle()">Record</button>
      <div class="status" id="recSt"></div>
    </section>

    <section class="card" style="flex:1;">
      <h2>Voices → Speaker</h2>
      <div class="slider-row">
        <label>Speak</label>
        <input type="range" id="volSpeak" min="0.2" max="4" step="0.1" value="2.5"/>
        <span class="val" id="volSpeakVal">2.5</span>
      </div>
      <div class="row">
        <button type="button" class="btn-danger" onclick="speakStop()">Stop</button>
        <span class="status" id="spk"></span>
      </div>
      <ul class="voices" id="voices"></ul>
    </section>
  </div>
</main>
<script>
// ---- video quality + mode ----
const Q = {
  low:  {stream:'2', w:320,  q:14, fps:8,  poll:125},
  med:  {stream:'2', w:480,  q:12, fps:10, poll:100},
  high: {stream:'2', w:720,  q:8,  fps:12, poll:80},
  max:  {stream:'1', w:1280, q:5,  fps:15, poll:66}
};
let videoQ = localStorage.getItem('tapo_q') || 'med';
let snapTimer=null;

function applyQChips(){
  document.querySelectorAll('#qChips [data-q]').forEach(b=>{
    b.classList.toggle('on', b.getAttribute('data-q')===videoQ);
  });
}
document.getElementById('qChips').onclick = (e)=>{
  const b=e.target.closest('[data-q]'); if(!b) return;
  videoQ = b.getAttribute('data-q');
  localStorage.setItem('tapo_q', videoQ);
  applyQChips();
  // snapshot worker CFG server-side sabitdir; mjpeg URL dəyişir.
  // snapshot üçün keyfiyyət dəyişsin deyə səhifə reload əvəzinə mjpeg param + restart hint
  setVideoMode(true);
};

function setVideoMode(restartSnap){
  const mode=document.querySelector('input[name=vmode]:checked').value;
  const img=document.getElementById('live');
  const c=Q[videoQ]||Q.med;
  if(snapTimer){ clearInterval(snapTimer); snapTimer=null; }
  const qs=`stream=${c.stream}&w=${c.w}&q=${c.q}&fps=${c.fps}&t=udp`;
  if(mode==='snap'){
    img.removeAttribute('src');
    const tick=()=>{ img.src='/api/snapshot?'+qs+'&_='+Date.now(); };
    tick();
    snapTimer=setInterval(tick, c.poll);
  }else{
    img.src='/api/mjpeg?'+qs+'&_='+Date.now();
  }
  applyQChips();
}
setVideoMode();

function bindSliders(){
  const bind=(id, valId, store, post)=>{
    const el=document.getElementById(id);
    const lab=document.getElementById(valId);
    if(!el) return;
    const saved=localStorage.getItem(store);
    if(saved!=null) el.value=saved;
    const sync=()=>{
      lab.textContent=(+el.value).toFixed(2).replace(/0+$/,'').replace(/\.$/,'')||el.value;
      localStorage.setItem(store, el.value);
      if(post) post(+el.value);
    };
    el.addEventListener('input', sync);
    sync();
  };
  bind('volListen','volListenVal','tapo_vol_listen', v=>{
    if(window._listenGain) window._listenGain.gain.value=v;
  });
  bind('ptzSpeed','ptzSpeedVal','tapo_ptz_speed', null);
  bind('volPtt','volPttVal','tapo_vol_ptt', v=>{
    fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ptt_gain:v})}).catch(()=>{});
  });
  bind('volSpeak','volSpeakVal','tapo_vol_speak', v=>{
    fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({volume:v})}).catch(()=>{});
  });
}
bindSliders();


// PTT pointer events (mobile + desktop)
(function(){
  const pttBtn=document.getElementById('ptt');
  if(!pttBtn) return;
  const down=e=>{ e.preventDefault(); pttDown(e); };
  const up=e=>{ e.preventDefault(); pttUp(e); };
  pttBtn.addEventListener('pointerdown', down);
  pttBtn.addEventListener('pointerup', up);
  pttBtn.addEventListener('pointercancel', up);
  pttBtn.addEventListener('pointerleave', e=>{ if(pttOn) pttUp(e); });
  // köhnə touch/mouse da
  pttBtn.addEventListener('touchstart', down, {passive:false});
  pttBtn.addEventListener('touchend', up);
  pttBtn.addEventListener('mousedown', down);
  pttBtn.addEventListener('mouseup', up);
})();

let ptzDir=null;

function ptzSpeed(){ return +document.getElementById('ptzSpeed').value||0.6; }
async function ptzStart(dir){
  if(ptzDir===dir) return;
  ptzDir=dir;
  document.getElementById('ptzst').textContent=dir+'...';
  try{
    const r=await fetch('/api/ptz',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({action:'start',dir,speed:ptzSpeed()})});
    const j=await r.json();
    document.getElementById('ptzst').textContent=j.limit?'limit':(j.ok?(dir+' '+j.speed): (j.error||''));
  }catch(e){ document.getElementById('ptzst').textContent=String(e); }
}
async function ptzStop(){
  ptzDir=null;
  try{
    await fetch('/api/ptz',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({action:'stop'})});
    document.getElementById('ptzst').textContent='STOP';
  }catch(e){ document.getElementById('ptzst').textContent=String(e); }
}
// düymələr: mousedown/touchstart = start, mouseup/leave = stop
document.querySelectorAll('[data-ptz]').forEach(btn=>{
  const dir=btn.getAttribute('data-ptz');
  const down=e=>{ e.preventDefault(); ptzStart(dir); };
  const up=e=>{ e.preventDefault(); ptzStop(); };
  btn.addEventListener('mousedown',down);
  btn.addEventListener('touchstart',down,{passive:false});
  btn.addEventListener('mouseup',up);
  btn.addEventListener('mouseleave',()=>{ if(ptzDir===dir) ptzStop(); });
  btn.addEventListener('touchend',up);
  btn.addEventListener('touchcancel',up);
});
window.addEventListener('mouseup',()=>{ if(ptzDir) ptzStop(); });
// klaviatura: keydown start, keyup stop
const keyMap={ArrowUp:'up',ArrowDown:'down',ArrowLeft:'left',ArrowRight:'right',w:'up',a:'left',s:'down',d:'right'};
document.addEventListener('keydown',e=>{
  if(['INPUT','TEXTAREA'].includes(e.target.tagName)) return;
  if(e.repeat) return;
  const d=keyMap[e.key]||keyMap[e.key.toLowerCase()];
  if(d){ e.preventDefault(); ptzStart(d); }
  if(e.key===' '){ e.preventDefault(); ptzStop(); }
});
document.addEventListener('keyup',e=>{
  const d=keyMap[e.key]||keyMap[e.key.toLowerCase()];
  if(d && ptzDir===d){ e.preventDefault(); ptzStop(); }
});
document.addEventListener('blur',()=>ptzStop());


async function loadVoices(){
  const j = await (await fetch('/api/voices')).json();
  const ul = document.getElementById('voices');
  ul.innerHTML='';
  (j.files||[]).forEach(f=>{
    const li=document.createElement('li');
    li.innerHTML=`<span class="name">${f.name}</span><span class="status">${(f.size/1024).toFixed(0)}KB</span>
      <button data-play="${f.name}">Play</button>
      <button class="btn-ok" data-f="${f.name}">Send</button>`;
    ul.appendChild(li);
  });
  if(j.speaking) document.getElementById('spk').textContent = j.status||'playing...';
}
let localAudio=null;
document.getElementById('voices').onclick = async e=>{
  const playBtn=e.target.closest('[data-play]');
  if(playBtn){
    const file=playBtn.getAttribute('data-play');
    try{
      if(localAudio){ localAudio.pause(); localAudio=null; }
      localAudio=new Audio('/api/voices/'+encodeURIComponent(file));
      localAudio.play();
      document.getElementById('spk').textContent='Play (PC): '+file;
    }catch(err){ document.getElementById('spk').textContent=String(err); }
    return;
  }
  const b=e.target.closest('[data-f]'); if(!b) return;
  const file=b.dataset.f;
  document.getElementById('spk').textContent='Gonderilir: '+file;
  b.disabled=true;
  try{
    const j=await (await fetch('/api/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({file})})).json();
    document.getElementById('spk').textContent=j.ok?('OK: '+file):(j.error||'xeta');
  }catch(err){ document.getElementById('spk').textContent=String(err); }
  b.disabled=false;
};

async function speakStop(){
  await fetch('/api/speak_stop',{method:'POST'});
  document.getElementById('spk').textContent='Stop...';
}
loadVoices();
setInterval(loadVoices, 4000);

async function recToggle(){
  const btn=document.getElementById('btnRec');
  const st=document.getElementById('recSt');
  btn.disabled=true;
  try{
    const j=await (await fetch('/api/record/toggle',{method:'POST'})).json();
    if(j.recording){
      btn.classList.add('on');
      btn.textContent='Recording... (stop)';
      st.textContent='yazilir: '+(j.file||'');
    }else{
      btn.classList.remove('on');
      btn.textContent='Record';
      st.textContent=j.file?('saxlandi: '+j.file):'dayandirildi';
      loadVoices();
    }
  }catch(e){ st.textContent=String(e); }
  btn.disabled=false;
}
(async ()=>{
  try{
    const j=await (await fetch('/api/record/status')).json();
    if(j.recording){
      const btn=document.getElementById('btnRec');
      btn.classList.add('on');
      btn.textContent='Recording... (stop)';
      document.getElementById('recSt').textContent='yazilir: '+(j.file||'');
    }
  }catch(_){}
})();

let audioCtx=null, listenAbort=null, listenGain=null, listenNextT=0;
document.getElementById('listen').onchange = async function(){
  const on=this.checked;
  const st=document.getElementById('listenSt');
  if(!on){
    if(listenAbort) listenAbort.abort();
    listenAbort=null;
    listenGain=null;
    window._listenGain=null;
    listenNextT=0;
    if(audioCtx){ try{ await audioCtx.close(); }catch(_){} audioCtx=null; }
    st.textContent='off';
    return;
  }
  st.textContent='qosulur...';
  try{
    // hər açılışda YENİ context + gain (köhnə closed context-ə bağlama)
    if(audioCtx){ try{ await audioCtx.close(); }catch(_){} }
    audioCtx=new (window.AudioContext||window.webkitAudioContext)({sampleRate:8000});
    await audioCtx.resume();
    listenGain=audioCtx.createGain();
    listenGain.gain.value=+document.getElementById('volListen').value||1;
    listenGain.connect(audioCtx.destination);
    window._listenGain=listenGain;
    listenNextT=audioCtx.currentTime;
    listenAbort=new AbortController();
    const res=await fetch('/api/camera_audio',{signal:listenAbort.signal});
    const reader=res.body.getReader();
    st.textContent='dinlenilir';
    let pending=new Uint8Array(0);
    const ctx=audioCtx; // closure — eyni context
    const gain=listenGain;
    const playChunk=(s16)=>{
      if(!ctx || ctx.state==='closed' || !gain) return;
      const n=s16.byteLength/2; if(n<1) return;
      const f32=new Float32Array(n);
      const view=new DataView(s16.buffer,s16.byteOffset,s16.byteLength);
      for(let i=0;i<n;i++) f32[i]=view.getInt16(i*2,true)/32768;
      const buf=ctx.createBuffer(1,n,8000);
      buf.copyToChannel(f32,0);
      const src=ctx.createBufferSource();
      src.buffer=buf;
      src.connect(gain);
      // kadrları ardıcıl schedule et (click/gap azaltmaq)
      const dur=n/8000;
      if(listenNextT < ctx.currentTime) listenNextT=ctx.currentTime+0.02;
      src.start(listenNextT);
      listenNextT+=dur;
    };
    (async()=>{
      while(true){
        const {done,value}=await reader.read();
        if(done) break;
        if(!ctx || ctx.state==='closed') break;
        const merged=new Uint8Array(pending.length+value.length);
        merged.set(pending); merged.set(value,pending.length);
        let off=0;
        while(off+3200<=merged.length){ playChunk(merged.subarray(off,off+3200)); off+=3200; }
        pending=merged.subarray(off);
      }
    })().catch(e=>{ if(e.name!=='AbortError') st.textContent=String(e); });
  }catch(e){ st.textContent=String(e); this.checked=false; }
};

let pttOn=false, pttStream=null, pttCtx=null, pttTimer=null, pttBuf=[];
async function pttDown(ev){
  ev.preventDefault();
  if(pttOn) return;
  pttOn=true;
  const btn=document.getElementById('ptt');
  btn.classList.add('active');
  btn.textContent='DANISIR...';
  document.getElementById('pttSt').textContent='session...';
  try{
    const j=await (await fetch('/api/ptt/start',{method:'POST'})).json();
    if(!j.ok) throw new Error(j.error||'start failed');
    document.getElementById('pttSt').textContent='OK '+j.session;
    pttStream=await navigator.mediaDevices.getUserMedia({
      audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true,channelCount:1}
    });
    pttCtx=new (window.AudioContext||window.webkitAudioContext)();
    const src=pttCtx.createMediaStreamSource(pttStream);
    const proc=pttCtx.createScriptProcessor(2048,1,1);
    const mute=pttCtx.createGain(); mute.gain.value=0;
    pttBuf=[];
    proc.onaudioprocess=(e)=>{
      if(!pttOn) return;
      const input=e.inputBuffer.getChannelData(0);
      const ratio=pttCtx.sampleRate/8000;
      const outLen=Math.floor(input.length/ratio);
      for(let i=0;i<outLen;i++){
        let s=input[Math.floor(i*ratio)]*0.5;
        s=Math.max(-1,Math.min(1,s));
        pttBuf.push((s*32767)|0);
      }
    };
    src.connect(proc); proc.connect(mute); mute.connect(pttCtx.destination);
    pttTimer=setInterval(async ()=>{
      if(!pttOn||pttBuf.length<160) return;
      const n=pttBuf.length-(pttBuf.length%160);
      const slice=pttBuf.splice(0,n);
      const s16=new Int16Array(slice);
      try{
        await fetch('/api/ptt/audio',{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:s16.buffer});
      }catch(_){}
    },100);
  }catch(e){
    document.getElementById('pttSt').textContent=String(e);
    pttUp(ev);
  }
}
async function pttUp(ev){
  if(ev) ev.preventDefault();
  pttOn=false;
  if(pttTimer){ clearInterval(pttTimer); pttTimer=null; }
  pttBuf=[];
  const btn=document.getElementById('ptt');
  btn.classList.remove('active');
  btn.textContent='BASILI SAXLA — DANIS';
  if(pttStream){ pttStream.getTracks().forEach(t=>t.stop()); pttStream=null; }
  if(pttCtx){ try{pttCtx.close();}catch(_){} pttCtx=null; }
  try{ await fetch('/api/ptt/stop',{method:'POST'}); }catch(_){}
  document.getElementById('pttSt').textContent='stop';
}
window.addEventListener('mouseup',()=>{ if(pttOn) pttUp(); });
window.addEventListener('blur',()=>{ if(pttOn) pttUp(); });
</script>
</body>
</html>
"""


@app.get("/")
def index():
    return render_template_string(PAGE, ip=CFG["camera_ip"])


if __name__ == "__main__":
    port = CFG["http_port"]
    base = os.path.dirname(os.path.abspath(__file__))
    cert = os.path.join(base, "cert.pem")
    key = os.path.join(base, "key.pem")
    if os.path.isfile(cert) and os.path.isfile(key):
        print(f"HTTPS https://0.0.0.0:{port}")
        app.run(host="0.0.0.0", port=port, threaded=True, ssl_context=(cert, key))
    else:
        print(f"HTTP  http://0.0.0.0:{port}")
        print("  PTT ucun cert: openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365 -subj /CN=tapo")
        app.run(host="0.0.0.0", port=port, threaded=True)
