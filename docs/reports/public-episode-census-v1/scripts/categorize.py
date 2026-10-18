"""Diagnostic only: classify an episode census against the registered roster.

needs_registration: non-stdlib modules executed (loaded) from the held site (or
  native-created, no file) that are not registered dependency modules.
local_source: palimpsest/upstream modules executed (need local source registration).
needs_declared_absence: non-stdlib requests no finder resolved, beyond the 32 v5 absent names.
hidden_candidates: non-stdlib, unregistered names requested, resolved, but never loaded.
"""
import collections, json, sys

CENSUS, REG, OUT = sys.argv[1:4]
V5_ABSENT = sorted('''OpenGL_accelerate accimage av backports_abc colorama defusedxml dill flint fx2trt_oss gmpy
gmpy2 hypothesis monkeytype numpy._distributor_init_local onnx onnx_tf onnxruntime opt_einsum org pydot pynvml
tabulate tensorflow tensorrt torch._rocm_init torch2trt torchdistx tqdm tree triton tvm xarray'''.split())
V5_HIDDEN = ['networkx', 'pandas', 'sklearn', 'torch.utils._cxx_pytree']
d = json.load(open(CENSUS))
reg = json.load(open(REG))
registered = {r['name'] for r in reg['modules']} | {r['name'] for r in reg['namespaces']}
stdlib = set(sys.stdlib_module_names)
FOUR = ('import.numpy', 'import.torch', 'import.torchvision', 'import.mujoco')

executed = {}
for phase, rows in d['loaded_by_phase'].items():
    for name, origin in rows:
        executed.setdefault(name, (phase, origin))


def caller(name):
    r = d['requests'].get(name)
    return r['stack'][:3] if r else None


need_reg = {n: v for n, v in executed.items()
            if v[1].split(':')[0] in ('site', 'nofile', 'other') and n not in registered
            and n.split('.')[0] not in stdlib}
local = sorted(n for n, v in executed.items() if v[1] in ('src', 'upstream'))
by_top = collections.defaultdict(list)
for n, (phase, origin) in sorted(need_reg.items()):
    by_top[n.split('.')[0]].append(n)
reg_summary = {}
for top, names in sorted(by_top.items()):
    phases = collections.Counter(need_reg[n][0] for n in names)
    first = min(names, key=lambda n: (n.count('.'), n))
    reg_summary[top] = dict(count=len(names), phases=dict(phases), first=first, caller=caller(first),
                            origins=dict(collections.Counter(need_reg[n][1].split(':')[0] for n in names)))
misses = d['non_stdlib_misses']
absent_new = {n: dict(phase=r['phase'], caller=r['stack'][:3]) for n, r in sorted(misses.items()) if n not in V5_ABSENT}
absent_declared_seen = sorted(n for n in misses if n in V5_ABSENT)
hidden = {}
for n in d['resolved_not_loaded']:
    if n.split('.')[0] in stdlib or n in registered:
        continue
    r = d['requests'][n]
    hidden[n] = dict(phase=r['phase'], caller=r['stack'][:3], n=r['n'])
out = dict(kind='diagnostic-episode-census-categories-v1', diagnostic_only=True, census=CENSUS,
           registered_modules=len(registered),
           needs_registration=dict(total=len(need_reg), outside_four_imports=sum(1 for v in need_reg.values() if v[0] not in FOUR),
                                   by_top=reg_summary, names=sorted(need_reg)),
           local_source_modules=local,
           needs_declared_absence_new=absent_new, v5_absent_requested=absent_declared_seen,
           v5_absent_not_requested=sorted(set(V5_ABSENT) - set(misses)),
           hidden_candidates=hidden,
           v5_hidden_in_requests=sorted(n for n in V5_HIDDEN if n in d['requests']))
json.dump(out, open(OUT, 'w'), indent=1)
print(json.dumps(dict(needs_registration_total=len(need_reg), by_top={k: (v['count'], v['first'], v['caller'], v['phases']) for k, v in reg_summary.items()},
                      local=local, absent_new=absent_new, hidden=hidden,
                      v5_absent_not_requested=out['v5_absent_not_requested'], v5_hidden_in_requests=out['v5_hidden_in_requests']), indent=1))
