# python-louvain wheel build v1: fixed execution specification

This is one ordinary package/build preparation stage toward the active simulation
release goal. The result is one verified missing wheel. It grants no installation,
numerical runtime, collection, model, renderer, physics, scientific or held-out use.
The earlier [design proposal](puck-python-louvain-build-v1-proposal.md) remains
historical. Existing actual allocations remain consumed. This specification and
its exact source/configuration require independent review before invocation.

## Observable exit

Accept only python_louvain-0.16-py3-none-any.whl built from the unchanged
204,641-byte source archive with SHA256
b7ba2df5002fd28d3ee789a49532baad11fe648e4f2117cf0798e7520a1da56b.
Require complete payload/CRC/METADATA/WHEEL/RECORD verification, its actual size
and digest, exact networkx/numpy requirement declarations, unchanged staged
source/backend/fixture bytes and trusted host baseline, normal return within the
allocation, and no matching process-group survivors. An independent terminal
outcome audit must inspect the retained raw inputs, commands, logs and wheel.
Require externally observed parent exit zero. The final normal-deadline check
includes outcome publication, guard teardown and flushed stdout; a late or
nonzero return overrides any earlier wheel_verified artifact result.
A fixture or verified backend alone does not close this exit.

## Exact route

The executable configuration is puck-python-louvain-build-01.json. Its own SHA256
is supplied on the command line; its source capsule pins the parent, worker,
inert staging/verifier/supervisor code, this specification and unchanged project
manifests. It also pins the full trusted host baseline JSON and source archive.
Run the pinned CPython3.11.15 with -I -S -B. The parent starts a dedicated process
group and outer hard guard before configuration/preflight work.

1. Verify the configuration, exact source capsule and resources. Check the entire
   declared trusted Python prefix, external libraries and bubblewrap executable.
   Exclusively reserve runs/puck-python-louvain-build-01; preserve partial files
   on any failure. Reusing this output is refused, with no retry/rescue loop.
2. Make a byte-identical source-archive copy. Acquire exactly the setuptools84.0.0
   wheel named in the configuration, through one direct HTTPS request with no
   proxies, redirects or dependency resolution. Verify its archive, advertised
   metadata digest, every member and complete RECORD before inert staging.
3. Extract the source and backend into fresh disjoint directories. Source parsing
   counts physical tar headers, permits only regular files/directories and the
   actual source's one-record per-entry PAX mtime metadata (ignored). Refuse path
   rewriting, links, special files, aliases, collisions and expansion overflow.
   Backend staging preserves verified wheel paths, including inert .pth bytes;
   .data relocation is unsupported. No package startup hooks run during staging.
4. Run an authored namespace probe, with no backend import. Prove a different
   network namespace with no external route, hidden host project, empty HOME,
   read-only source/backend/Python/root/proc/dev, exact scratch capacity, isolated
   Python flags and denial of every listed process/session/exec syscall.
5. Build one authored fixture with the exact backend and same read-only source
   route. Its package and script raise if imported/executed; a deliberately absent
   declared dependency must not be installed. Verify its sole wheel, then recheck
   all staged inputs. This checks real backend write routing before target setup.
6. Build the real source once through setuptools.build_meta.build_wheel. Global
   options direct build-base to /work/build and egg-base to /work/egg; bdist-dir
   is /work/bdist and wheel output is /work/wheel-output. Do not add a pyproject or
   modify source inputs. Reject target community, NumPy, NetworkX, Torch,
   torchvision, MuJoCo and fixture-package imports before backend execution.
7. Return one bounded JSON/base64 wheel over stdout. Parent publishes exclusive
   stable file names and verifies the wheel with the existing full-payload API.
   Recheck all staged trees, source custody, complete trusted host baseline and
   retained output size. Publish terminal outcome and stop. A failed preflight
   prevents target invocation; every failure remains a failed retained stage.

## Namespace and resource contract

The bubblewrap route uses unshare-all, disable-userns, cap-drop ALL,
die-with-parent and clearenv. Mount only the exact read-only Python prefix at its
original absolute path, seven exact declared Python loader/glibc files, three
host library aliases, read-only source/backend/worker, private read-only proc/dev,
and private writable /work. Remount the root read-only; /tmp points into /work.
Set only HOME, TMPDIR, PATH=/nonexistent, LC_ALL, LANG, TZ and
SOURCE_DATE_EPOCH=1720000000. No host credentials, project or home tree is mounted.

