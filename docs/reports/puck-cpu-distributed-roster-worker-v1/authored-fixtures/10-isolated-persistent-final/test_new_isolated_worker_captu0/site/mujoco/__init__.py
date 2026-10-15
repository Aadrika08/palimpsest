__version__='3.3.6'
import sys
for name in ('torch._C._distributed_autograd', 'torch._C._distributed_c10d', 'torch._C._distributed_rpc'):
 sys.modules[name].late=abs
