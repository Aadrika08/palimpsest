let token: string | undefined;
export async function session(refresh=false):Promise<string> {
  if (!token||refresh) {const response=await fetch('/api/v1/session',{cache:'no-store'}); if(!response.ok) throw new Error(`Session failed (${response.status})`); const data=await response.json(); token=data.token;}
  if (!token) throw new Error('The server did not provide a session token.');
  return token;
}
export async function request<T>(path:string, body?:unknown):Promise<T> {
  const response=await fetch(`/api/v1${path}`,{method:body===undefined?'GET':'POST',headers:{'X-Palimpsest-Session':await session(),...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body),cache:'no-store'});
  const data=await response.json().catch(()=>({detail:`HTTP ${response.status}`}));
  if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail??data));
  return data;
}
export async function download(path:string,filename:string) {
  const target=new URL(path,location.origin);
  if(target.origin!==location.origin || !target.pathname.startsWith('/api/v1/artifacts/')) throw new Error('Invalid artifact download URL.');
  const response=await fetch(target,{headers:{'X-Palimpsest-Session':await session()}});
  if(!response.ok) throw new Error(`Download failed (${response.status}).`);
  const url=URL.createObjectURL(await response.blob()); const link=document.createElement('a'); link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
