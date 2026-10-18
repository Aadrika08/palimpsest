__version__='2.9.0+cpu'
import sys,types
_C=types.ModuleType("torch._C")
sys.modules["torch._C"]=_C
for name in ('torch._C._distributed_autograd', 'torch._C._distributed_c10d', 'torch._C._distributed_rpc'):
 child=types.ModuleType(name)
 def forbidden(): raise RuntimeError("member invoked")
 child.call=forbidden
 setattr(_C,name.rsplit(".",1)[1],child)
 sys.modules[name]=child
