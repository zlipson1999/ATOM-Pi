/**
 * AtomRobot v2 — ATOM-Pi's full robot CHARACTER (not a face with a body).
 * Code-drawn, offline, original design. Head with brow plate, visor
 * eyes and mouth grille; trapezius + pauldron shoulders; armored torso
 * with a large ringed chest power core; two articulated arms
 * (shoulder + elbow + hand) — the right hand physically TRAVELS to the
 * head, taps with a visible contact recoil while thinking, and glides
 * back the instant thinking ends (all poses are transform transitions:
 * interruptible by design).
 *
 * State priority (single resolver, applied in AtomRobotAdapter):
 *   error > boot > speaking > thinking > seeing > tool_use
 *         > listening > idle > offline(when disconnected)
 * Animation interruption rules (enforced structurally):
 *   thinking->speaking: tap interval cleared on state change, arm
 *   transitions home; speaking->listening: mouth interval cleared;
 *   any->error: gesture cancels the same way. No pose persists.
 */
import { useEffect, useRef, useState } from "react";

const STEEL="#5c6a78", STEEL_D="#3d4854", STEEL_L="#7b8ca0", PLATE="#4a5866";
const LINE="#1d242c", CORE="#39c0ff", CORE_HOT="#a5e9ff";
const EYE="#39c0ff", EYE_ERR="#ff5c5c", EYE_OFF="#31404d";
const VALID=["boot","idle","listening","thinking","seeing","knowledge_search","web_search","tool_use","speaking","error","offline"];
const T="transform .55s cubic-bezier(.34,1.25,.45,1)";

