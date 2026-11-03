"""Force requests must bypass saved results for every registered task."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.test import RequestFactory
from app.views import create_task_views, analysis_jobs

TASKS = sorted(p.stem for p in (Path(create_task_views.__file__).parent.parent / 'analysis' / 'tasks').glob('*.py')
               if not p.name.startswith('_') and p.stem != 'base_task')


@pytest.mark.parametrize('task_name', TASKS)
def test_force_bypasses_cached_result_for_every_task(task_name, monkeypatch):
    cached = {'source': 'old-cache'}
    loader = Mock(return_value=cached)
    inference = Mock(return_value={'source': 'new-inference'})
    saver = Mock()
    class_name = ''.join(word.capitalize() for word in task_name.split('_')) + 'Task'
    module = SimpleNamespace(**{class_name: lambda: SimpleNamespace(api_response=inference)})
    monkeypatch.setattr(create_task_views, 'cache_key', lambda *args: 'same-key')
    monkeypatch.setattr(create_task_views, 'load_cached', loader)
    monkeypatch.setattr(create_task_views, 'save_cached', saver)
    monkeypatch.setattr(create_task_views.importlib, 'import_module', lambda *args: module)
    monkeypatch.setattr(create_task_views, 'attach_landmark_schema', lambda *args: None)
    monkeypatch.setattr(create_task_views, 'assess_analysis_quality', lambda *args: {})
    factory = RequestFactory()
    normal = create_task_views.execute_task(task_name, factory.post('/api/task/?id=1', {'json_data': '{}'}))
    assert normal['analysisRuntime']['cache_hit'] is True
    inference.assert_not_called()
    loader.reset_mock()
    fresh = create_task_views.execute_task(task_name, factory.post('/api/task/?id=1&force=1', {'json_data': '{}'}))
    assert fresh['source'] == 'new-inference'
    assert fresh['analysisRuntime']['cache_hit'] is False
    loader.assert_not_called()
    inference.assert_called_once()
    saver.assert_called_once_with('1', 'same-key', fresh)


@pytest.mark.parametrize('task_name', TASKS)
def test_background_job_forwards_force_for_every_task(task_name, monkeypatch):
    execute = Mock(return_value={'fresh': True})
    monkeypatch.setattr(analysis_jobs, 'execute_task', execute)
    monkeypatch.setattr(analysis_jobs, '_JOBS', {'reset-job': {'status': 'queued'}})
    analysis_jobs._run('reset-job', task_name, '1', '{}', True)
    assert execute.call_args.args[1].GET['force'] == '1'
    assert analysis_jobs._JOBS['reset-job']['status'] == 'completed'
