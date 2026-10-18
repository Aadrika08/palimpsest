"""Choose descriptor origins and observe persistent native target identities.

The held-directory policy supports ELF $ORIGIN dependencies while trusting the
native initializer. It does not prevent races: a directory-edge swap during
dlopen may execute changed native code before the later observation refuses it.
Target guards and map observations detect persistent mismatches only; transient
mappings, anonymous code and JIT code are outside this contract.
"""
from __future__ import annotations


def _require_policy(policy):
    if policy not in ('exact-file-fd-v1', 'held-directory-observed-v1'):
        raise ValueError('Unknown native origin policy')


def native_load_path(provider, row, policy) -> str:
    """Recheck the held target and select its explicitly registered origin."""
    _require_policy(policy)
    holder = provider._holders[row['root_index']]
    provider._target_recheck(holder, row['path'])
    fd, parent_fd, leaf_name, _ = holder._files[row['path']]
    if policy == 'exact-file-fd-v1':
        return '/proc/self/fd/' + str(fd)
    return '/proc/self/fd/' + str(parent_fd) + '/' + leaf_name


def require_native_target(provider, row, policy, observed_maps) -> None:
    """For directory origins require the target's raw (device, inode) map key."""
    _require_policy(policy)
    holder = provider._holders[row['root_index']]
    expected_identity = holder._files[row['path']][3]
    if (policy == 'held-directory-observed-v1'
            and (expected_identity[0], expected_identity[1]) not in observed_maps):
        raise RuntimeError('Native target image was not observed')
    provider._target_recheck(holder, row['path'])
