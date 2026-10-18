from pathlib import Path
import ast,json
root=Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-held-qualification-amendment-03')
parent=root/'scripts/qualify_puck_cpu_held_runtime.py';s=parent.read_text()
old="""            prior=decode(prior_raw);validate_configuration(prior)
            old_configuration=OUTPUTS['prepare']+'/configuration.json'"""
new="""            prior=decode(prior_raw);validate_configuration(prior)
            if config['version']==5:rows.append(prior['inputs']['candidate'])
            old_configuration=OUTPUTS['prepare']+'/configuration.json'"""
assert s.count(old)==1;s=s.replace(old,new)
old="""                    dependencies=decode(dependency_raw)
                    attached=attach_cpu_candidate(dependencies,blobs['candidate'],expected_sha256=config['inputs']['candidate']['sha256'],deadline=deadline)
                    if (attached!=dependencies or dependencies.get('distributions')!=source_reg['distributions']
                            or any(a.get('files')!=b['files'] for a,b in zip(dependencies['roots'],source_reg['roots']))):
                        raise ValueError('CPU prepared bytes/profile differ from accepted source plan')"""
new="""                    dependencies=decode(dependency_raw);expected=dependencies
                    if config['version']==5:
                        old_pin=prior['inputs']['candidate']
                        old_raw=read(ROOT/old_pin['path'],16*MiB,old_pin['sha256'])
                        if len(old_raw)!=old_pin['size_bytes']:raise ValueError('Historical candidate size differs')
                        validate_publication_candidate(decode(old_raw),candidate)
                        if (read(prepared/'control/candidate.json',16*MiB,old_pin['sha256'])!=old_raw
                                or attach_cpu_candidate(dependencies,old_raw,expected_sha256=old_pin['sha256'],deadline=deadline)!=dependencies):
                            raise ValueError('Historical candidate/prepared dependency profile differs')
                        expected=copy.deepcopy(dependencies)
                        expected['import_profile']=copy.deepcopy(candidate['import_profile'])
                    attached=attach_cpu_candidate(dependencies,blobs['candidate'],expected_sha256=config['inputs']['candidate']['sha256'],deadline=deadline)
                    if (attached!=expected or dependencies.get('distributions')!=source_reg['distributions']
                            or any(a.get('files')!=b['files'] for a,b in zip(dependencies['roots'],source_reg['roots']))):
                        raise ValueError('CPU prepared bytes/profile differ from accepted source plan')
                    if config['version']==5:
                        dependencies=attached;dependency_raw=canonical(attached)[:-1]"""
assert s.count(old)==1;s=s.replace(old,new)
ast.parse(s);parent.write_text(s)
audit=root/'scripts/audit_puck_cpu_held_runtime.py';s=audit.read_text()
marker="""        for folder,names in (('parent-source',SOURCES),('worker-source',WORKER)):
"""
assert s.count(marker)==1
insert="""        prepdata=data;prepblobs=blobs;prep_source=source;prep_dependency=dependency
        if config['version']==5:
            old_pin=prepconfig['inputs']['candidate']
            old_candidate,old_raw=held.json(root/old_pin['path'],old_pin,16*MiB)
            publication_candidate(old_candidate,data['candidate'])
            prepdata=dict(data,candidate=old_candidate);prepblobs=dict(blobs,candidate=old_raw)
            inputs_binding(prepconfig,prepdata,prepblobs)
            prep_source,prep_dependency,prep_dirs=plan(prepconfig,prepdata)
            expected=json.loads(canonical(prep_dependency));expected['import_profile']=dependency['import_profile']
            require(canonical(dependency)==canonical(expected) and source==prep_source and directories==prep_dirs,
                    'Publication05 physical/module projection differs from historical preparation')
"""
s=s.replace(marker,insert+marker)
s=s.replace("canonical(copy,False)==canonical(source,False),'Independent source file plan differs'", "canonical(copy,False)==canonical(prep_source,False),'Independent source file plan differs'")
s=s.replace("==blobs[role],'Retained preparation input differs'", "==prepblobs[role],'Retained preparation input differs'")
s=s.replace("sha256=sha(canonical(source,False))),candidate=dict(path='/puck/control/candidate.json',sha256=sha(blobs['candidate']))", "sha256=sha(canonical(prep_source,False))),candidate=dict(path='/puck/control/candidate.json',sha256=sha(prepblobs['candidate']))")
s=s.replace("canonical(dep,False)==canonical(dependency,False),'Independent staged dependency plan/profile differs'", "canonical(dep,False)==canonical(prep_dependency,False),'Independent staged dependency plan/profile differs'")
old="""        if phase=='qualify':
            require(held.file(base/'control/dependencies.json',maximum=16*MiB,raw=True)==depraw,'Qualification control dependency bytes differ')"""
new="""        historical_depraw=depraw
        if config['version']==5:dep=dependency;depraw=canonical(dependency,False)
        if phase=='qualify':
            require(held.file(base/'control/dependencies.json',maximum=16*MiB,raw=True)==depraw,'Qualification control dependency bytes differ')"""
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace("namespace_command(prepconfig,data,'prepare',stage_command)", "namespace_command(prepconfig,prepdata,'prepare',stage_command)")
marker="""    finally:held.close()
    require(len(os.listdir('/proc/self/fd'))==before"""
insert="""        if config['version']==5:
            report.update(historical_dependencies_sha256=sha(historical_depraw),current_dependencies_sha256=sha(depraw),
                historical_candidate_sha256=sha(prepblobs['candidate']),current_candidate_sha256=sha(blobs['candidate']))
"""
assert s.count(marker)==1;s=s.replace(marker,insert+marker)
ast.parse(s);audit.write_text(s)
