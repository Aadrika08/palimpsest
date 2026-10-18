import sys, types, torch
def authored_delegate():
    return 47
torch._C._distributed_rpc = types.ModuleType('torch._C._distributed_rpc')
torch._C._distributed_rpc.__file__ = __file__
sys.modules['torch._C._distributed_rpc'] = torch._C._distributed_rpc
import _authored_publication_gate_distributed_rpc
for name in ['PyRRef', 'RemoteProfilerManager', 'RpcAgent', 'RpcBackendOptions', 'TensorPipeAgent', 'WorkerInfo', '_TensorPipeRpcBackendOptionsBase', '_cleanup_python_rpc_handler', '_delete_all_user_and_unforked_owner_rrefs', '_destroy_rref_context', '_disable_jit_rref_pickle', '_disable_server_process_global_profiler', '_enable_jit_rref_pickle', '_enable_server_process_global_profiler', '_get_current_rpc_agent', '_invoke_remote_builtin', '_invoke_remote_python_udf', '_invoke_remote_torchscript', '_invoke_rpc_builtin', '_invoke_rpc_python_udf', '_invoke_rpc_torchscript', '_is_current_rpc_agent_set', '_reset_current_rpc_agent', '_rref_context_get_debug_info', '_set_and_start_rpc_agent', '_set_profiler_node_id', '_set_rpc_timeout', 'enable_gil_profiling', 'get_rpc_timeout']:
    setattr(torch._C._distributed_rpc, name, authored_delegate)
