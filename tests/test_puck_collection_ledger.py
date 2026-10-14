"""Synthetic clocks exercise frozen allocation, never collection execution."""
import importlib
import pytest


class Clock:
    def __init__(self): self.value = 0.0
    def __call__(self): return self.value
    def advance(self, seconds): self.value += seconds


def ledger():
    module = importlib.import_module('palimpsest.puck_collection_ledger')
    clock = Clock()
    return module.CollectionClockLedger(clock=clock), clock


def children(book, clock, seconds=0):
    for ordinal in range(12):
        with book.child(ordinal): clock.advance(seconds)


def returns(book, clock, full=False):
    for name, cap in [('final_recheck',15),('publication',20),('release',10),('return_guard',5)]:
        with book.phase(name): clock.advance(cap if full else 0)


def test_exact_frozen_allocation_and_defensive_source_receipt():
    book, clock = ledger()
    with book.phase('pre_owner_admission'): clock.advance(20)
    with book.phase('launch_reap'): clock.advance(20)
    children(book, clock, 180)
    with book.phase('reduction'): clock.advance(10)
    returns(book, clock, True)
    receipt = book.complete()
    assert receipt['status'] == 'completed'
    assert receipt['elapsed_seconds'] == 2260
    assert receipt['child_seconds'] == 2160
    assert len(receipt['owners']) == 12
    assert receipt['owners'][0]['owner_id'] == 'collection-6110-seed-21'
    assert receipt['owners'][-1]['owner_id'] == 'collection-6113-seed-23'
    assert receipt['qualification_claims'] == []
    assert receipt['executable'] is receipt['collection_admission'] is receipt['native_execution'] is False
    receipt['owners'].clear()
    assert len(book.receipt()['owners']) == 12


@pytest.mark.parametrize('name,cap',[('pre_owner_admission',20),('launch_reap',20),('reduction',10),('final_recheck',15),('publication',20),('release',10),('return_guard',5)])
def test_bucket_cannot_borrow_other_bucket_budget(name,cap):
    book, clock = ledger()
    if name=='reduction':children(book,clock)
    if name in ('final_recheck','publication','release','return_guard'):
        children(book,clock)
        order=['final_recheck','publication','release','return_guard']
        for previous in order[:order.index(name)]:
            with book.phase(previous): pass
    with pytest.raises(TimeoutError):
        with book.phase(name): clock.advance(cap + .001)
    assert book.receipt()['status'] == 'failed'
    assert book.receipt()['buckets'][name]['used_seconds'] == cap + .001
    with pytest.raises(RuntimeError):
        with book.child(0): pass


def test_repeated_parent_phases_share_their_own_fixed_bucket():
    book, clock = ledger()
    with book.phase('launch_reap'): clock.advance(12)
    with book.phase('launch_reap'): clock.advance(8)
    with pytest.raises(TimeoutError):
        with book.phase('launch_reap'): clock.advance(.001)


@pytest.mark.parametrize('ordinal',[1,-1,12,True,0.0,'0'])
def test_child_order_and_exact_ordinal(ordinal):
    book,_ = ledger()
    with pytest.raises(ValueError):
        with book.child(ordinal): pass
    assert book.receipt()['status'] == 'failed'


def test_each_child_has_own_bound_and_failed_owner_does_not_complete():
    book,clock = ledger()
    with book.child(0): clock.advance(1)
    with pytest.raises(TimeoutError):
        with book.child(1): clock.advance(180.001)
    assert len(book.receipt()['owners']) == 1


def test_owner_cannot_repeat():
    book,_ = ledger()
    with book.child(0): pass
    with pytest.raises(ValueError):
        with book.child(0): pass


@pytest.mark.parametrize('nested',['phase','child'])
def test_nested_intervals_poison_even_when_inner_error_caught(nested):
    book,_ = ledger()
    with pytest.raises(RuntimeError):
        with book.phase('launch_reap'):
            try:
                with (book.child(0) if nested=='child' else book.phase('pre_owner_admission')): pass
            except RuntimeError: pass
    assert book.receipt()['status']=='failed'


def test_body_exception_charges_elapsed_and_poison_preserves_original_error():
    book,clock = ledger()
    with pytest.raises(LookupError,match='authored'):
        with book.phase('launch_reap'):
            clock.advance(9)
            raise LookupError('authored')
    assert book.receipt()['buckets']['launch_reap']['used_seconds']==9
    assert book.receipt()['status']=='failed'


@pytest.mark.parametrize('bad',[float('nan'),float('inf'),-1,True,'1'])
def test_clock_invalid_at_exit_poison(bad):
    book,clock=ledger()
    with pytest.raises(ValueError):
        with book.child(0): clock.value=bad
    assert book.receipt()['status']=='failed'


def test_monotonic_regression_between_phases():
    book,clock=ledger()
    with book.phase('launch_reap'): clock.advance(1)
    clock.value=.5
    with pytest.raises(ValueError):
        with book.phase('pre_owner_admission'): pass


@pytest.mark.parametrize('bad',[float('nan'),float('inf'),-1,True,'1'])
def test_invalid_initial_clock_does_not_create_a_ledger(bad):
    module=importlib.import_module('palimpsest.puck_collection_ledger')
    with pytest.raises(ValueError):module.CollectionClockLedger(clock=lambda:bad)


