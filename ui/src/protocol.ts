export type Phase = 'loading'|'paused'|'running'|'terminated'|'truncated'|'stopped'|'failed'|'playback';
export type Profile = {id:string; label:string; description:string; available?:boolean; reason?:string; privileged?:boolean;scenarios?:string[];textures?:string[];devices?:string[]};
export type Profiles = {scenarios:Profile[];controllers:Profile[];textures:Profile[]};
export type Receipt = {id:string;status:string;kind?:string;tick?:number;episode?:number;reason?:string;error?:string;[key:string]:unknown};
export type State = {run_id?:string;phase:Phase;controller?:string;episode:number;total_tick:number;episode_step:number;revision:number;simulation_time?:number;eyes?:{left:boolean;right:boolean};last_outcome?:unknown;metrics?:Record<string,unknown>;receipts?:Receipt[]|Record<string,Receipt>;[key:string]:unknown};
export type World = {arena:number;pose:[number,number,number];obstacles:[number,number,number][];goal:[number,number,number]};
export type Population = {name:string;count:number;mean:number;min:number;max:number;scale:[number,number]};
export type RunPerformance = {active_wall_seconds:number;advanced_simulation_seconds:number;rtf:number|null};
export type Sample = {version:1;type:'sample';run_id:string;mode:'live'|'playback';state:State;world:World;inputs:{episode:number;tick:number;stage:'used'|'next'|'pending-memory'|'pending-task';cam_left:string;cam_right:string;sensors:(number|null)[];eyes:{left:boolean;right:boolean}};transition:null|{episode:number;tick:number;action:number[];control:number[];raw_output?:number[];populations:Population[];latency:number;step_latency:number};trace:number[][];wall_elapsed:number|null;performance?:RunPerformance;branch_origin?:unknown;memory?:MemoryView|null;task?:Record<string,unknown>|null};
export type RunStatus = {run_id:string;status?:string;state?:State|null;sample?:Sample|null;error?:string;failure?:unknown;receipts?:Receipt[];snapshots?:Snapshot[];initial_snapshot_id?:string;job?:'replay';replay_mode?:'actions'|'policy';jobstate?:'loading'|'running'|'paused'|'completed'|'canceled'|'failed';underlying_state?:State|null;replay?:unknown};
export type RunSummary = {run_id:string;controller?:string;scenario?:string;status?:string;[key:string]:unknown};
export type Event = {type?:string;kind?:string;tick?:number;episode?:number;[key:string]:unknown};
export type Intervention = {kind:'move_goal';xy:[number,number]}|{kind:'move_obstacle';index:number;xy:[number,number]};
export type Command = {id:string;kind:string;expected_state:Phase;expected_episode:number;expected_revision:number;payload?:unknown};
export type Compare = {differences:unknown;left:unknown;right:unknown;metrics?:unknown;events?:unknown;[key:string]:unknown};
export type Snapshot = {run_id:string;snapshot_id:string;revision:number;initial?:boolean;episode?:number;tick?:number};

export type MemoryView = {episode_id:string;tick:number|null;hashes:{m:string;e:string;u:string};counts:{facts:number;episodes:number;requests:number};u:Record<string,unknown>;facts:{id:string;estimate:string|null;status:string;revision:number;evidence:unknown}[];facts_truncated:number;active:unknown;recent_decisions:unknown[]};
