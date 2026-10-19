import type {Page} from '@playwright/test';

// Passive browser instrumentation: never alters sample contents or commands.
export async function installMeter(page:Page){await page.addInitScript(()=>{
  const meter:any={active:false,ws:[],commits:[],paint:[],raf:[],commands:[],applied:{},started:0,ended:0};(window as any).__labMeter=meter;
  const NativeSocket=window.WebSocket;
  window.WebSocket=class extends NativeSocket{constructor(url:string|URL,protocols?:string|string[]){super(url,protocols);this.addEventListener('message',event=>{
    let data:any;try{data=JSON.parse(event.data);}catch{return;}const now=performance.now();
    if(meter.active&&data.type==='sample'&&data.state?.phase==='running'&&meter.ws.length<2000)meter.ws.push(now);
    const receipts=data.receipts??(data.receipt?[data.receipt]:[]);for(const receipt of receipts){if(['applied','rejected'].includes(receipt.status)&&meter.applied[receipt.id]===undefined)meter.applied[receipt.id]=now;}
  });}};
  const nativeFetch=window.fetch.bind(window);window.fetch=async(input,init)=>{
    const isCommand=String(input).endsWith('/commands')&&init?.method==='POST';const start=performance.now();const response=await nativeFetch(input,init);
    if(isCommand&&meter.commands.length<64){const value=await response.clone().json();const command=JSON.parse(String(init?.body));meter.commands.push({id:command.id,kind:command.kind,started:start,ack_ms:performance.now()-start,http_status:response.status,ack_status:value.status});}
    return response;
  };
  let marker='';new MutationObserver(()=>{
    const element=document.querySelector('.world-region');const next=element?.getAttribute('data-display-run')+':'+element?.getAttribute('data-display-wall');
    if(!meter.active||next===marker||document.querySelector('.run-heading strong')?.textContent!=='running')return;marker=next;if(meter.commits.length>=2000)return;meter.commits.push(performance.now());requestAnimationFrame(time=>{if(meter.active&&meter.paint.at(-1)!==time)meter.paint.push(time);});
  }).observe(document,{subtree:true,attributes:true,attributeFilter:['data-display-wall']});
  function frame(time:number){if(meter.active&&meter.raf.length<2000)meter.raf.push(time);requestAnimationFrame(frame);}requestAnimationFrame(frame);
});}

export async function startMeter(page:Page){await page.evaluate(()=>{const meter=(window as any).__labMeter;meter.ws=[];meter.commits=[];meter.paint=[];meter.raf=[];meter.started=performance.now();meter.active=true;});}
export async function stopMeter(page:Page){return page.evaluate(()=>{const meter=(window as any).__labMeter;meter.active=false;meter.ended=performance.now();return {started:meter.started,ended:meter.ended,window_ms:meter.ended-meter.started,ws:meter.ws,commits:meter.commits,paint:meter.paint,raf:meter.raf};});}
export async function commandMetrics(page:Page){return page.evaluate(()=>(window as any).__labMeter.commands.map((command:any)=>({...command,applied_ms:(window as any).__labMeter.applied[command.id]===undefined?null:(window as any).__labMeter.applied[command.id]-command.started})));}
export function summarize(values:number[]){const sorted=[...values].sort((a,b)=>a-b);const percentile=(p:number)=>sorted.length?sorted[Math.max(0,Math.ceil(sorted.length*p)-1)]:null;return{count:values.length,p50:percentile(.5),p95:percentile(.95),p99:percentile(.99)};}
export function cadence(times:number[]){const intervals=times.slice(1).map((time,index)=>time-times[index]);return{count:times.length,hz:times.length>1?(times.length-1)*1000/(times.at(-1)!-times[0]):null,interval_ms:summarize(intervals)};}
export function windowRate(times:number[],started:number,ended:number){const duration=ended-started;return{count:times.length,window_ms:Number.isFinite(duration)?duration:null,hz:Number.isFinite(duration)&&duration>0?times.length*1000/duration:null};}
// Decided acceptance (manual lab refresh v4): keep 30 Hz emission; delivered
// display mean >= 29 Hz over the full window, p99 inter-sample gap <= 70 ms and
// command acknowledgement p95 < 150 ms. Missing data never passes.
export const CADENCE_ACCEPTANCE={emission_hz:30,display_mean_hz_min:29,interarrival_p99_ms_max:70,acknowledgement_p95_ms_below:150};
export function cadenceAcceptance(display:number[],started:number,ended:number,ackP95:number|null){
  const rate=windowRate(display,started,ended),gaps=cadence(display).interval_ms;
  const passed=rate.hz!==null&&rate.hz>=CADENCE_ACCEPTANCE.display_mean_hz_min&&gaps.p99!==null&&gaps.p99<=CADENCE_ACCEPTANCE.interarrival_p99_ms_max&&ackP95!==null&&ackP95<CADENCE_ACCEPTANCE.acknowledgement_p95_ms_below;
  return {mean_hz:rate.hz,interarrival_p50_ms:gaps.p50,interarrival_p99_ms:gaps.p99,acknowledgement_p95_ms:ackP95,passed};
}
