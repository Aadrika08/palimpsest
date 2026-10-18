import sys, types, torch
def authored_delegate():
    return 47
torch._C._distributed_autograd = types.ModuleType('torch._C._distributed_autograd')
torch._C._distributed_autograd.__file__ = __file__
sys.modules['torch._C._distributed_autograd'] = torch._C._distributed_autograd
import _authored_publication_gate_distributed_autograd
for name in ['DistAutogradContext', '_current_context', '_get_debug_info', '_get_max_id', '_init', '_is_valid_context', '_new_context', '_release_context', '_retrieve_context', 'backward', 'get_gradients']:
    setattr(torch._C._distributed_autograd, name, authored_delegate)