def test_clock_exception_on_exit_poison():
    module=importlib.import_module('palimpsest.puck_collection_ledger')
    class FailingClock(Clock):
        def __call__(self):
            if self.value==2:raise OSError('authored clock unavailable')
            return self.value
    clock=FailingClock();book=module.CollectionClockLedger(clock=clock)
    with pytest.raises(OSError):
        with book.phase('launch_reap'):clock.value=2
    assert book.receipt()['status']=='failed'
    with pytest.raises(RuntimeError):book.complete()


@pytest.mark.parametrize('seconds',[2210.001,2260.001,2270.001])
def test_unaccounted_time_cannot_escape_stage_deadline(seconds):
    book,clock=ledger()
    clock.advance(seconds)
    with pytest.raises(TimeoutError):
        with book.child(0): pass


def test_exact_internal_boundary_is_permitted_but_return_overrun_is_not():
    book,clock=ledger()
    with book.phase('pre_owner_admission'):clock.advance(20)
    with book.phase('launch_reap'):clock.advance(20)
    children(book,clock,180)
    with book.phase('reduction'):clock.advance(10)
    with book.phase('final_recheck'): pass
    with book.phase('publication'): pass
    with book.phase('release'): pass
    with book.phase('return_guard'): pass
    clock.advance(5.001)
    with pytest.raises(TimeoutError): book.complete()


@pytest.mark.parametrize('kind',['missing_child','missing_return','out_of_order_return','premature_return','active_complete','unknown_phase'])
def test_incomplete_or_invalid_route_never_completes(kind):
    book,_=ledger()
    with pytest.raises((ValueError,RuntimeError)):
        if kind=='missing_child': book.complete()
        elif kind=='missing_return':
            children(book,Clock());book.complete()
        elif kind=='out_of_order_return':
            children(book,Clock())
            with book.phase('publication'): pass
        elif kind=='premature_return':
            with book.phase('final_recheck'): pass
        elif kind=='active_complete':
            with book.phase('launch_reap'): book.complete()
        else:
            with book.phase('unknown'): pass
    assert book.receipt()['status']=='failed'


def test_final_phase_teardown_time_is_charged():
    book,clock=ledger();children(book,clock)
    for name in ('final_recheck','publication','release'):
        with book.phase(name): pass
    with pytest.raises(TimeoutError):
        with book.phase('return_guard'):
            try: clock.advance(4)
            finally: clock.advance(1.001)


def test_completed_ledger_cannot_reenter_or_repeat_completion():
    book,clock=ledger();children(book,clock);returns(book,clock);book.complete()
    with pytest.raises(RuntimeError):book.complete()
    with pytest.raises(RuntimeError):
        with book.child(0):pass


def test_unused_child_time_cannot_pay_for_inter_owner_parent_gap():
    book,clock=ledger()
    with book.child(0):clock.advance(1)
    clock.advance(20.001)
    with pytest.raises(TimeoutError,match='launch_reap'):
        with book.child(1):clock.advance(1)
    assert book.receipt()['status']=='failed'


@pytest.mark.parametrize('position,bucket,limit',[
    ('initial','pre_owner_admission',20),('after_children','reduction',10),
    ('after_recheck','publication',20),('after_publication','release',10),
    ('after_release','return_guard',5),('after_guard','return_guard',5)])
def test_control_gap_uses_explicit_fixed_bucket(position,bucket,limit):
    book,clock=ledger()
    if position!='initial':children(book,clock,1)
    phases={'after_recheck':1,'after_publication':2,'after_release':3,'after_guard':4}
    order=['final_recheck','publication','release','return_guard']
    for name in order[:phases.get(position,0)]:
        with book.phase(name):pass
    clock.advance(limit+.001)
    with pytest.raises(TimeoutError,match=bucket):
        if position=='initial':
            with book.child(0):pass
        elif position=='after_guard':book.complete()
        else:
            with book.phase(order[phases.get(position,0)]):pass
    assert book.receipt()['buckets'][bucket]['used_seconds']==pytest.approx(limit+.001)


def test_small_realistic_control_gaps_are_accounted_and_can_complete():
    book,clock=ledger();clock.advance(.01)
    for ordinal in range(12):
        with book.child(ordinal):clock.advance(1)
        clock.advance(.01)
    returns(book,clock)
    clock.advance(.01)
    result=book.complete()
    assert result['buckets']['pre_owner_admission']['used_seconds']==pytest.approx(.01)
    assert result['buckets']['launch_reap']['used_seconds']==pytest.approx(.11)
    assert result['buckets']['reduction']['used_seconds']==pytest.approx(.01)
    assert result['buckets']['return_guard']['used_seconds']==pytest.approx(.01)
    assert result['elapsed_seconds']==pytest.approx(result['child_seconds']+sum(x['used_seconds'] for x in result['buckets'].values()))


@pytest.mark.parametrize('kind',['pre_after_owner','reduction_before_owners'])
def test_parent_phase_placement_is_fixed(kind):
    book,clock=ledger()
    if kind=='pre_after_owner':
        with book.child(0):clock.advance(1)
    with pytest.raises(ValueError):
        with book.phase('pre_owner_admission' if kind=='pre_after_owner' else 'reduction'):pass
    assert book.receipt()['status']=='failed'


def test_completion_receipt_construction_is_inside_return_guard(monkeypatch):
    book,clock=ledger();children(book,clock);returns(book,clock)
    original=book.receipt
    def slow_receipt():
        result=original();clock.advance(5.001);return result
    monkeypatch.setattr(book,'receipt',slow_receipt)
    with pytest.raises(TimeoutError,match='return_guard'):book.complete()
    assert original()['status']=='failed'
