"""AUTHORED run of the Stage-3 guarded rehearsal tool over the authored project.

The tool characterizes unguarded, derives the profile through the real
derivation path, stages with the real stager and runs the real guarded v4
bootstrap for source then replay, all into scratch, never runs/.
"""
import json
from pathlib import Path
import secrets

import pytest

from puck_episode_authored import PYTHON, authored_scale, episode_project, run, write


def test_the_rehearsal_runs_both_guarded_workers_into_scratch(tmp_path):
    project=episode_project(tmp_path);authored_scale(project);root=project['root']
    generated=write(root,'docs/authored/generated/_authored_cpu_generated.py',b'AUTHORED_PROSPECTIVE_HELPER = True\n')
    write(root,'docs/authored/template-candidate.json',dict(kind='puck-cpu-observed-import-profile-candidate-v1',version=1,
        import_profile=dict(kind='puck-producer-import-profile-v2',version=2,exports=[],module_changes=[],native_origins=[],
            native_cache=[dict(name='_cython_authored',producer='authoredcy._creator',phase='module_exec',
                               delegate_attributes=['cython_function_or_method','generator'])]),
        additional_package_inputs=[dict(root='docs/authored/generated',files=[dict(generated,path='_authored_cpu_generated.py')])]))
    output=tmp_path/'rehearsal';stage='/tmp/puck-held-rehearsal-'+secrets.token_hex(6)
    code,stdout,stderr=run([PYTHON,'-I','-B',str(root/'scripts/rehearse_puck_held_episode.py'),'--site',str(project['site']),
        '--inventory',str(root/project['inputs']['inventory']['path']),'--layout',str(root/project['inputs']['layout']['path']),
        '--template',str(root/'docs/authored/template-candidate.json'),'--generated',str(root/'docs/authored/generated'),
        '--native',str(root/project['inputs']['native']['path']),'--baseline',str(root/project['inputs']['baseline']['path']),
        '--upstream',str(root/'upstream/fly-gym'),'--output',str(output),'--stage',stage],root,900)
    summary=json.loads((output/'rehearsal.json').read_bytes())
    assert code==0,(summary.get('error'),stderr[-3000:])
    assert summary['diagnostic_only'] is True and summary['allocation'] is False and not (root/'runs/puck-cpu-held-episode-16').exists()
    for phase in ('source','replay'):
        value=summary['phases']['episode_'+phase]
        assert value['supervision']['status']=='completed' and value['process_creation_attempts']==dict(count=0,events=[])
        assert value['entry_result']['phase']==phase and value['bundle']['members']>0
    assert summary['candidate']['native_cache'][0]['late_delegates']==[dict(attribute='fused_cython_function',
        producers=[dict(producer='authoredcy._fused',phase='module_exec')])]
    assert summary['candidate']['module_aliases']==[dict(name='_tools',target='authoredcy._tools')]
    # Allocation-16 style checks on the rehearsal outputs: the parent's receipt/bundle checks and the
    # episode auditor's internal recording, provenance, schedule, bundle and replay comparison checks.
    checks=summary['alloc16_checks']
    assert checks['parent_receipts']['status']=='passed',checks
    assert checks['auditor_internal']['status']=='passed',checks
    assert checks['auditor_internal']['detail']['compared_ticks']==48 and checks['auditor_internal']['detail']['first_divergence'] is None
    assert not Path(stage).exists()
