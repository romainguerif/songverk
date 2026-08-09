"""Audit responsive : rejoue l'app dans Chromium à plusieurs largeurs de téléphone
et signale débordements, textes coupés et cibles tactiles trop petites.

    pip install playwright && playwright install chromium
    python3 tools/audit.py
"""
import os
os.makedirs("shots", exist_ok=True)
from playwright.sync_api import sync_playwright
import json, sys

SEED = """
(()=>{
  const s=song();
  s.name="hypnose nocturne";
  s.rows=[];
  const mk=(bank,slot,len,rep,bpm,label,jm)=>{const r=newRow();
    r.bank=bank;r.slot=slot;r.len=len;r.rep=rep;r.bpm=bpm;r.label=label;
    if(jm)r.jump=jm; return r;};
  s.rows.push(mk(0,0,16,4,132.5,"intro nappe longue et descriptive",null));
  s.rows.push(mk(0,1,64,2,132.5,"drop",{mode:"afterN",target:0,n:3}));
  s.rows.push(mk(7,15,12,1,88,"",{mode:"hold",target:0,n:2}));
  s.rows[0].mutes[3]=true; s.rows[0].mutes[9]=true;
  const l=newLane(); l.key="c49"; l.track=4; l.pts=[{x:0,y:0},{x:.5,y:1},{x:1,y:.2}];
  const l2=newLane(); l2.key="n0.3"; l2.track=11;
  s.rows[0].lanes=[l,l2];
  render();
})()
"""

AUDIT = """
(()=>{
  const bad=[];
  const de=document.documentElement;
  if(de.scrollWidth>de.clientWidth+1) bad.push({el:"<html>",type:"page scroll-x",sw:de.scrollWidth,cw:de.clientWidth});
  document.querySelectorAll("*").forEach(el=>{
    const cs=getComputedStyle(el);
    if(cs.display==="none"||cs.visibility==="hidden") return;
    const r=el.getBoundingClientRect();
    if(r.width===0||r.height===0) return;
    const sel=el.tagName.toLowerCase()+(el.id?"#"+el.id:"")+(el.className&&typeof el.className==="string"?"."+el.className.trim().split(/\\s+/).join("."):"");
    // débordement horizontal non voulu
    if(el.scrollWidth>el.clientWidth+1 && cs.overflowX!=="auto" && cs.overflowX!=="scroll" && cs.textOverflow!=="ellipsis" && !["INPUT","SELECT","TEXTAREA","CANVAS"].includes(el.tagName)){
      bad.push({el:sel,type:"overflow-x",sw:el.scrollWidth,cw:el.clientWidth,txt:(el.textContent||"").trim().slice(0,40)});
    }
    // sort du viewport
    if(r.right>de.clientWidth+1) bad.push({el:sel,type:"hors écran droite",right:Math.round(r.right),vw:de.clientWidth,txt:(el.textContent||"").trim().slice(0,40)});
    if(r.left<-1) bad.push({el:sel,type:"hors écran gauche",left:Math.round(r.left)});
    // texte tronqué verticalement
    if(el.children.length===0 && el.scrollHeight>el.clientHeight+2 && cs.overflowY!=="auto" && cs.overflowY!=="scroll"){
      bad.push({el:sel,type:"texte coupé (hauteur)",sh:el.scrollHeight,ch:el.clientHeight,txt:(el.textContent||"").trim().slice(0,40)});
    }
    // cible tactile trop petite
    if(["BUTTON"].includes(el.tagName) && (r.height<32||r.width<28) && el.offsetParent!==null){
      bad.push({el:sel,type:"cible tactile "+Math.round(r.width)+"x"+Math.round(r.height),txt:(el.textContent||"").trim().slice(0,20)});
    }
  });
  return bad;
})()
"""

VIEWS = [("iPhone SE",320,568),("Android compact",360,740),("Pixel",412,915)]
SHEETS = [("accueil",None),("row",'openRow(0)'),("courbe",'openRow(0);openCurve(0)'),
          ("reglages",'open("#setSheet")'),("songs",'$("#songPill").click()'),
          ("picker",'openRow(0);openCurve(0);$("#laneParam").click()')]

out={}
with sync_playwright() as p:
    b=p.chromium.launch()
    for vname,w,h in VIEWS:
        ctx=b.new_context(viewport={"width":w,"height":h},device_scale_factor=2,is_mobile=True,has_touch=True)
        pg=ctx.new_page()
        pg.on("pageerror", lambda e: print("JS ERROR:",e))
        pg.goto("file://" + __import__("pathlib").Path(__file__).resolve().parent.parent.joinpath("index.html").as_posix() + "")
        pg.wait_for_timeout(400)
        pg.evaluate(SEED)
        for sname,act in SHEETS:
            pg.evaluate("document.querySelectorAll('.sheet').forEach(s=>s.classList.remove('open'))")
            if act: pg.evaluate(act)
            pg.wait_for_timeout(250)
            res=pg.evaluate(AUDIT)
            key=f"{vname} / {sname}"
            out[key]=res
            pg.screenshot(path=f"shots/{w}-{sname}.png", full_page=False)
        ctx.close()
    b.close()

for k,v in out.items():
    uniq={}
    for it in v:
        uniq[it["el"]+it["type"]]=it
    if uniq:
        print("\n=== "+k+" ===")
        for it in list(uniq.values())[:14]:
            print("  ", json.dumps(it, ensure_ascii=False))
    else:
        print("\n=== "+k+" === OK")
