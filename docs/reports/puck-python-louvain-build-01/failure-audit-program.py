#!/usr/bin/env python3
"""Audit only the preserved stage-01 failure; success never accepts a wheel.

Uses the retained independent audit's pinned stdlib-only inert readers. No
project, backend or target module is imported; no subprocess or network exists.
Only --report is written, exclusively, after read-only evidence verification.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import runpy
import signal
import stat
import time

ORIGINAL_PROGRAM = Path("/tmp/palimpsest-louvain-build-audit-v1.py")
ORIGINAL_PROGRAM_SHA = "adf57f209cfa59bee40c3bb5a95c606386b31abc32f932d336a423869b7b12f1"
ORIGINAL_REPORT = Path("/tmp/palimpsest-louvain-build-01-audit.json")
ORIGINAL_REPORT_SHA = "adbb1bdfab1d5e3aa3dc4dd4c34d144d25bc129f00fabb939b8b7acbe971435c"
CONFIG_SHA = "e57b32033656c1bdc300ce3b6441f5f103f6569dc979b6e38e464273965ed418"
EXPECTED_ERROR = b"bwrap: --disable-userns requires --unshare-user\n"
START = time.monotonic()


def require(value, message):
    if not value:
        raise ValueError(message)


def load_library():
    s = ORIGINAL_PROGRAM.lstat()
    require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1 and s.st_size == 51980,
            "original audit is not its unchanged single-link regular file")
    raw = ORIGINAL_PROGRAM.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == ORIGINAL_PROGRAM_SHA, "original audit program changed")
    before = (s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_nlink,s.st_mtime_ns,s.st_ctime_ns)
    library = runpy.run_path(str(ORIGINAL_PROGRAM), run_name="independent_terminal_audit_library")
    s = ORIGINAL_PROGRAM.lstat()
    require(before == (s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_nlink,s.st_mtime_ns,s.st_ctime_ns),
            "original audit changed while loading inert readers")
    return library


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    a = load_library()
    read = a["read_file"]
    control = a["control"]
    root = Path(args.root)
    output = root / a["OUTPUT_PATH"]
    require(root.is_absolute() and root == root.resolve(strict=True), "noncanonical worktree root")
    report = Path(args.report)
    require(report.is_absolute() and not report.exists() and not report.is_symlink()
            and output not in report.parents, "report must be exclusive and outside retained evidence")
    a["ancestors"](report)
    result = dict(kind="puck-python-louvain-preserved-failure-audit-v1",version=1,
        status="FAILURE_AUDIT_INCOMPLETE",wheel_accepted=False,
        original_audit_program_sha256=ORIGINAL_PROGRAM_SHA,original_audit_report_sha256=ORIGINAL_REPORT_SHA,
        configuration_sha256=CONFIG_SHA,root=str(root),**a["FALSE"])
    a["AUDIT"].clear()
    a["AUDIT"].update(result)
    try:
        original_report = a["parse"](read(ORIGINAL_REPORT,2*a["MIB"],dict(size_bytes=73917,sha256=ORIGINAL_REPORT_SHA))[0])
        require(original_report["status"] == "FAIL" and original_report["wheel_accepted"] is False
                and original_report["terminal_classification"] == "failed_stage_preserved", "original audit failure verdict differs")
        a["process_scan"](CONFIG_SHA,root,{2344325})
        cfg,config_raw = a["load_config"](root,CONFIG_SHA)
        require(read(output/"configuration.json",4*a["MIB"])[0] == config_raw,"retained configuration bytes differ")
        census = a["census"](output)
        require(census == original_report["retained_namespace"], "retained evidence changed since original audit")
        result["retained_namespace"] = census
        result["source_capsule"] = cfg["sources"]
        result["source_capsule_count"] = len(cfg["sources"])
        result["all_pinned_input_count"] = len(cfg["sources"]) + 3

        original = read(root/a["SOURCE_PATH"],2*a["MIB"],cfg["source_archive"])[0]
        copy = read(output/"inputs/archives/python-louvain-0.16.tar.gz",2*a["MIB"],cfg["source_archive"])[0]
        require(original == copy,"source original and retained copy differ")
        source,source_payloads,tar_counts = a["source_inventory"](original)
        require(control(output/"source-manifest.json") == source,"independent source manifest differs")
        source_counts = a["tree"](output/"inputs/source",source)
        backend = a["BACKEND"]
        backend_raw = read(output/"inputs/archives"/backend["filename"],2*a["MIB"],backend)[0]
        verified,backend_payloads = a["verify_wheel"](backend_raw,backend["filename"],"setuptools","84.0.0",backend["metadata_sha256"],True)
        require(control(output/"backend-archive-verification.json") == verified,"independent backend archive payload verification differs")
        backend_manifest = dict(kind="backend",files=sorted([
            dict(path=p,size_bytes=len(v),sha256=hashlib.sha256(v).hexdigest()) for p,v in backend_payloads.items()],key=lambda r:r["path"]),
            directories=sorted(r["path"][:-1] for r in verified["members"] if r["path"].endswith("/")),
            total_bytes=sum(len(v) for v in backend_payloads.values()),archive_sha256=backend["sha256"],wheel_verification=verified)
        require(control(output/"backend-manifest.json") == backend_manifest,"independent backend staging manifest differs")
        backend_counts = a["tree"](output/"inputs/backend",backend_manifest)
        fixture = a["fixture_manifest"]()
        require(control(output/"fixture-manifest.json") == fixture,"fixture authored bytes differ")
        fixture_counts = a["tree"](output/"inputs/fixture",fixture)
        result["staged_trees"] = dict(source=source_counts,backend=backend_counts,fixture=fixture_counts)
        result["source_tar"] = tar_counts
        result["backend_archive"] = {k:verified[k] for k in ("name","version","filename","size_bytes","sha256","metadata_sha256","member_count","uncompressed_bytes","archive_payload_verified","record_verified")}
        result["backend_archive"]["regular_payloads"] = len(backend_payloads)
        result["backend_archive"]["licence_candidates"] = len(verified["licence_candidates"])

        outcome = control(output/"outcome.json")
        a["claims"](outcome,"failed outcome")
        require(outcome["kind"] == "puck-python-louvain-build-result-v1" and outcome["version"] == 1
            and outcome["status"] == "failed" and outcome["configuration_sha256"] == CONFIG_SHA
            and outcome["backend_request_state"] == "completed" and outcome["authored_fixture_build"] == "not_started"
            and outcome["target_source_build"] == "not_started" and outcome["error_type"] == "RuntimeError"
            and outcome["error"] == "Build stage failed within its fixed allocation", "preserved terminal failure/state differs")
        require(a["finite_number"](outcome["elapsed_seconds"],high=120),"parent elapsed outside finite allocation")
        req = outcome["request"]
        require(set(req) == {"url","status","body_bytes","elapsed_seconds"} and req["url"] == backend["url"]
            and req["status"] == 200 and req["body_bytes"] == 818216
            and a["finite_number"](req["elapsed_seconds"],high=outcome["elapsed_seconds"]),"actual backend HTTP receipt differs")
        result["outcome"] = outcome
        result["external_terminal_observation"] = dict(parent_exitcode=1,evidence="root exec session 19137 final chunk 327a1a exit 1",
            evidence_source="orchestrator supplied terminal observation")
        observation = control(output/"outer/supervision.json")
        require(observation == dict(status="failed",returncode=1,failure=None,matching_survivors=[],
            sampled_peak_rss_bytes=38232064,rss_sampling_seconds=0.05,pid=2344325,finished_monotonic=435293.253196502),
            "actual launcher terminal supervision differs")
        require(observation["sampled_peak_rss_bytes"] <= cfg["limits"]["rss_bytes"],"sampled combined RSS over threshold")
        require(read(output/"outer/stdout.log",a["MIB"])[0] == b"","probe stdout was not empty")
        require(read(output/"outer/stderr.log",a["MIB"])[0] == EXPECTED_ERROR,"exact launcher failure message differs")
        invocation = control(output/"outer/invocation.json")
        argv = invocation["argv"]
        require(set(invocation) == {"argv"} and argv[-3] == "probe" and argv[-1] == str(root)
            and argv == a["sandbox"](root,output/"inputs/fixture",["probe",argv[-2],str(root)]),"attempted launcher command differs")
        result["launcher_supervision"] = observation
        result["attempted_command"] = argv
        result["worker_guard_source_review"] = a["source_guard_review"](root)

        expected = {"configuration.json","outcome.json","baseline-before.json","backend-archive-verification.json",
            "source-manifest.json","backend-manifest.json","fixture-manifest.json",
            "inputs/archives/python-louvain-0.16.tar.gz","inputs/archives/"+backend["filename"],
            "outer/invocation.json","outer/supervision.json","outer/stdout.log","outer/stderr.log"}
        manifests = dict(source=source,backend=backend_manifest,fixture=fixture)
        for name,manifest in manifests.items():
            expected.update("inputs/"+name+"/"+r["path"] for r in manifest["files"])
        require({r["path"] for r in census["files"]} == expected,"unexpected/missing failure files; possible extra execution evidence")
        expected_dirs = {"build","fixture"} | {str(p) for path in expected for p in Path(path).parents if str(p)!="."}
        for name,manifest in manifests.items():
            expected_dirs.update("inputs/"+name+"/"+d for d in manifest["directories"])
        require(set(census["directories"]) == expected_dirs,"unexpected/missing failure directory namespace")
        require(list((output/"build").iterdir()) == list((output/"fixture").iterdir()) == [],"fixture or target stage has retained launch evidence")
        require(not (output/"namespace-preflight.json").exists() and not (output/"baseline-after.json").exists(),
            "unexpected probe-pass or successful after-baseline receipt")

        # Fresh independent full trusted-host check, including links and all bytes.
        host_started = time.monotonic()
        deadline = host_started + 2
        baseline = a["parse"](read(root/a["BASELINE_PATH"],a["MIB"],cfg["host_baseline"])[0])
        require(baseline["python_prefix"] == a["PYTHON_PREFIX"] and baseline["host_path_aliases"] == a["ALIASES"]
            and baseline["recommended_python_system_files"] == a["SYSTEM_FILES"] and len(baseline["external_libraries"]) == 9,
            "baseline fixed identities differ")
        files,links = [],[]
        prefix = Path(a["PYTHON_PREFIX"])
        for directory,dirs,names in os.walk(prefix,followlinks=False):
            a["tick"](deadline)
            for name in sorted([*dirs,*names]):
                path = Path(directory)/name
                relative = path.relative_to(prefix).as_posix()
                state = path.lstat()
                if stat.S_ISLNK(state.st_mode):
                    target = os.readlink(path)
                    require(path.resolve(strict=True).is_relative_to(prefix),"trusted prefix symlink escaped")
                    links.append([relative,target])
                    a["LINKS"][str(path)] = (a["identity"](state),target)
                    if name in dirs:
                        dirs.remove(name)
                elif stat.S_ISREG(state.st_mode):
                    _,row = read(path,64*a["MIB"],single=False,retain=False,deadline=deadline)
                    files.append([relative,row["size_bytes"],row["sha256"]])
                else:
                    require(stat.S_ISDIR(state.st_mode),"special trusted prefix entry")
        inventory = dict(files=sorted(files),symlinks=sorted(links))
        digest = hashlib.sha256(json.dumps(inventory,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        require(inventory["files"] == baseline["files"] and inventory["symlinks"] == baseline["symlinks"]
            and digest == baseline["prefix_manifest_sha256"],"fresh trusted host prefix differs")
        for path,target in a["ALIASES"]:
            require(os.readlink(path) == target,"host loader alias changed")
            a["LINKS"][path] = (a["identity"](Path(path).lstat()),target)
        for row in [*baseline["external_libraries"],baseline["bwrap_executable"]]:
            for path,target in row.get("symlink_components",[]):
                require(os.readlink(path) == target,"external library link differs")
                a["LINKS"][path] = (a["identity"](Path(path).lstat()),target)
            path = Path(row.get("realpath",row.get("path")))
            for load in row.get("load_paths",[]):
                require(Path(load).resolve(strict=True) == path,"external library load identity differs")
            read(path,64*a["MIB"],dict(size_bytes=row["size"],sha256=row["sha256"]),single=False,retain=False,deadline=deadline)
        host = dict(prefix_manifest_sha256=digest,regular_file_count=len(files),symlink_count=len(links),
            regular_file_bytes=sum(r[1] for r in files),external_file_count=10)
        require(host == control(output/"baseline-before.json") and len(files) == 4233 and len(links) == 1048
            and host["regular_file_bytes"] == 90314007,"fresh host check differs from before receipt")
        result["fresh_host_rehash"] = dict(**host,elapsed_seconds=time.monotonic()-host_started)

        result["process_scan"] = a["process_scan"](CONFIG_SHA,root,{2344325})
        other_drivers = []
        for proc in Path("/proc").iterdir():
            if not proc.name.isdecimal() or int(proc.name) == os.getpid():
                continue
            try:
                fields = (proc/"stat").read_text().rsplit(")",1)[1].split()
                argv = (proc/"cmdline").read_bytes().split(b"\0")
                if fields[0] not in ("Z","X") and b"/driver.py" in argv and any(v in argv for v in (b"probe",a["FIXTURE_NAME"].encode(),a["TARGET_NAME"].encode())):
                    other_drivers.append(int(proc.name))
            except (FileNotFoundError,ProcessLookupError):
                continue
        require(not other_drivers,"a matching namespace Python driver survives")
        result["process_scan"]["matching_namespace_python_drivers"] = other_drivers
        for path,wanted in a["IDENTITIES"].items():
            require(a["identity"](Path(path).lstat()) == wanted,"pinned/evidence file changed through failure audit: "+path)
        for path,(wanted,target) in a["LINKS"].items():
            require(a["identity"](Path(path).lstat()) == wanted and os.readlink(path) == target,"trusted host link changed through failure audit")
        require(a["census"](output) == census,"retained failure namespace changed through failure audit")
        result["supported"] = ["Exact config and twelve source-capsule pins plus baseline/source archive unchanged.",
            "Original/copied source archive identical; physical tar and every staged source/backend/fixture file and directory verified.",
            "Exact backend archive hash, METADATA, WHEEL, RECORD, every regular payload and CRC verified without importing it.",
            "One recorded bubblewrap probe launcher attempted and returned 1 with the exact option error; stdout empty.",
            "Fixture and target outcomes not_started, their retained stage directories empty, and no probe-pass or wheel artifact exists.",
            "Fresh full trusted prefix, symlinks, nine external libraries and bubblewrap bytes match baseline.",
            "No live recorded PGID, exact parent/build routes or matching namespace Python drivers at final scan."]
        result["not_established"] = ["Namespace creation, probe Python execution or actual syscall/read-only/network denial checks.",
            "Backend fixture execution, target setup execution, target wheel production, installation or numerical-runtime qualification.",
            "A hard RSS/WCET bound or historical kernel-level proof of every process exec; launch ordering relies on pinned authored code and retained bubblewrap refusal."]
        result["status"] = "PRESERVED_FAILURE_VERIFIED"
    except Exception as error:
        result["findings"] = [dict(type=type(error).__name__,message=str(error))]
    result["elapsed_seconds"] = time.monotonic()-START
    result["audit_program_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    a["AUDIT"].clear()
    a["AUDIT"].update(result)
    a["publish"](report)
    return 0 if result["status"] == "PRESERVED_FAILURE_VERIFIED" else 1


if __name__ == "__main__":
    def expired(signum,frame):
        raise TimeoutError("failure audit exceeded 20 seconds")
    signal.signal(signal.SIGALRM,expired)
    signal.alarm(20)
    try:
        code=main()
    finally:
        signal.alarm(0)
    raise SystemExit(code)
