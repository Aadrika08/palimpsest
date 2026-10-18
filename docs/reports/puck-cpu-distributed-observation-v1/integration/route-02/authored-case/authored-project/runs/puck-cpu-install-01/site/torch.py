__version__ = '2.9.0+cpu'
import sys, types
def authored_delegate():
    return 47
_C = types.ModuleType('torch._C')
sys.modules['torch._C'] = _C
child = types.ModuleType('torch._C._distributed_autograd')
setattr(_C, '_distributed_autograd', child)
sys.modules['torch._C._distributed_autograd'] = child
for key in ['DistAutogradContext', '_current_context', '_get_debug_info', '_get_max_id', '_init', '_is_valid_context', '_new_context', '_release_context', '_retrieve_context', 'backward', 'get_gradients', 'AUTHORED_é']:
    setattr(child, key, authored_delegate)
child = types.ModuleType('torch._C._distributed_c10d')
setattr(_C, '_distributed_c10d', child)
sys.modules['torch._C._distributed_c10d'] = child
for key in ['AllToAllOptions', 'AllgatherOptions', 'AllreduceCoalescedOptions', 'AllreduceOptions', 'Backend', 'BarrierOptions', 'BroadcastOptions', 'BuiltinCommHookType', 'DDPLoggingData', 'DebugLevel', 'ErrorType', 'FakeProcessGroup', 'FakeWork', 'FileStore', 'GatherOptions', 'GradBucket', 'HashStore', 'Logger', 'OpType', 'PrefixStore', 'ProcessGroup', 'ProcessGroupGloo', 'ReduceOp', 'ReduceOptions', 'ReduceScatterOptions', 'Reducer', 'ScatterOptions', 'Store', 'TCPStore', 'Work', 'WorkInfo', 'WorkResult', '_ControlCollectives', '_DMAConnectivity', '_DistributedBackendOptions', '_ProcessGroupWrapper', '_Request', '_Response', '_StoreCollectives', '_SymmetricMemory', '_WorkerServer', '_allow_inflight_collective_as_graph_input', '_broadcast_coalesced', '_compute_bucket_assignment_by_size', '_create_work_from_future', '_current_process_group', '_detect_dma_connectivity', '_dump_fr_trace', '_dump_fr_trace_json', '_get_handler', '_get_handler_names', '_get_work_registry_size', '_make_nccl_premul_sum', '_register_builtin_comm_hook', '_register_comm_hook', '_register_process_group', '_register_work', '_resolve_process_group', '_set_allow_inflight_collective_as_graph_input', '_set_global_rank', '_set_process_group', '_set_thread_isolation_mode', '_test_python_store', '_unregister_all_process_groups', '_unregister_process_group', '_verify_params_across_processes', 'get_debug_level', 'set_debug_level', 'set_debug_level_from_env']:
    setattr(child, key, authored_delegate)
child = types.ModuleType('torch._C._distributed_rpc')
setattr(_C, '_distributed_rpc', child)
sys.modules['torch._C._distributed_rpc'] = child
for key in ['PyRRef', 'RemoteProfilerManager', 'RpcAgent', 'RpcBackendOptions', 'TensorPipeAgent', 'WorkerInfo', '_TensorPipeRpcBackendOptionsBase', '_cleanup_python_rpc_handler', '_delete_all_user_and_unforked_owner_rrefs', '_destroy_rref_context', '_disable_jit_rref_pickle', '_disable_server_process_global_profiler', '_enable_jit_rref_pickle', '_enable_server_process_global_profiler', '_get_current_rpc_agent', '_invoke_remote_builtin', '_invoke_remote_python_udf', '_invoke_remote_torchscript', '_invoke_rpc_builtin', '_invoke_rpc_python_udf', '_invoke_rpc_torchscript', '_is_current_rpc_agent_set', '_reset_current_rpc_agent', '_rref_context_get_debug_info', '_set_and_start_rpc_agent', '_set_profiler_node_id', '_set_rpc_timeout', 'enable_gil_profiling', 'get_rpc_timeout']:
    setattr(child, key, authored_delegate)
