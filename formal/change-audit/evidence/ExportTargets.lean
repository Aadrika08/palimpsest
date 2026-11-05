import Cache.Hashing
open Cache IO Hashing System in
def main (args : List String) : IO Unit := CacheM.run do
  let roots ← parseArgs ("lookup" :: args)
  if roots.size != args.length then throw <| IO.userError "Every explicit module root must be distinct and retained"
  if roots.isEmpty then throw <| IO.userError "Explicit target modules required"
  let memo ← getHashMemo roots
  let hashes ← memo.filterByRootModules roots.keys
  for (mod, hash) in hashes.toArray do
    let paths ← mkBuildPaths mod
    if !(← allExist paths) then
      let base := if isFromMathlib mod then "mathlib" else "project"
      let target := (paths[1]!).1
      let trace := (paths[0]!).1
      IO.println s!"{mod}\t{hash.asLTar}\t{base}\t{target}\t{trace}"
