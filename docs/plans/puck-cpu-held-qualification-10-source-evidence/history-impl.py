from pathlib import Path
import ast
import hashlib
import json

root=Path('/home/utkarsh/.codex/worktrees/0071/brain')
path=root/'docs/plans/puck-cpu-held-qualification-10-admission.py'
text=path.read_text()
assert 'def check_consumed09' not in text
start=text.index('HISTORICAL08_JSON={')
end=text.index('\n\ndef resources(',start)
block=text[start:end]
function=block[block.index('def check_consumed08'):]
for old,new in [
    ('HISTORICAL08_JSON','HISTORICAL09_JSON'),('check_consumed08','check_consumed09'),
    ('puck-cpu-held-qualification-08','puck-cpu-held-qualification-09'),('held08','held09'),
    ('puck-cpu-held-runtime-allocation-v8','puck-cpu-held-runtime-allocation-v9'),
    ("config['version']==8","config['version']==9"),("config['allocation_id']==8","config['allocation_id']==9"),
    ('pid=3996069,start_ticks=54384185','pid=104005,start_ticks=55289090'),
    ('pid=3996070,start_ticks=54384185','pid=104006,start_ticks=55289091'),
    ('pid=3996071,start_ticks=54384186','pid=104007,start_ticks=55289092'),
    ('size_bytes=1469','size_bytes=11086'),
    ('12fd091b446124bfd8c40a8ef0b962b81b7e3bbc0c94b716736cc3fddf34ca3f','c548022a96e5cc22dfb8bbd9d9bb5c0c0ef446dc5a662401dc3e91bc06714a61'),
    ('0406bfa94f6b230fca440d57f65e5d429a30d70d054e2cdd29bafb0da1ca2b35','dffcec25696948da18b18abda32dae764fa933a1175c622f45d33a3bca27d234'),
    ("'],616,145,audit_command)","'],617,145,audit_command)")
]:
    function=function.replace(old,new)
old_dict=text[start:text.index('\n\ndef check_consumed08',start)]
keys=list(ast.literal_eval(old_dict.split('=',1)[1]))
values={}
for key in keys:
    key=key.replace('puck-cpu-held-qualification-08','puck-cpu-held-qualification-09').replace('held08','held09')
    values[key]=hashlib.sha256((root/key).read_bytes()).hexdigest()
new_block='HISTORICAL09_JSON='+repr(values)+'\n\n\n'+function
text=text[:end]+'\n\n'+new_block+text[end:]
assert text.count("('07','08')")==2
text=text.replace("('07','08')","('07','08','09')")
text=text.replace('raw_paths.update(HISTORICAL08_JSON)','raw_paths.update(HISTORICAL08_JSON)\n            raw_paths.update(HISTORICAL09_JSON)')
text=text.replace('consumed08=check_consumed08(held)','consumed08=check_consumed08(held)\n            consumed09=check_consumed09(held)')
text=text.replace('(3996071,54384186)]:','(3996071,54384186),(104005,55289090),(104006,55289091),(104007,55289092)]:')
text=text.replace('nine recorded identities only','twelve recorded identities only')
text=text.replace('qualifications01_02_03_04_05_06_07_08_still_failed_consumed','qualifications01_02_03_04_05_06_07_08_09_still_failed_consumed')
text=text.replace('qualification09_invoked=False','qualification09_invoked=True,qualification10_invoked=False')
text=text.replace('qualification08_failure=consumed08,','qualification08_failure=consumed08,qualification09_failure=consumed09,')
compile(text,str(path),'exec')
path.write_text(text)
print(json.dumps(dict(new_history09=True,historical_missing_receipts=16,process_samples=12,admission_or_runtime_invoked=False)))
