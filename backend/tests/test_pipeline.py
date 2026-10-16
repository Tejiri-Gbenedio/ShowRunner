from itertools import product
from uuid import uuid4

import pytest

from app.pipeline import (
    InMemoryPipelineRepository, PipelineRun, PipelineState, TRANSITIONS, transition,
)

def test_every_transition_not_in_table_is_rejected() -> None:
    for current, target in product(PipelineState, repeat=2):
        if target not in TRANSITIONS[current]:
            with pytest.raises(ValueError, match="illegal pipeline transition"):
                transition(current, target)

def test_every_declared_transition_is_accepted() -> None:
    for current, targets in TRANSITIONS.items():
        for target in targets:
            assert transition(current, target) is target

def test_repository_isolates_owners_for_list_get_and_update() -> None:
    repository = InMemoryPipelineRepository()
    owner_a, owner_b = uuid4(), uuid4()
    run_a = repository.create(PipelineRun(uuid4(), owner_a))
    run_b = repository.create(PipelineRun(uuid4(), owner_b))

    assert repository.list_for_owner(owner_a) == [run_a]
    assert repository.list_for_owner(owner_b) == [run_b]
    assert repository.get_for_owner(owner_b, run_a.id) is None
    assert repository.update_for_owner(owner_b, run_a.id, PipelineState.QUEUED) is None
    assert repository.get_for_owner(owner_a, run_a.id) == run_a

def test_owner_can_update_through_a_legal_transition() -> None:
    owner = uuid4()
    repository = InMemoryPipelineRepository()
    run = repository.create(PipelineRun(uuid4(), owner))

    updated = repository.update_for_owner(owner, run.id, PipelineState.QUEUED)

    assert updated is not None
    assert updated.state is PipelineState.QUEUED
    assert updated.updated_at >= run.updated_at
