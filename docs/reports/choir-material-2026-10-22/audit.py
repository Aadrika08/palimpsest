import hashlib,json,struct,wave
from pathlib import Path
from collections import Counter
import numpy as np
from palimpsest.records import iter_ticks
from record_choir_material import pins
root=Path('runs/choir-material-2026-10-22-v1')
cfg=json.loads((root/'registration.json').read_text());run=root/cfg['run_id']
assert pins()==cfg['sources']
b=(root/'choir.wav').read_bytes();p=12
while p<len(b):
 kind,n=struct.unpack_from('<4sI',b,p)
 if kind==b'plmp': m=json.loads(b[p+8:p+8+n]);break
 p+=8+n+n%2
for item in m['source']['files']:
 path=run/item['path']
 assert path.stat().st_size==item['size_bytes']
 with path.open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==item['sha256']
with wave.open(str(root/'choir.wav'),'rb') as w:
 assert (w.getnframes(),w.getframerate(),w.getnchannels(),w.getsampwidth())==(5760000,48000,1,2)
 pcm=w.readframes(5760000)
assert hashlib.sha256(pcm).hexdigest()==m['pcm_sha256']
expected=hashlib.sha256(); total=0; selected=Counter(); peak=0.;square=0.
for i,row in enumerate(iter_ticks(run/'recording')):
 total+=1
 if i>=6000: continue
 selected[row['episode']]+=1
 pos=np.arange(i*960,(i+1)*960,dtype=np.float64)
 signal=sum(.25*float(row['population_stats'][j,1])*np.sin(2*np.pi*f*pos/48000) for j,f in enumerate((220.,330.,440.)))
 data=np.rint(32767*signal).astype('<i2').tobytes()
 assert pcm[i*1920:(i+1)*1920]==data
 expected.update(data)
 values=np.frombuffer(data,dtype='<i2').astype(float)/32768
 peak=max(peak,float(np.max(np.abs(values))));square+=float(np.sum(values**2))
assert total==6004 and expected.hexdigest()==m['pcm_sha256']
segments=m['timing']['segments'];assert len(segments)==18 and m['timing']['final_episode_prefix']
for segment in segments:
 assert selected[segment['episode']]==segment['end_tick_inclusive']-segment['start_tick']+1
 assert segment['output_end_sample_exclusive']-segment['output_start_sample']==selected[segment['episode']]*960
assert segments[-1]['output_end_sample_exclusive']==5760000
outcomes=Counter()
for line in (run/'recording/events.jsonl').read_text().splitlines():
 e=json.loads(line)
 if e['kind']=='episode_finished': outcomes[e['outcome']['reason']]+=1
assert pins()==cfg['sources']
result={'status':'passed','source_intervals':total,'selected_intervals':6000,'episodes':18,'outcomes':dict(outcomes),'source_bytes':sum(i['size_bytes'] for i in m['source']['files']),'wav_bytes':len(b),'pcm_sha256':m['pcm_sha256'],'pcm_byte_exact':True,'peak_dbfs':float(20*np.log10(peak)) if peak else None,'rms_dbfs':float(20*np.log10((square/5760000)**.5)) if square else None,'final_episode_prefix':True,'source_pins_unchanged':True}
(root/'independent-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
