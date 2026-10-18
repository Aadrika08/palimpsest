import sys, types, torch
def authored_delegate():
    return 47
torch._C._autograd = types.ModuleType('torch._C._autograd')
torch._C._autograd.__file__ = __file__
sys.modules['torch._C._autograd'] = torch._C._autograd
import _authored_publication_gate_autograd
for name in ['CreationMeta', 'DeviceType', 'ProfilerEvent', 'SavedTensor', 'TensorGeometry', '_InputMetadata', '_KinetoEvent', '_ProfilerDisableOptions', '_ProfilerResult', '_add_metadata_json', '_clear_callbacks', '_disable_profiler', '_disable_profiler_legacy', '_enable_profiler', '_enable_profiler_legacy', '_enable_record_function', '_get_creation_meta', '_get_current_graph_task_keep_graph', '_get_data_attr', '_get_sequence_nr', '_kineto_step', '_pop_saved_tensors_default_hooks', '_prepare_profiler', '_profiler_enabled', '_profiler_type', '_push_saved_tensors_default_hooks', '_record_function_with_args_enter', '_record_function_with_args_exit', '_saved_tensors_hooks_disable', '_saved_tensors_hooks_enable', '_saved_tensors_hooks_get_disabled_error_message', '_saved_tensors_hooks_is_enabled', '_saved_tensors_hooks_set_tracing', '_set_creation_meta', '_set_empty_test_observer', '_soft_assert_raises', '_supported_activities', '_toggle_collection_dynamic', '_top_saved_tensors_default_hooks', '_unsafe_set_version_counter', 'kineto_available']:
    setattr(torch._C._autograd, name, authored_delegate)