The fixed x86_64 seccomp filter checks audit architecture, kills alternate/x32
ABI use and returns EPERM for clone56, fork57, vfork58, execve59, ptrace101,
setpgid109, setsid112, unshare272, setns308, execveat322 and clone3 435. It is
installed before backend code; the authored probe calls all eleven denied
syscalls. This prevents the build worker from creating descendants or escaping
PGID sampling. The supervisor already creates a dedicated session, so the inner
bubblewrap invocation omits new-session. The namespace's init and launcher remain
trusted. This is one fixed Linux x86_64 pure-Python build, not a general sandbox.

| Resource | Fixed boundary |
| --- | --- |
| Whole stage | 120s normal return, 135s hard guard; one invocation, no automatic retry |
| Worker group | At most3 processes; combined parent/group RSS stop at768MiB, sampled every50ms |
| Worker kernel limits | 512MiB address space,60s CPU,8MiB regular file,128 FDs, zero core dump |
| Mutable build storage | Private tmpfs /work, hard capacity256MiB; no host-writable build bind |
| Retained output | At most128MiB; staged source16MiB decoded, backend64MiB decoded |
| Source archive | At most2MiB raw,512 physical headers,2MiB/member,16MiB decoded including padding |
| Backend archive | Exactly818,216B; staging refuses above2MiB;4096 members,16MiB/member,4MiB metadata |
| Wheel transport | At most256KiB compressed; default1MiB retained log prefix per stream |
| Target/fixture wheel verification | At most256 members,2MiB decoded total,512KiB/member and metadata |
| Network | One exact backend URL,20s socket timeout; build namespace has no external route |
| Admission floors | At least2GiB free project disk and1GiB MemAvailable, checked before reservation |

The wheel transfer cap is tighter than the preliminary8MiB proposal: this fixed
source is small, and256KiB fits the existing bounded log transport without
changing its API. Backend chatter goes to stderr. The supervisor scans only
stable per-stage log/control directories; source/tools are read-only and all
mutable backend scratch remains in the quota-limited private tmpfs. No monitor
walk races backend temporary-file creation/removal.

The whole-stage hard guard bounds parent preparation and publication, including
network waits. Kernel worker limits and tmpfs quotas complement sampled
operational RSS/process checks; sampled maxima are not hard memory/WCET proofs.
A hard-killed parent may lack an outcome.json; the terminal audit must treat
missing or partial evidence as failure rather than manufacture a passing receipt.

## Trusted host baseline and remaining work

puck-python-louvain-host-baseline-v1.json records4,233 regular prefix files /
90,314,007B and1,048 internal symlinks, plus nine actual external library files and
bubblewrap. Only seven Python loader/glibc files are mounted inside; libcap and
libgcc_s support launching bubblewrap outside. Prefix inventories/hashes and all
external bytes are checked before/after. Parent-side Python/stdlib, kernel and
host filesystem stability during execution remain trusted assumptions. These
before/after hashes are not the stricter numerical runtime's held native-identity
qualification. Optional crypt/Tk closure remains unestablished and is not claimed.

The full prefix includes existing site-packages; -I -S -B prevents inherited site
startup, and backend paths are inserted explicitly. The build imports the
verified setuptools tool and executes reviewed setup.py. It does not import the
target package or install its numerical requirements. No dependency resolver,
pip, external build frontend, compiler, shell or numerical package is needed.

Versioned API references: [setuptools84 build_meta](https://raw.githubusercontent.com/pypa/setuptools/v84.0.0/setuptools/build_meta.py),
[bubblewrap0.12 README](https://raw.githubusercontent.com/containers/bubblewrap/v0.12.0/README.md),
and [Linux seccomp filter API](https://www.kernel.org/doc/html/latest/userspace-api/seccomp_filter.html).
The actual local header constants and authored denial check cover this fixed ABI.

After acceptance of the built wheel, measure the complete installed namespace,
retain licence contents and finish native/EGL/tmpfs custody and the executable
four-import qualification configuration. Installation and an actual successful
runtime qualification still precede the simulator episode. This build stage
changes none of the seven simulation release gates or33 requirement statuses.
