"""Build bounded candidate slots; never launch, allocate or qualify a study."""
import copy

from palimpsest import memory, memory_decision_world as world
from palimpsest.memory_experiment import CONDITIONS, KINDS
from scripts.memory_confirmatory_v3 import require, validate_plan


def build_slots(split, blocks, prerequisites):
    """Explicit full blocks only; prerequisite descriptors are caller declarations."""
    memory._enum(split, ('development', 'held-out'))
    memory._list(blocks, 1)
    require(bool(blocks), 'One complete family block required')
    for block in blocks:
        require(type(block) is int and 0 <= block < world.FAMILY_DESIGN['block_limit'], 'Invalid family block')
    require(blocks == sorted(set(blocks)), 'Blocks must be distinct and canonical')
    memory._list(prerequisites, 256)
    require(bool(prerequisites), 'Prerequisites must be declared')
    plan = {'schema': 'memory-confirmatory-readout-v3', 'split': split,
        'conditions': list(CONDITIONS), 'families': [],
        'prerequisites': copy.deepcopy(prerequisites)}
    cases, slots = [], []
    for block in blocks:
        for row in range(world.FAMILY_DESIGN['rows_per_block']):
            twins = [world.make_family_case(split, block, row, kind) for kind in KINDS]
            plan['families'].append({'id': twins[0]['family_id'],
                'cases': {case['kind']: case['case_id'] for case in twins}})
            for case in twins:
                cases.append(case)
                binding = {key: case[key] for key in ('family_id', 'case_id',
                    'case_sha256', 'profile_sha256', 'seed', 'split', 'block', 'row', 'kind')}
                slots.extend({**binding, 'condition': condition} for condition in CONDITIONS)
    validate_plan(plan)
    return {'schema': 'memory-family-slots-v3', 'claim': 'software-candidate-only',
        'native_allocation': False, 'plan': plan, 'cases': cases, 'slots': slots,
        'assignment_table': [world.family_assignment(row)
                             for row in range(world.FAMILY_DESIGN['rows_per_block'])],
        'aliases': ['strength-2 public projection; interaction effects are not separately identified']}
