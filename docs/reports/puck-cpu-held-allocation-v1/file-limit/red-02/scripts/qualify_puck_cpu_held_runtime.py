import resource
from pathlib import Path
resource.setrlimit(resource.RLIMIT_FSIZE,(1073741824,1073741824))
with Path("authored-payload.bin").open("wb") as stream:
 for i in range(17):stream.write(b"x"*(1024**2))
print("authored copy complete",flush=True)