export default function AtomRobot({ state="idle", size=340 }) {
  const s = VALID.includes(state) ? state : "idle";
  const [tick,setTick]=useState(0);
  const [tap,setTap]=useState(0);
  const [mouth,setMouth]=useState([7,12,9,6,10]);
  const reduced=useRef(typeof window!=="undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);

  useEffect(()=>{ if(reduced.current) return;
    const id=setInterval(()=>setTick(t=>t+1),120); return ()=>clearInterval(id);},[]);
  useEffect(()=>{ if(s!=="thinking"||reduced.current){setTap(0);return;}
    const id=setInterval(()=>setTap(t=>(t+1)%8),380); return ()=>clearInterval(id);},[s]);
  useEffect(()=>{ if(s!=="speaking"||reduced.current){setMouth([7,12,9,6,10]);return;}
    const id=setInterval(()=>setMouth(m=>m.map(()=>4+Math.round(Math.random()*11))),130);
    return ()=>clearInterval(id);},[s]);

  const breathe=reduced.current?0:Math.sin(tick/8)*2.4;
  const speakSway=(s==="speaking"&&!reduced.current)?Math.sin(tick/4)*0.8:0;
  const pulse=(()=>{const base={idle:.35,listening:.55,thinking:.95,seeing:.85,
    knowledge_search:.85,web_search:.9,tool_use:.85,speaking:.6,boot:.9,error:.5,offline:.1}[s];
    const speed={idle:14,listening:8,thinking:3.5,seeing:5,knowledge_search:4.5,web_search:3.8,tool_use:4,
      speaking:6,boot:4,error:5,offline:34}[s];
    return base+(reduced.current?0:Math.abs(Math.sin(tick/speed))*0.4);})();
  const eyeH={idle:9,listening:16,thinking:8,seeing:12,knowledge_search:10,web_search:11,tool_use:9,
    speaking:11,boot:5,error:12,offline:4}[s];
  const eyeFill=s==="error"?EYE_ERR:s==="offline"?EYE_OFF:EYE;
  const eyeScan=((s==="seeing"||s==="web_search"||s==="knowledge_search")&&!reduced.current)?Math.sin(tick/(s==="web_search"?3.5:5))*9:0;
  const headTilt=s==="thinking"?-4:s==="listening"?2:0;

  // Right arm choreography: rest -> raised beside head -> tap contact.
  // tap sequence gives travel + contact + recoil, varied so it never
  // reads as a loop: contact frames pull the forearm in (elbow), the
  // hand nudges down onto the head, then eases off.
  const rest={sh:-8, el:-6, hy:0};
  const think={sh:-148, el:-96, hy:0};
  const contact=[0,-7,0,-4,0,0,-6,0][tap];          // hand press depth
  const elbowTap=[0,-6,0,-4,0,0,-5,0][tap];          // forearm pulls in
  const pose=s==="thinking"
    ? {sh:think.sh, el:think.el+elbowTap, hy:contact}
    : (s==="tool_use"||s==="knowledge_search"||s==="web_search") ? {sh:-42,el:-30,hy:0}
    : s==="listening" ? {sh:-16,el:-12,hy:0}
    : rest;
  const leftSh=s==="thinking"?12:s==="listening"?7:4;

  const label={boot:"starting up",idle:"say the wake word",listening:"listening…",
    thinking:"thinking",seeing:"looking…",knowledge_search:"checking the library…",web_search:"searching the web…",tool_use:"working on it",
    speaking:"speaking",error:"something went wrong",offline:"offline — limited mode"}[s];

  return (
    <div style={{textAlign:"center"}}>
      <svg viewBox="0 0 380 480" width={size} height={size*1.26}
           role="img" aria-label={`ATOM robot, ${label}`}>
        <defs>
          <radialGradient id="coreG" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={CORE_HOT} stopOpacity={pulse}/>
            <stop offset="45%" stopColor={CORE} stopOpacity={pulse*.8}/>
            <stop offset="100%" stopColor={CORE} stopOpacity="0"/>
          </radialGradient>
        </defs>
        <g style={{transform:`translateY(${breathe}px) rotate(${speakSway}deg)`,
                   transformOrigin:"190px 300px",transition:"transform .12s linear"}}>

          {/* LEFT ARM */}
          <g style={{transformOrigin:"104px 232px",transform:`rotate(${leftSh}deg)`,transition:T}}>
            <circle cx="104" cy="232" r="21" fill={STEEL_L} stroke={LINE} strokeWidth="5"/>
            <rect x="90" y="240" width="26" height="66" rx="12" fill={STEEL_D} stroke={LINE} strokeWidth="4"/>
            <circle cx="103" cy="308" r="11" fill={PLATE} stroke={LINE} strokeWidth="4"/>
            <rect x="92" y="312" width="22" height="58" rx="10" fill={STEEL} stroke={LINE} strokeWidth="4"/>
            <rect x="94" y="330" width="18" height="7" rx="3" fill={STEEL_L} opacity=".5"/>
            <rect x="90" y="368" width="26" height="24" rx="8" fill={STEEL_L} stroke={LINE} strokeWidth="4"/>
            <rect x="112" y="372" width="9" height="14" rx="4" fill={STEEL_L} stroke={LINE} strokeWidth="3"/>
          </g>

          {/* TORSO */}
          <path d="M 116 222 L 264 222 L 252 372 Q 190 390 128 372 Z"
                fill={STEEL} stroke={LINE} strokeWidth="6"/>
          <path d="M 116 222 L 264 222 L 259 262 L 121 262 Z" fill={PLATE} stroke={LINE} strokeWidth="4"/>
          <path d="M 132 372 L 248 372 L 244 396 Q 190 408 136 396 Z"
                fill={STEEL_D} stroke={LINE} strokeWidth="5"/>
          {[150,190,230].map(x=>(<rect key={x} x={x-2} y="350" width="4" height="14" rx="2" fill={LINE} opacity=".55"/>))}
          {/* CHEST CORE — large, housed, pulsing */}
          <circle cx="190" cy="300" r="66" fill="url(#coreG)"/>
          <circle cx="190" cy="300" r="42" fill="#0c1216" stroke={LINE} strokeWidth="6"/>
          <circle cx="190" cy="300" r="42" fill="none" stroke={STEEL_L} strokeWidth="2" opacity=".5"/>
          {[0,60,120,180,240,300].map(a=>{
            const r=(a*Math.PI)/180;
            return <circle key={a} cx={190+Math.cos(r)*49} cy={300+Math.sin(r)*49}
                           r="3.4" fill={STEEL_L} stroke={LINE} strokeWidth="2"/>;})}
          <circle cx="190" cy="300" r="29" fill="none" stroke={CORE}
                  strokeWidth="5" opacity={0.45+pulse*.5}/>
          <circle cx="190" cy="300" r="13" fill={s==="error"?EYE_ERR:CORE} opacity={0.5+pulse*.5}/>

          {/* SHOULDER PAULDRONS */}
          <path d="M 96 206 Q 122 186 152 200 L 148 236 Q 118 244 96 232 Z"
                fill={PLATE} stroke={LINE} strokeWidth="5"/>
          <path d="M 284 206 Q 258 186 228 200 L 232 236 Q 262 244 284 232 Z"
                fill={PLATE} stroke={LINE} strokeWidth="5"/>

          {/* NECK + HEAD */}
          <rect x="172" y="168" width="36" height="30" rx="9" fill={STEEL_D} stroke={LINE} strokeWidth="5"/>
          <g style={{transformOrigin:"190px 170px",transform:`rotate(${headTilt}deg)`,transition:T}}>
            <rect x="126" y="52" width="128" height="118" rx="26" fill={STEEL} stroke={LINE} strokeWidth="6"/>
            <path d="M 126 92 L 254 92 L 254 74 Q 254 52 228 52 L 152 52 Q 126 52 126 74 Z"
                  fill={PLATE} stroke={LINE} strokeWidth="4"/>
            <g style={{transform:`translateX(${eyeScan}px)`,transition:"transform .2s"}}>
              <rect x="146" y={104-eyeH/2} width="32" height={eyeH} rx={eyeH/2}
                    fill={eyeFill} style={{transition:"all .25s"}}/>
              <rect x="202" y={104-eyeH/2} width="32" height={eyeH} rx={eyeH/2}
                    fill={eyeFill} style={{transition:"all .25s"}}/>
            </g>
            <g>{mouth.map((h,i)=>(
              <rect key={i} x={150+i*17} y={144-h/2} width="9" height={h} rx="4"
                    fill={s==="offline"?EYE_OFF:LINE} style={{transition:"all .12s"}}/>))}
            </g>
            <rect x="114" y="88" width="14" height="32" rx="7" fill={STEEL_D} stroke={LINE} strokeWidth="4"/>
            <rect x="252" y="88" width="14" height="32" rx="7" fill={STEEL_D} stroke={LINE} strokeWidth="4"/>
            <circle cx="140" cy="66" r="3" fill={LINE}/><circle cx="240" cy="66" r="3" fill={LINE}/>
          </g>

          {/* RIGHT ARM — performs the head tap */}
          <g style={{transformOrigin:"276px 232px",transform:`rotate(${pose.sh}deg)`,transition:T}}>
            <circle cx="276" cy="232" r="21" fill={STEEL_L} stroke={LINE} strokeWidth="5"/>
            <rect x="264" y="240" width="26" height="66" rx="12" fill={STEEL_D} stroke={LINE} strokeWidth="4"/>
            <g style={{transformOrigin:"277px 308px",transform:`rotate(${pose.el}deg)`,transition:T}}>
              <circle cx="277" cy="308" r="11" fill={PLATE} stroke={LINE} strokeWidth="4"/>
              <rect x="266" y="312" width="22" height="58" rx="10" fill={STEEL} stroke={LINE} strokeWidth="4"/>
              <rect x="268" y="330" width="18" height="7" rx="3" fill={STEEL_L} opacity=".5"/>
              <g style={{transform:`translateY(${pose.hy}px)`,transition:"transform .16s ease-out"}}>
                <rect x="264" y="368" width="26" height="24" rx="8" fill={STEEL_L} stroke={LINE} strokeWidth="4"/>
                <rect x="256" y="372" width="9" height="14" rx="4" fill={STEEL_L} stroke={LINE} strokeWidth="3"/>
              </g>
            </g>
          </g>
        </g>
      </svg>
      <div style={{fontFamily:"ui-monospace,monospace",fontSize:13,letterSpacing:3,
        color:s==="error"?EYE_ERR:CORE,textTransform:"uppercase",marginTop:2}}>{label}</div>
    </div>
  );
}
