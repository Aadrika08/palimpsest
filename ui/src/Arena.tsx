import type {World,Intervention} from './protocol';
export default function Arena({world,trace=[],other,preview,emptyText}:{world?:World;trace?:number[][];other?:number[][];preview?:Intervention;emptyText?:string}) {
  if(!world) return <div className="arena-empty">{emptyText?<p>{emptyText}</p>:<><p>The arena will appear when the worker has loaded.</p><p>Create a run or open recorded playback.</p></>}</div>;
  const a=world.arena, view=a*2, path=(points:number[][])=>points.map(p=>`${p[0]},${-p[1]}`).join(' ');
  return <figure className="arena"><svg role="img" aria-label="Top-down arena with actual rover position, obstacles, goal and recorded route" viewBox={`${-a} ${-a} ${view} ${view}`}>
    <defs><pattern id="grid" width="1" height="1" patternUnits="userSpaceOnUse"><path d="M 1 0 L 0 0 0 1" fill="none" stroke="#d7e2e8" strokeWidth=".012"/></pattern></defs>
    <rect x={-a} y={-a} width={view} height={view} fill="url(#grid)" stroke="#203444" strokeWidth=".035"/>
    <path d={`M ${-a} 0 H ${a} M 0 ${-a} V ${a}`} stroke="#bacbd6" strokeWidth=".015"/>
    {world.obstacles.map(([x,y,r],i)=><g key={i}><circle cx={x} cy={-y} r={r} fill="#203444" opacity=".8"/><text x={x} y={-y+.09} textAnchor="middle" fill="white" fontSize=".26">{i}</text></g>)}
    <circle cx={world.goal[0]} cy={-world.goal[1]} r={world.goal[2]} fill="#8b5b12" fillOpacity=".2" stroke="#8b5b12" strokeWidth=".04"/>
    <path d={`M ${world.goal[0]-.16} ${-world.goal[1]} h .32 M ${world.goal[0]} ${-world.goal[1]-.16} v .32`} stroke="#8b5b12" strokeWidth=".04"/>
    <polyline points={path(trace)} fill="none" stroke="#245b84" strokeWidth=".06" strokeLinejoin="round"/>
    {other && <polyline points={path(other)} fill="none" stroke="#9a4265" strokeWidth=".06" strokeDasharray=".18 .12"/>}
    <g transform={`translate(${world.pose[0]} ${-world.pose[1]}) rotate(${-world.pose[2]*180/Math.PI})`}><circle r=".3" fill="white" stroke="#245b84" strokeWidth=".05"/><path d="M -.14 -.15 L .3 0 L -.14 .15 Z" fill="#245b84"/></g>
    {preview && <g><circle cx={preview.xy[0]} cy={-preview.xy[1]} r=".35" fill="none" stroke="#9a4265" strokeWidth=".055" strokeDasharray=".12 .08"/><path d={`M ${preview.xy[0]-.2} ${-preview.xy[1]} h .4 M ${preview.xy[0]} ${-preview.xy[1]-.2} v .4`} stroke="#9a4265" strokeWidth=".04"/></g>}
  </svg><figcaption>World coordinates (m) · solid blue: recorded route{other?' · dashed berry: comparison route':''}{preview?' · dotted marker: advisory edit preview':''}</figcaption></figure>;
}
