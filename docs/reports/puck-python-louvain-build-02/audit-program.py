#!/usr/bin/env python3
"""Independent, stdlib-only terminal evidence audit; never builds or installs.

Run only after the orchestrator explicitly declares the one build terminal.
The sole write is an exclusively created JSON report at --report. No project
module, backend, wheel payload or target package is imported or executed.
"""
import argparse
import ast
import base64
import csv
from email import policy
from email.parser import BytesParser
import gzip
import hashlib
import io
import itertools
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import sys
import tarfile
import time
import zipfile
import zlib

MIB = 1024 ** 2
CONFIG_PATH = "docs/plans/puck-python-louvain-build-02.json"
OUTPUT_PATH = "runs/puck-python-louvain-build-02"
BASELINE_PATH = "docs/plans/puck-python-louvain-host-baseline-v1.json"
SOURCE_PATH = "runs/puck-cpu-payload-acquisition-01/archives/python-louvain-0.16.tar.gz"
SOURCE_SHA = "b7ba2df5002fd28d3ee789a49532baad11fe648e4f2117cf0798e7520a1da56b"
PYTHON_PREFIX = "/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu"
INTERPRETER = PYTHON_PREFIX + "/bin/python3.11"
TARGET_NAME = "python_louvain-0.16-py3-none-any.whl"
FIXTURE_NAME = "palimpsest_build_fixture-0.0-py3-none-any.whl"
DENIED = [56, 57, 58, 59, 101, 109, 112, 272, 308, 322, 435]
FORBIDDEN = {"community", "numpy", "networkx", "torch", "torchvision", "mujoco", "fixture_package"}
FALSE = dict(installed=False, runtime_qualified=False, collection_authorized=False,
             study_authorized=False, numerical_runtime_authorized=False, qualification_claims=[])
LIMITS = dict(normal_seconds=120, hard_seconds=135, socket_seconds=20,
    rss_bytes=768*MIB, output_bytes=128*MIB, scratch_bytes=256*MIB,
    min_free_bytes=2048*MIB, min_available_ram_bytes=1024*MIB,
    max_members=4096, max_uncompressed_bytes=64*MIB, max_member_bytes=16*MIB,
    max_metadata_bytes=4*MIB, max_wheel_bytes=256*1024,
    log_bytes_per_stream=MIB, max_processes=3, max_worker_fds=128,
    worker_address_space_bytes=512*MIB, worker_cpu_seconds=60, worker_file_bytes=8*MIB)
BACKEND = dict(name="setuptools", version="84.0.0", filename="setuptools-84.0.0-py3-none-any.whl",
    url="https://files.pythonhosted.org/packages/95/9c/c510029fc6ef33a6275cd2c5d3cecd6613dfd6aa401d57c54f1c18852ccf/setuptools-84.0.0-py3-none-any.whl",
    size_bytes=818216, sha256="51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670",
    metadata_sha256="3ef2975718dd31cabdd5829455e9b868ca14dbf79ed8fed2de0af4e87347006e", format="wheel")
SOURCE_CAPSULE = sorted(["docs/plans/puck-python-louvain-build-v1.md",
    "docs/plans/puck-python-louvain-build-v2.md", "pyproject.toml",
    "scripts/acquire_puck_cpu_payloads.py", "scripts/build_puck_python_louvain.py",
    "scripts/puck_python_louvain_worker.py", "src/palimpsest/__init__.py",
    "src/palimpsest/bounded_qualification.py", "src/palimpsest/evaluate.py",
    "src/palimpsest/puck_build_inputs.py", "src/palimpsest/puck_execution_files.py",
    "src/palimpsest/puck_package_payloads.py", "uv.lock"])
SYSTEM_FILES = ["/usr/lib/ld-linux-x86-64.so.2", "/usr/lib/libc.so.6", "/usr/lib/libdl.so.2",
    "/usr/lib/libm.so.6", "/usr/lib/libpthread.so.0", "/usr/lib/librt.so.1", "/usr/lib/libutil.so.1"]
ALIASES = [["/lib", "usr/lib"], ["/lib64", "usr/lib"], ["/usr/lib64", "lib"]]
FIXTURE_FILES = {
    "setup.py": b'from setuptools import setup\nsetup(name="palimpsest-build-fixture", version="0.0", packages=["fixture_package"], scripts=["bin/fixture"], install_requires=["not-installed-for-fixture>=1"])\n',
    "setup.cfg": b"[egg_info]\ntag_build =\ntag_date = 0\n",
    "fixture_package/__init__.py": b"raise RuntimeError('fixture package must never import')\n",
    "bin/fixture": b"#!/usr/bin/env python\nraise RuntimeError('fixture script must never execute')\n"}
