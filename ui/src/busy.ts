// Controls stay busy until every overlapping operation settles; a boolean reset
// by whichever finishes first re-enabled actions while Close run was in flight.
export function busyTracker(setBusy:(busy:boolean)=>void){
  let pending=0;
  return {async run<T>(work:()=>Promise<T>):Promise<T>{
    pending++;setBusy(true);
    try{return await work();}finally{pending--;if(pending===0)setBusy(false);}
  }};
}
