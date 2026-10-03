import math
import pytest
from app.analysis.tasks.hand_movement_left import HandMovementLeftTask
from app.analysis.tasks.hand_movement_right import HandMovementRightTask

@pytest.mark.parametrize('task_type', [HandMovementLeftTask, HandMovementRightTask])
def test_palm_default_and_explicit_index_override(task_type):
    frame = [[float(i), float(i % 3), 0.] for i in range(21)]
    palm = sum(math.dist(frame[0], frame[i]) for i in [5, 9, 13, 17]) / 4
    index = sum(math.dist(frame[i], frame[j]) for i,j in [(5,6),(6,7),(7,8)])
    task = task_type()
    assert task.task_norm_strategy == 'PALMSIZE'
    assert task.calculate_normalization_factor([frame]) == pytest.approx(palm)
    task.task_norm_strategy = None
    assert task.calculate_normalization_factor([frame]) == pytest.approx(palm)
    task.task_norm_strategy = 'INDEXSIZE'
    assert task.calculate_normalization_factor([frame]) == pytest.approx(index)