IDENTITIES = {}
LINKS = {}
START = time.monotonic()
DEADLINE = START + 20
AUDIT = dict(kind="puck-python-louvain-independent-terminal-audit-v1", version=1,
    status="FAIL", wheel_accepted=False, findings=[], checks=[], **FALSE)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def tick(deadline=None):
    require(time.monotonic() < (DEADLINE if deadline is None else min(DEADLINE, deadline)),
            "independent audit deadline exceeded")


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode()


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("nonfinite JSON number: " + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def identity(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def rel(name, directory=False):
    require(type(name) is str and name, "empty or nonstring relative path")
    bare = name[:-1] if directory and name.endswith("/") else name
    require(bare and "\\" not in name and not any(ord(c) < 32 or 127 <= ord(c) < 160 for c in name),
            "unsafe relative path: " + repr(name))
    require(all(p not in ("", ".", "..") for p in bare.split("/")), "noncanonical path: " + name)
    return bare


def ancestors(path):
    require(path.is_absolute() and all(p not in (".", "..") for p in path.parts), "noncanonical absolute path")
    for parent in reversed(path.parents):
        require(stat.S_ISDIR(parent.lstat().st_mode), "symlink/special ancestor: " + str(parent))


def read_file(path, cap=64*MIB, expected=None, single=True, retain=True, track=True, deadline=None):
    tick(deadline)
    ancestors(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= cap and (not single or before.st_nlink == 1),
                "not a bounded regular file with required links: " + str(path))
        digest, count, chunks = hashlib.sha256(), 0, []
        while True:
            tick(deadline)
            block = os.read(fd, min(128*1024, cap + 1 - count))
            if not block:
                break
            count += len(block)
            require(count <= cap, "file grew above cap: " + str(path))
            digest.update(block)
            if retain:
                chunks.append(block)
        require(count == before.st_size and identity(before) == identity(os.fstat(fd)) == identity(path.lstat()),
                "file changed during independent read: " + str(path))
        row = dict(size_bytes=count, sha256=digest.hexdigest())
        if expected is not None:
            require(row == {k: expected[k] for k in ("size_bytes", "sha256")}, "pinned file differs: " + str(path))
        if track:
            old = IDENTITIES.setdefault(str(path), identity(before))
            require(old == identity(before), "file changed between audit reads: " + str(path))
        return (b"".join(chunks) if retain else None), row
    finally:
        os.close(fd)


def control(path):
    return parse(read_file(path, MIB)[0])


def check(label, function):
    tick()
    try:
        value = function()
        AUDIT["checks"].append(dict(check=label, passed=True))
        return value
    except Exception as error:
        AUDIT["checks"].append(dict(check=label, passed=False))
        AUDIT["findings"].append(dict(check=label, type=type(error).__name__, message=str(error)))
        return None


def claims(value, label):
    for key, expected in FALSE.items():
        require(key in value and type(value[key]) is type(expected) and value[key] == expected,
                label + " has a false-authority flag mismatch: " + key)


def descriptor(value):
    require(type(value) is dict and set(value) == {"path", "size_bytes", "sha256"}, "descriptor fields differ")
    rel(value["path"])
    require(type(value["size_bytes"]) is int and 0 <= value["size_bytes"] <= 64*MIB,
            "invalid descriptor size")
    require(type(value["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]), "invalid SHA256")


def finite_number(value, low=0, high=None):
    return type(value) in (int, float) and math.isfinite(value) and value >= low and (high is None or value < high)


def process_scan(config_sha, root, groups=()):
    live_groups, exact_routes, unreadable = [], [], []
    root_parent = os.fsencode(str(root / "scripts/build_puck_python_louvain.py"))
    worker_path = os.fsencode(str(root / "scripts/puck_python_louvain_worker.py"))
    for proc in Path("/proc").iterdir():
        tick()
        if not proc.name.isdecimal() or int(proc.name) == os.getpid():
            continue
        try:
            fields = (proc / "stat").read_text().rsplit(")", 1)[1].split()
            if fields[0] in ("Z", "X"):
                continue
            argv = (proc / "cmdline").read_bytes().split(b"\0")
            pid = int(proc.name)
            if int(fields[2]) in groups:
                live_groups.append(dict(pid=pid, pgid=int(fields[2])))
            parent_script = any(v == root_parent or v == b"scripts/build_puck_python_louvain.py"
                or v.endswith(b"/build_puck_python_louvain.py") for v in argv)
            configuration_token = any(v == CONFIG_PATH.encode() or v == os.fsencode(str(root / CONFIG_PATH)) for v in argv)
            parent = (parent_script and b"--configuration" in argv and b"--sha256" in argv
                and configuration_token and config_sha.encode() in argv)
            worker = (worker_path in argv or (b"/driver.py" in argv and any(v in argv
                for v in (b"probe", FIXTURE_NAME.encode(), TARGET_NAME.encode()))))
            if parent or worker:
                exact_routes.append(dict(pid=pid, route="parent" if parent else "worker"))
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError:
            unreadable.append(int(proc.name))
    result = dict(live_group_members=live_groups, live_exact_routes=exact_routes,
                  unreadable_proc_entries=unreadable, groups=sorted(groups))
    require(not live_groups and not exact_routes, "matching build process group/route still lives: " + repr(result))
    require(not unreadable, "cannot establish absence of matching processes through unreadable /proc entries")
    return result


def load_config(root, sha):
    raw, row = read_file(root / CONFIG_PATH, 4*MIB)
    require(row["sha256"] == sha, "exact configuration SHA256 differs")
    cfg = parse(raw)
    require(set(cfg) == {"kind", "version", "sources", "source_archive", "host_baseline", "backend", "output", "limits", "claims"}
        and cfg["kind"] == "puck-python-louvain-build-v1" and type(cfg["version"]) is int and cfg["version"] == 1,
        "configuration kind/version/fields differ")
    require(cfg["limits"] == LIMITS and cfg["backend"] == BACKEND and cfg["output"] == OUTPUT_PATH,
            "fixed backend/limits/output differ")
    claims(cfg["claims"], "configuration")
    require(cfg["claims"] == FALSE, "configuration authority flag set differs")
    require([r["path"] for r in cfg["sources"]] == SOURCE_CAPSULE, "exact source capsule paths differ")
    require(cfg["source_archive"] == dict(path=SOURCE_PATH, size_bytes=204641, sha256=SOURCE_SHA), "source archive pin differs")
    require(cfg["host_baseline"]["path"] == BASELINE_PATH, "host baseline path differs")
    paths = []
    for item in [*cfg["sources"], cfg["source_archive"], cfg["host_baseline"]]:
        descriptor(item)
        paths.append(item["path"])
        read_file(root / item["path"], 64*MIB, item, retain=False)
    require(len(paths) == len(set(paths)), "source capsule aliases/duplicates")
    AUDIT["configuration_sha256"] = sha
    AUDIT["source_pins"] = cfg["sources"]
    return cfg, raw


def census(output):
    require(stat.S_ISDIR(output.lstat().st_mode), "output root not ordinary directory")
    ancestors(output)
    files, directories, total, inodes = [], [], 0, set()
    for directory, dirs, names in os.walk(output, followlinks=False):
        tick()
        for name in dirs:
            path = Path(directory) / name
            require(stat.S_ISDIR(path.lstat().st_mode), "output symlink/special directory")
            directories.append(path.relative_to(output).as_posix())
        for name in names:
            path = Path(directory) / name
            _, row = read_file(path, LIMITS["output_bytes"], retain=False)
            state = path.lstat()
            inode = state.st_dev, state.st_ino
            require(inode not in inodes, "retained output inode alias")
            inodes.add(inode)
            files.append(dict(path=path.relative_to(output).as_posix(), **row))
            total += row["size_bytes"]
        require(len(files) <= 8192 and len(directories) <= 4096 and total <= LIMITS["output_bytes"],
                "retained output allocation exceeded")
    return dict(files=sorted(files, key=lambda x:x["path"]), directories=sorted(directories),
                file_count=len(files), directory_count=len(directories), size_bytes=total)


def source_inventory(raw):
    decoded = bytearray()
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        while True:
            tick()
            block = stream.read(min(128*1024, 16*MIB + 1 - len(decoded)))
            if not block:
                break
            decoded.extend(block)
            require(len(decoded) <= 16*MIB, "source gzip decode cap")
    offset, count, pending, physical = 0, 0, False, []
    def string(field):
        first, separator, rest = field.partition(b"\0")
        require(not separator or not any(rest), "aliased tar header string")
        return first.decode("utf-8")
    while offset < len(decoded):
        tick()
        header = bytes(decoded[offset:offset+512])
        require(len(header) == 512, "truncated physical tar header")
        if not any(header):
            require(not pending and len(decoded)-offset >= 1024 and not any(decoded[offset:]), "invalid tar end/padding")
            break
        count += 1
        require(count <= 512, "physical tar header cap")
        item = tarfile.TarInfo.frombuf(header, "utf-8", "strict")
        name, prefix = string(header[:100]), string(header[345:500])
        name = prefix + "/" + name if prefix else name
        link = string(header[157:257])
        require(0 <= item.size <= 2*MIB, "tar member byte cap")
        start, end = offset+512, offset+512+item.size
        following = start + ((item.size+511)//512)*512
        require(following <= len(decoded) and not any(decoded[end:following]), "tar truncation/nonzero member padding")
        data = bytes(decoded[start:end])
        offset = following
        if item.type == tarfile.XHDTYPE:
            require(not pending and name == "././@PaxHeader" and not link, "unreviewed PAX header")
            length, separator, record = data.partition(b" ")
            require(separator and re.fullmatch(rb"[1-9][0-9]*", length) and int(length) == len(data)
                and re.fullmatch(rb"mtime=-?[0-9]+(?:\.[0-9]+)?\n", record), "unreviewed PAX payload")
            pending = True
            continue
        require(item.type in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE) and not link,
                "source alias/link/special extension")
        pending = False
        directory = item.type == tarfile.DIRTYPE
        name = rel(name, directory)
        require(not directory or item.size == 0, "source directory payload")
        require(name == "python-louvain-0.16" or name.startswith("python-louvain-0.16/"), "wrong source root")
        if name == "python-louvain-0.16":
            require(directory, "source root is file")
            relative = ""
        else:
            relative = name[len("python-louvain-0.16/"):]
        physical.append((relative, directory, data))
    else:
        raise ValueError("missing physical tar end markers")
    require(len({p for p, _, _ in physical}) == len(physical), "duplicate/aliased source member")
    paths = {p:d for p,d,_ in physical}
    for path in paths:
        require(not any(paths.get("/".join(path.split("/")[:i])) is False
            for i in range(1,len(path.split("/")))), "source prefix collision")
    # A separate high-level tarfile traversal must see exactly the physical entries.
    logical = []
    with tarfile.open(fileobj=io.BytesIO(decoded), mode="r:") as archive:
        for item in archive:
            tick()
            require(item.isdir() or item.isreg(), "tarfile sees special source member")
            require(set(item.pax_headers) <= {"mtime"}, "tarfile sees non-mtime PAX override")
            path = rel(item.name, item.isdir())
            path = "" if path == "python-louvain-0.16" else path[len("python-louvain-0.16/"):]
            stream = None if item.isdir() else archive.extractfile(item)
            data = b"" if stream is None else stream.read(2*MIB+1)
            require(len(data) == item.size, "tarfile payload count differs")
            logical.append((path,item.isdir(),data))
    require(logical == physical, "physical tar and independent tarfile views differ")
    payloads = {p:data for p,d,data in physical if not d}
    files = sorted([dict(path=p,size_bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        for p,data in payloads.items()],key=lambda x:x["path"])
    manifest = dict(kind="source", files=files, directories=sorted(p for p,d,_ in physical if d and p),
        total_bytes=sum(r["size_bytes"] for r in files),archive_sha256=SOURCE_SHA)
    return manifest, payloads, dict(physical_headers=count, logical_members=len(logical), decoded_bytes=len(decoded))


def tags(value):
    parts=value.split("-")
    require(len(parts)==3 and all(re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*",p) for p in parts), "invalid wheel tag")
    return {"-".join(v) for v in itertools.product(*(p.split(".") for p in parts))}


def one(message, key):
    values=message.get_all(key,[])
    require(len(values)==1,"metadata requires exactly one " + key)
    return str(values[0])


def verify_wheel(raw, filename, name, version, metadata_sha=None, backend=False):
    tokens=filename[:-4].split("-")
    require(filename.endswith(".whl") and len(tokens)==5 and re.sub(r"[-_.]+","-",tokens[0]).lower()==name
        and tokens[1]==version, "wheel filename identity differs")
    dist=tokens[0]+"-"+tokens[1]+".dist-info"
    special_paths={dist+"/"+v for v in ("METADATA","WHEEL","RECORD")}
    cap_members, cap_total, cap_member, cap_meta = (4096,64*MIB,16*MIB,4*MIB) if backend else (256,2*MIB,512*1024,512*1024)
    collected, payloads, digests, seen, total = [], {}, {}, {}, 0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos=archive.infolist()
        require(len(infos)<=cap_members,"wheel member cap")
        require(sum(i.file_size for i in infos)<=cap_total,"declared wheel decode cap")
        for item in infos:
            tick()
            path=item.orig_filename
            directory=item.is_dir()
            bare=rel(path,directory)
            require(path==item.filename and bare not in seen,"wheel alias/duplicate")
            seen[bare]=directory
            mode=stat.S_IFMT(item.external_attr>>16)
            require(mode in ((0,stat.S_IFDIR) if directory else (0,stat.S_IFREG))
                and not (directory and item.file_size),"wheel special member")
            require(item.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED)
                and not item.flag_bits & 0x41,"wheel encryption/compression")
            require(item.file_size<=cap_member,"wheel member cap")
            require(not bare.split("/")[0].endswith(".dist-info") or bare.split("/")[0]==dist,"different dist-info identity")
            require(path not in {dist+"/RECORD.jws",dist+"/RECORD.p7s"},"signed wheel unsupported")
            require(not backend or not bare.split("/")[0].endswith(".data"),"backend data relocation tree")
            hashes={alg:hashlib.new(alg) for alg in ("sha256","sha384","sha512")}
            count,crc,chunks=0,0,[]
            with archive.open(item) as member:
                while True:
                    tick()
                    block=member.read(min(128*1024,cap_member+1-count))
                    if not block:
                        break
                    count+=len(block)
                    total+=len(block)
                    require(count<=cap_member and total<=cap_total,"actual wheel decode cap")
                    require(path not in special_paths or count<=cap_meta,"wheel metadata cap")
                    crc=zlib.crc32(block,crc)
                    chunks.append(block)
                    for h in hashes.values():
                        h.update(block)
            require(count==item.file_size and crc==item.CRC,"actual wheel size/CRC mismatch: "+path)
            collected.append(dict(path=path,size_bytes=count,sha256=hashes["sha256"].hexdigest(),mode=item.external_attr>>16))
            if not directory:
                payloads[path]=b"".join(chunks)
                digests[path]={alg:h.digest() for alg,h in hashes.items()}
    for path in seen:
        require(not any(seen.get("/".join(path.split("/")[:i])) is False for i in range(1,len(path.split("/")))),"wheel prefix collision")
    require(special_paths<=set(payloads),"mandatory METADATA/WHEEL/RECORD absent")
    mp,wp,rp=(dist+"/"+v for v in ("METADATA","WHEEL","RECORD"))
    actual_metadata_sha=hashlib.sha256(payloads[mp]).hexdigest()
    require(metadata_sha is None or metadata_sha==actual_metadata_sha,"advertised METADATA hash differs")
    payloads[mp].decode("utf-8")
    md=BytesParser(policy=policy.default).parsebytes(payloads[mp])
    require(not md.defects and re.sub(r"[-_.]+","-",one(md,"Name")).lower()==name
        and one(md,"Version")==version,"METADATA identity/defects")
    wh=BytesParser(policy=policy.default).parsebytes(payloads[wp])
    require(not wh.defects and not wh.get_payload().strip() and one(wh,"Wheel-Version")=="1.0","WHEEL version/body")
    purity=one(wh,"Root-Is-Purelib")
    wheeltags=set().union(*(tags(str(v)) for v in wh.get_all("Tag",[])))
    require(purity == "true" and wheeltags==tags("-".join(tokens[-3:])),"WHEEL purity/tags")
    rows={}
    for row in csv.reader(io.StringIO(payloads[rp].decode("utf-8"),newline=""),strict=True):
        require(len(row)==3 and row[0] not in rows,"invalid/duplicate RECORD row")
        rows[row[0]]=row[1:]
    require(set(rows)==set(payloads),"RECORD does not cover every regular payload exactly")
    for path,(encoded,size) in rows.items():
        if path==rp:
            require(encoded==size=="","RECORD self hash/size")
            continue
        alg,value=encoded.split("=",1)
        require(alg in ("sha256","sha384","sha512") and re.fullmatch(r"[A-Za-z0-9_-]+",value),"RECORD algorithm/encoding")
        decoded=base64.urlsafe_b64decode(value+"="*(-len(value)%4))
        require(decoded==digests[path][alg] and base64.urlsafe_b64encode(decoded).rstrip(b"=").decode()==value,"RECORD digest differs: "+path)
        require(re.fullmatch(r"0|[1-9][0-9]*",size) and int(size)==len(payloads[path]),"RECORD size differs: "+path)
    collected.sort(key=lambda x:x["path"])
    result=dict(name=name,version=version,filename=filename,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
        metadata_sha256=actual_metadata_sha,member_count=len(collected),uncompressed_bytes=total,members=collected,
        licence_candidates=[r for r in collected if r["path"] in payloads and (r["path"].startswith(dist+"/licenses/")
            or r["path"].rsplit("/",1)[-1].lower().startswith(("license","licence","copying","notice")))],
        metadata=dict(name=one(md,"Name"),version=version,license_expression=md.get("License-Expression"),license=md.get("License"),
            license_files=md.get_all("License-File",[]),requires_dist=md.get_all("Requires-Dist",[])),
        wheel=dict(version="1.0",root_is_purelib=purity=="true",tags=sorted(wheeltags)),
        archive_payload_verified=True,record_verified=True)
    return result,payloads


def tree(root, manifest):
    expected={r["path"]:r for r in manifest["files"]}
    require(len(expected)==len(manifest["files"]),"duplicate staged manifest path")
    expected_dirs=set(manifest["directories"])
    for path in expected:
        rel(path)
        expected_dirs.update(str(p) for p in Path(path).parents if str(p)!=".")
    actual,dirs={},set()
    require(stat.S_ISDIR(root.lstat().st_mode),"staged root not directory")
    for directory,names,files in os.walk(root,followlinks=False):
        tick()
        for name in names:
            path=Path(directory)/name
            require(stat.S_ISDIR(path.lstat().st_mode),"staged directory alias/special")
            dirs.add(path.relative_to(root).as_posix())
        for name in files:
            path=Path(directory)/name
            _,row=read_file(path,64*MIB,retain=False)
            relative=path.relative_to(root).as_posix()
            actual[relative]=dict(path=relative,**row)
        require(len(actual)<=4096 and len(dirs)<=4096,"staged namespace cap")
    require(actual==expected and dirs==expected_dirs,"staged exact files/directories/bytes differ")
    return dict(files=len(actual),directories=len(dirs),bytes=sum(r["size_bytes"] for r in actual.values()))


def fixture_manifest():
    rows=[dict(path=p,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()) for p,raw in sorted(FIXTURE_FILES.items())]
    return dict(kind="authored-fixture",files=rows,directories=["bin","fixture_package"],total_bytes=sum(r["size_bytes"] for r in rows))


def baseline_verify(root,cfg):
    baseline=parse(read_file(root/BASELINE_PATH,MIB,cfg["host_baseline"])[0])
    require(baseline["python_prefix"]==PYTHON_PREFIX and baseline["recommended_python_system_files"]==SYSTEM_FILES
        and baseline["host_path_aliases"]==ALIASES and baseline["bwrap_executable"]["path"]=="/usr/bin/bwrap","baseline mount identities differ")
    require(len(baseline["files"])==4233 and len(baseline["symlinks"])==1048
        and sum(r[1] for r in baseline["files"])==90314007 and len(baseline["external_libraries"])==9,"baseline fixed census differs")
    host_started=time.monotonic()
    host_deadline=host_started+2
    prefix=Path(PYTHON_PREFIX)
    actual_files,actual_links=[],[]
    for directory,dirs,names in os.walk(prefix,followlinks=False):
        tick(host_deadline)
        for name in sorted([*dirs,*names]):
            path=Path(directory)/name
            relative=path.relative_to(prefix).as_posix()
            state=path.lstat()
            if stat.S_ISLNK(state.st_mode):
                target=os.readlink(path)
                require(path.resolve(strict=True).is_relative_to(prefix),"prefix link leaves declared prefix")
                LINKS[str(path)] = (identity(state), target)
                actual_links.append([relative,target])
                if name in dirs:
                    dirs.remove(name)
            elif stat.S_ISREG(state.st_mode):
                _,row=read_file(path,64*MIB,single=False,retain=False,deadline=host_deadline)
                actual_files.append([relative,row["size_bytes"],row["sha256"]])
            else:
                require(stat.S_ISDIR(state.st_mode),"special host prefix entry")
    inventory=dict(files=sorted(actual_files),symlinks=sorted(actual_links))
    digest=hashlib.sha256(json.dumps(inventory,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    require(inventory["files"]==baseline["files"] and inventory["symlinks"]==baseline["symlinks"]
        and digest==baseline["prefix_manifest_sha256"],"fresh full prefix bytes/links differ")
    for path,target in ALIASES:
        require(stat.S_ISLNK(Path(path).lstat().st_mode) and os.readlink(path)==target,"host loader alias differs")
        LINKS[path] = (identity(Path(path).lstat()), target)
    for row in [*baseline["external_libraries"],baseline["bwrap_executable"]]:
        for path,target in row.get("symlink_components",[]):
            require(stat.S_ISLNK(Path(path).lstat().st_mode) and os.readlink(path)==target,"external library link differs")
            LINKS[path] = (identity(Path(path).lstat()), target)
        path=Path(row.get("realpath",row.get("path")))
        for load in row.get("load_paths",[]):
            require(Path(load).resolve(strict=True)==path,"external library load resolution differs")
        read_file(path,64*MIB,dict(size_bytes=row["size"],sha256=row["sha256"]),single=False,retain=False,deadline=host_deadline)
    observed=dict(prefix_manifest_sha256=digest,regular_file_count=len(actual_files),symlink_count=len(actual_links),
        regular_file_bytes=sum(r[1] for r in actual_files),external_file_count=10)
    for name in ("baseline-before.json","baseline-after.json"):
        require(control(root/OUTPUT_PATH/name)==observed,"retained baseline receipt differs: "+name)
    AUDIT["trusted_host_rehash_seconds"]=time.monotonic()-host_started
    AUDIT["trusted_host_baseline"]=observed
    return baseline


def sandbox(root,source,mode):
    command=["/usr/bin/bwrap","--unshare-all","--unshare-user","--die-with-parent","--disable-userns","--cap-drop","ALL","--clearenv",
        "--hostname","palimpsest-wheel-build","--ro-bind",PYTHON_PREFIX,PYTHON_PREFIX,"--dir","/usr/lib"]
    for path in SYSTEM_FILES:
        command.extend(["--ro-bind",path,path])
    for path,target in ALIASES:
        command.extend(["--symlink",target,path])
    command.extend(["--ro-bind",str(source),"/source","--ro-bind",str(root/OUTPUT_PATH/"inputs/backend"),"/backend",
        "--ro-bind",str(root/"scripts/puck_python_louvain_worker.py"),"/driver.py",
        "--size",str(LIMITS["scratch_bytes"]),"--tmpfs","/work"])
    for name in ("home","tmp","build","egg","wheel-output"):
        command.extend(["--dir","/work/"+name])
    command.extend(["--symlink","work/tmp","/tmp","--proc","/proc","--remount-ro","/proc",
        "--dev","/dev","--remount-ro","/dev","--remount-ro","/"])
    for key,value in dict(HOME="/work/home",TMPDIR="/work/tmp",PATH="/nonexistent",LC_ALL="C.UTF-8",LANG="C.UTF-8",TZ="UTC",SOURCE_DATE_EPOCH="1720000000").items():
        command.extend(["--setenv",key,value])
    return command+["--chdir","/source",INTERPRETER,"-I","-S","-B","/driver.py",*mode]


def source_guard_review(root):
    raw=read_file(root/"scripts/puck_python_louvain_worker.py",MIB)[0]
    module=ast.parse(raw)
    assignments={node.targets[0].id:node.value for node in module.body if isinstance(node,ast.Assign)
        and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)}
    require(list(ast.literal_eval(assignments["DENIED_SYSCALLS"]))==DENIED
        and ast.literal_eval(assignments["FORBIDDEN"])==FORBIDDEN,"worker syscall/import guards differ")
    functions={n.name:n for n in module.body if isinstance(n,ast.FunctionDef)}
    main=functions["main"]
    require(isinstance(main.body[0],ast.Expr) and isinstance(main.body[0].value,ast.Call)
        and isinstance(main.body[0].value.func,ast.Name) and main.body[0].value.func.id=="initialise","worker guard not first main action")
    filter_function=functions["disable_process_changes"]
    expected_rows=[(0x20,0,0,4),(0x15,1,0,0xc000003e),(0x06,0,0,0x80000000),
        (0x20,0,0,0),(0x35,0,1,0x40000000),(0x06,0,0,0x80000000)]
    filter_rows=[n for n in filter_function.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="rows" for t in n.targets)]
    require(len(filter_rows)==1 and ast.literal_eval(filter_rows[0].value)==expected_rows,"worker ABI/x32 filter guard differs")
    # Amendment 02: exact automatic PWD/cwd and kernel read-only mount checks.
    readonly = functions["readonly"]
    expected_mount_test = ast.parse("not os.statvfs(directory).f_flag & os.ST_RDONLY", mode="eval").body
    require(isinstance(readonly.body[0], ast.If)
        and ast.dump(readonly.body[0].test) == ast.dump(expected_mount_test),
        "worker readonly route does not first require kernel ST_RDONLY")
    expected_proc_test = ast.parse('directory == "/proc"', mode="eval").body
    require(isinstance(readonly.body[1], ast.If)
        and ast.dump(readonly.body[1].test) == ast.dump(expected_proc_test)
        and len(readonly.body[1].body) == 1 and isinstance(readonly.body[1].body[0], ast.Return),
        "worker proc mount exception differs from amendment 02")
    probe_function = functions["probe"]
    env_nodes = [n for n in probe_function.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "expected_env" for t in n.targets)]
    require(len(env_nodes) == 1 and ast.literal_eval(env_nodes[0].value)
        == {"HOME", "TMPDIR", "PATH", "LC_ALL", "LANG", "TZ", "SOURCE_DATE_EPOCH", "PWD"},
        "worker exact environment set differs from amendment 02")
    expected_env_test = ast.parse('set(os.environ) != expected_env or os.environ.get("PWD") != "/source" or os.getcwd() != "/source"', mode="eval").body
    require(any(isinstance(n, ast.If) and ast.dump(n.test) == ast.dump(expected_env_test)
        for n in probe_function.body), "worker automatic PWD/cwd is not checked exactly")
    expected_mount_loop = ast.parse('for path in ("/", "/source", "/backend", sys.prefix, "/dev", "/proc"):\n    readonly(path)').body[0]
    require(any(isinstance(n, ast.For) and ast.dump(n) == ast.dump(expected_mount_loop)
        for n in probe_function.body), "worker probe does not check every read-only mount")
    text=raw.decode()
    for fragment in ["disable_process_changes()", "sys.meta_path.insert(0, BlockTarget())", "ctypes.get_errno() != errno.EPERM",
        "for number in DENIED_SYSCALLS:", "sock.connect((\"192.0.2.1\", 9))", "errno.ENETUNREACH, errno.EHOSTUNREACH",
        "build_meta.build_wheel(\"/work/wheel-output\", config_settings=settings)", "\"--build-base\", \"/work/build\"",
        "\"--egg-base\", \"/work/egg\"", "\"--bdist-dir\", \"/work/bdist\""]:
        require(fragment in text,"pinned worker implementation fragment missing: "+fragment)
    return dict(worker_source_sha256=hashlib.sha256(raw).hexdigest(),denied_syscalls=DENIED,
        source_evidence_only=True,retained_probe_required=True)


def stages(root):
    output=root/OUTPUT_PATH
    probe=control(output/"namespace-preflight.json")
    expected_keys={"kind","status","private_net_namespace","private_pid_namespace","scratch_capacity_bytes","inputs_readonly",
        "host_project_hidden","empty_home","external_route_absent","denied_syscalls","isolated","no_site"}
    require(set(probe)==expected_keys and probe["kind"]=="wheel-build-namespace-probe-v1" and probe["status"]=="passed","probe fields/status")
    for key in ("inputs_readonly","host_project_hidden","empty_home","external_route_absent","isolated","no_site"):
        require(probe[key] is True,"retained actual probe did not pass "+key)
    require(probe["denied_syscalls"]==DENIED and probe["scratch_capacity_bytes"]==256*MIB,"probe syscall/scratch evidence differs")
    require(re.fullmatch(r"net:\[[0-9]+\]",probe["private_net_namespace"])
        and re.fullmatch(r"pid:\[[0-9]+\]",probe["private_pid_namespace"]),"probe namespace receipt invalid")
    observations=[]
    for name,source,mode in [("outer",output/"inputs/fixture",None),
        ("fixture",output/"inputs/fixture",["build",FIXTURE_NAME]),("build",output/"inputs/source",["build",TARGET_NAME])]:
        stage=output/name
        invocation=control(stage/"invocation.json")
        require(set(invocation)=={"argv"},"stage invocation fields differ")
        argv=invocation["argv"]
        if mode is None:
            require(len(argv)>=3 and argv[-3]=="probe" and argv[-1]==str(root)
                and re.fullmatch(r"net:\[[0-9]+\]",argv[-2]),"probe actual command route differs")
            require(argv[-2]!=probe["private_net_namespace"],"probe retained host network namespace")
            mode=["probe",argv[-2],str(root)]
            require(control(stage/"stdout.log")==probe,"probe stdout differs from publication")
        require(argv==sandbox(root,source,mode),"actual "+name+" command differs from exact read-only namespace route")
        observed=control(stage/"supervision.json")
        require(set(observed)=={"status","returncode","failure","matching_survivors","sampled_peak_rss_bytes",
            "rss_sampling_seconds","pid","finished_monotonic"},"supervision fields differ")
        require(observed["status"]=="completed" and observed["returncode"]==0 and observed["failure"] is None
            and observed["matching_survivors"]==[],"stage did not return normally: "+name)
        require(type(observed["pid"]) is int and observed["pid"]>0
            and type(observed["sampled_peak_rss_bytes"]) is int and 0<=observed["sampled_peak_rss_bytes"]<=LIMITS["rss_bytes"]
            and observed["rss_sampling_seconds"]==0.05 and finite_number(observed["finished_monotonic"]),"stage clock/RSS/PGID evidence invalid")
        for stream in ("stdout.log","stderr.log"):
            require((stage/stream).lstat().st_size<=MIB,"retained stream cap exceeded")
        observations.append(dict(stage=name,**observed))
    require(len({r["pid"] for r in observations})==3,"reused worker group receipt")
    require([r["finished_monotonic"] for r in observations]==sorted(r["finished_monotonic"] for r in observations),"stage return clocks out of order")
    require(observations[-1]["finished_monotonic"]-observations[0]["finished_monotonic"]<120,"stage interval exceeds normal allocation")
    AUDIT["retained_probe"]=probe
    AUDIT["supervision"]=observations
    AUDIT["process_scan"]=process_scan(AUDIT["configuration_sha256"],root,{r["pid"] for r in observations})
    return observations


def wheel_stage(output,stage,filename,name,version):
    directory=output/stage
    transport=control(directory/"stdout.log")
    require(set(transport)=={"kind","filename","size_bytes","sha256","wheel_base64","source_build_executed","forbidden_modules_absent","backend_version"}
        and transport["kind"]=="wheel-build-worker-v1" and transport["filename"]==filename
        and transport["source_build_executed"] is True and transport["forbidden_modules_absent"] is True
        and transport["backend_version"]=="84.0.0","wheel stdout transport fields/flags differ")
    require(type(transport["size_bytes"]) is int and 0<transport["size_bytes"]<=256*1024
        and type(transport["wheel_base64"]) is str and len(transport["wheel_base64"])<=4*((256*1024+2)//3),"wheel transport bound")
    raw=base64.b64decode(transport["wheel_base64"],validate=True)
    require(len(raw)==transport["size_bytes"] and hashlib.sha256(raw).hexdigest()==transport["sha256"],"wheel transport digest/size")
    published=read_file(directory/filename,256*1024,transport)[0]
    require(raw==published,"published wheel differs from retained stdout base64")
    result,payloads=verify_wheel(published,filename,name,version)
    require(control(directory/"wheel-verification.json")==result,"retained wheel verifier result differs from independent full audit")
    return result,payloads


def script_matches(source,built):
    if built==source:
        return True
    if not source.startswith(b"#!") or not built.startswith(b"#!python\n"):
        return False
    return source.partition(b"\n")[2]==built.partition(b"\n")[2]


def verify_inputs_and_wheels(root,cfg):
    output=root/OUTPUT_PATH
    original=read_file(root/SOURCE_PATH,2*MIB,cfg["source_archive"])[0]
    copied=read_file(output/"inputs/archives/python-louvain-0.16.tar.gz",2*MIB,cfg["source_archive"])[0]
    require(original==copied,"source original/copy byte custody differs")
    source,source_files,tar_counts=source_inventory(original)
    require(control(output/"source-manifest.json")==source,"source manifest differs from independently parsed archive")
    source_counts=tree(output/"inputs/source",source)
    backend_raw=read_file(output/"inputs/archives"/BACKEND["filename"],2*MIB,BACKEND)[0]
    backend_wheel,backend_files=verify_wheel(backend_raw,BACKEND["filename"],"setuptools","84.0.0",BACKEND["metadata_sha256"],True)
    require(control(output/"backend-archive-verification.json")==backend_wheel,"backend archive verification differs")
    backend_manifest=dict(kind="backend",files=sorted([dict(path=p,size_bytes=len(v),sha256=hashlib.sha256(v).hexdigest())
        for p,v in backend_files.items()],key=lambda r:r["path"]),
        directories=sorted(r["path"][:-1] for r in backend_wheel["members"] if r["path"].endswith("/")),
        total_bytes=sum(len(v) for v in backend_files.values()),archive_sha256=BACKEND["sha256"],wheel_verification=backend_wheel)
    require(control(output/"backend-manifest.json")==backend_manifest,"backend manifest differs from independent wheel")
    backend_counts=tree(output/"inputs/backend",backend_manifest)
    fixture=fixture_manifest()
    require(control(output/"fixture-manifest.json")==fixture,"authored fixture source manifest differs")
    fixture_counts=tree(output/"inputs/fixture",fixture)
    fixture_wheel,fixture_payloads=wheel_stage(output,"fixture",FIXTURE_NAME,"palimpsest-build-fixture","0.0")
    require(fixture_wheel["metadata"]["requires_dist"]==["not-installed-for-fixture>=1"],"fixture missing-dependency declaration differs")
    require(fixture_payloads["fixture_package/__init__.py"]==FIXTURE_FILES["fixture_package/__init__.py"],"fixture package trap changed")
    fixture_scripts={p:v for p,v in fixture_payloads.items() if p.startswith("palimpsest_build_fixture-0.0.data/scripts/")}
    require(set(fixture_scripts)=={"palimpsest_build_fixture-0.0.data/scripts/fixture"}
        and script_matches(FIXTURE_FILES["bin/fixture"],next(iter(fixture_scripts.values()))),"fixture script trap/body differs")
    target,target_payloads=wheel_stage(output,"build",TARGET_NAME,"python-louvain","0.16")
    require(sorted(target["metadata"]["requires_dist"])==["networkx","numpy"],"target requirement declarations differ")
    expected_py={p:v for p,v in source_files.items() if p.startswith("community/") and p.endswith(".py")}
    actual_py={p:v for p,v in target_payloads.items() if p.startswith("community/") and p.endswith(".py")}
    require(expected_py and expected_py==actual_py,"target community Python files differ from unchanged source")
    scripts={p:v for p,v in source_files.items() if p.startswith("bin/")}
    actual_scripts={p:v for p,v in target_payloads.items() if p.startswith("python_louvain-0.16.data/scripts/")}
    require(scripts and {p.rsplit("/",1)[1] for p in scripts}=={p.rsplit("/",1)[1] for p in actual_scripts},"target script set differs")
    for path,raw in scripts.items():
        require(script_matches(raw,actual_scripts["python_louvain-0.16.data/scripts/"+path.rsplit("/",1)[1]]),"target script body differs: "+path)
    require("LICENSE" in source_files,"source LICENSE missing")
    licences=[p for p,v in target_payloads.items() if p.startswith("python_louvain-0.16.dist-info/")
        and p.rsplit("/",1)[-1]=="LICENSE" and v==source_files["LICENSE"]]
    require(licences,"source LICENSE bytes not retained in target wheel")
    AUDIT["source_tar"]=tar_counts
    AUDIT["staged_trees"]=dict(source=source_counts,backend=backend_counts,fixture=fixture_counts)
    AUDIT["wheels"]=[{k:r[k] for k in ("name","version","filename","size_bytes","sha256","metadata_sha256","member_count","uncompressed_bytes")}
        for r in (backend_wheel,fixture_wheel,target)]
    AUDIT["target_source_equivalence"]=dict(community_python_files=sorted(expected_py),scripts=sorted(scripts),licence_members=licences)
    return target,fixture_wheel


def outcome_verify(root,cfg,config_raw,observations,wheels,args):
    output=root/OUTPUT_PATH
    require(read_file(output/"configuration.json",4*MIB)[0]==config_raw,"retained exact configuration bytes differ")
    outcome=control(output/"outcome.json")
    claims(outcome,"terminal outcome")
    AUDIT["terminal_outcome"]={k:outcome.get(k) for k in ("kind","version","status","configuration_sha256","elapsed_seconds",
        "backend_request_state","authored_fixture_build","target_source_build","error_type","error")}
    require(outcome["kind"]=="puck-python-louvain-build-result-v1" and outcome["version"]==1
        and outcome["configuration_sha256"]==args.sha256,"terminal identity/config hash differs")
    if outcome["status"]!="wheel_verified":
        AUDIT["terminal_classification"]="failed_stage_preserved"
        raise ValueError("retained build stage failed; wheel acceptance refused: "+str(outcome.get("error",outcome["status"])))
    require(outcome["backend_request_state"]==outcome["authored_fixture_build"]==outcome["target_source_build"]=="completed",
            "successful outcome lacks all three completed stages")
    require(finite_number(outcome["started_unix"]) and finite_number(outcome["elapsed_seconds"],high=120),"parent normal-return clock invalid")
    request=outcome["request"]
    require(set(request)=={"url","status","body_bytes","elapsed_seconds"} and request["url"]==BACKEND["url"]
        and request["status"]==200 and request["body_bytes"]==818216 and finite_number(request["elapsed_seconds"],high=120)
        and request["elapsed_seconds"]<=outcome["elapsed_seconds"],"single exact backend request receipt differs")
    require(observations is not None and wheels is not None,"successful outcome lacks independently verified actual stages/wheels")
    target,fixture=wheels
    require(outcome["wheel"]=={k:target[k] for k in ("filename","size_bytes","sha256","metadata_sha256","member_count","uncompressed_bytes")}
        and outcome["fixture_wheel_sha256"]==fixture["sha256"],"outcome wheel descriptors differ")
    inventory=AUDIT["retained_namespace"]
    outcome_size=(output/"outcome.json").lstat().st_size
    expected_pre=dict(files=inventory["file_count"]-1,directories=inventory["directory_count"],size_bytes=inventory["size_bytes"]-outcome_size)
    require(outcome["retained_namespace_before_outcome"]==expected_pre,"pre-outcome retained namespace receipt differs")
    require(args.parent_exitcode==0 and args.exit_evidence,"externally observed parent exitcode/evidence missing or nonzero")
    AUDIT["external_terminal_observation"]=dict(parent_exitcode=args.parent_exitcode,evidence=args.exit_evidence,
        evidence_source="orchestrator supplied terminal observation")
    AUDIT["terminal_classification"]="normal_wheel_build_completed"
    return outcome


def namespace_exact(root):
    output=root/OUTPUT_PATH
    inventory=AUDIT["retained_namespace"]
    expected={"configuration.json","outcome.json","baseline-before.json","baseline-after.json","backend-archive-verification.json",
        "source-manifest.json","backend-manifest.json","fixture-manifest.json","namespace-preflight.json",
        "inputs/archives/python-louvain-0.16.tar.gz","inputs/archives/"+BACKEND["filename"]}
    for name,filename in (("outer",None),("fixture",FIXTURE_NAME),("build",TARGET_NAME)):
        expected.update(name+"/"+v for v in ("invocation.json","supervision.json","stdout.log","stderr.log"))
        if filename:
            expected.update({name+"/"+filename,name+"/wheel-verification.json"})
    for name in ("source","backend","fixture"):
        manifest=control(output/(name+"-manifest.json"))
        expected.update("inputs/"+name+"/"+r["path"] for r in manifest["files"])
    require({r["path"] for r in inventory["files"]}==expected,"retained namespace has unexpected or missing files")
    expected_dirs={str(p) for path in expected for p in Path(path).parents if str(p)!="."}
    for name in ("source","backend","fixture"):
        manifest=control(output/(name+"-manifest.json"))
        expected_dirs.update("inputs/"+name+"/"+d for d in manifest["directories"])
    require(set(inventory["directories"])==expected_dirs,"retained namespace has unexpected or missing directories")
    return dict(exact_files=True,exact_directories=True)


def recheck(root,args,observations):
    groups=set() if observations is None else {r["pid"] for r in observations}
    AUDIT["final_process_scan"]=process_scan(args.sha256,root,groups)
    for path,wanted in IDENTITIES.items():
        tick()
        require(identity(Path(path).lstat())==wanted,"pinned/evidence file changed through audit: "+path)
    for path,(wanted,target) in LINKS.items():
        tick()
        require(identity(Path(path).lstat())==wanted and os.readlink(path)==target,
                "host symlink changed through audit: "+path)
    final=census(root/OUTPUT_PATH)
    require(final==AUDIT["retained_namespace"],"retained namespace changed through independent audit")
    return True


def publish(path):
    require(path.is_absolute() and all(p not in (".","..") for p in path.parts),"report path must be absolute/canonical")
    ancestors(path)
    require(not path.exists() and not path.is_symlink(),"report already exists")
    AUDIT["elapsed_seconds"]=time.monotonic()-START
    raw=canonical(AUDIT)
    require(len(raw)<=2*MIB,"audit report cap exceeded")
    parent_fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    before=os.fstat(parent_fd)
    try:
        fd=os.open(path.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent_fd)
        try:
            view=memoryview(raw)
            while view:
                count=os.write(fd,view)
                require(count>0,"audit report write made no progress")
                view=view[count:]
            os.fsync(fd)
            require(os.fstat(fd).st_nlink==1,"audit report aliases")
            expected=identity(os.fstat(fd))
            require(expected==identity(os.stat(path.name,dir_fd=parent_fd,follow_symlinks=False)),"report edge changed")
            os.fsync(parent_fd)
            now=path.parent.lstat()
            require((before.st_dev,before.st_ino,before.st_mode)==(now.st_dev,now.st_ino,now.st_mode),"report parent edge changed")
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)
    print(json.dumps(dict(status=AUDIT["status"],wheel_accepted=AUDIT["wheel_accepted"],report=str(path),
        report_bytes=len(raw),report_sha256=hashlib.sha256(raw).hexdigest(),findings=AUDIT["findings"]),sort_keys=True,separators=(",",":")))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",required=True)
    parser.add_argument("--sha256",required=True)
    parser.add_argument("--report",required=True)
    parser.add_argument("--parent-exitcode",type=int)
    parser.add_argument("--exit-evidence")
    args=parser.parse_args()
    require(re.fullmatch(r"[0-9a-f]{64}",args.sha256),"exact config SHA256 required")
    root=Path(args.root)
    report=Path(args.report)
    require(root.is_absolute() and root==root.resolve(strict=True),"root must be actual canonical absolute worktree")
    require(report.is_absolute() and report!=root/OUTPUT_PATH and root/OUTPUT_PATH not in report.parents,
            "audit report must be outside the retained build namespace")
    ancestors(report)
    require(not report.exists() and not report.is_symlink(),"audit report must be new/exclusive")
    AUDIT["root"]=str(root)
    AUDIT["configuration_sha256"]=args.sha256
    AUDIT["audit_program_sha256"]=read_file(Path(__file__).absolute(),MIB)[1]["sha256"]
    # No audit report is published while this exact invocation still has a live route.
    process_scan(args.sha256,root)
    loaded=check("exact_configuration_and_source_capsule",lambda:load_config(root,args.sha256))
    inventory=check("finite_single_link_retained_namespace_all_files_sha256",lambda:census(root/OUTPUT_PATH))
    if inventory is not None:
        AUDIT["retained_namespace"]=inventory
    check("pinned_worker_filter_and_build_write_routing_source",lambda:source_guard_review(root))
    cfg,config_raw=loaded if loaded is not None else (None,None)
    if cfg is not None:
        check("fresh_full_host_prefix_links_libraries_and_bwrap",lambda:baseline_verify(root,cfg))
    observations=check("three_actual_commands_probe_denials_normal_stage_returns",lambda:stages(root))
    wheels=check("independent_tar_backend_fixture_target_payloads_and_staged_trees",
        lambda:verify_inputs_and_wheels(root,cfg)) if cfg is not None else None
    terminal=check("terminal_outcome_matches_retained_actual_stages",lambda:outcome_verify(root,cfg,config_raw,observations,wheels,args))
    if inventory is not None and terminal is not None:
        check("exact_success_retained_namespace",lambda:namespace_exact(root))
    if inventory is not None:
        check("final_process_absence_and_unchanged_evidence",lambda:recheck(root,args,observations))
    AUDIT["limitations"]=["Retained clocks, probe and supervision receipts rely on pinned authored parent/worker and trusted host execution.",
        "RSS maxima are sampled operational observations, not hard memory bounds or WCET proof.",
        "Before/after host hashes do not establish hostile-Linux isolation or numerical-runtime native identity.",
        "This audit executes no product entrypoint and grants no installation, numerical runtime, assets, study or collection authority."]
    if terminal is not None and not AUDIT["findings"]:
        AUDIT["status"]="PASS"
        AUDIT["wheel_accepted"]=True
    publish(report)
    return 0 if AUDIT["status"]=="PASS" else 1


if __name__=="__main__":
    def expired(signum,frame):
        raise TimeoutError("independent terminal audit exceeded 20 seconds")
    signal.signal(signal.SIGALRM,expired)
    signal.alarm(20)
    try:
        result=main()
    finally:
        signal.alarm(0)
    raise SystemExit(result)
