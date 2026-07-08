import io
import os
import time
from collections import deque

import pytest

import app as app_module


@pytest.fixture
def client():
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as client:
        yield client


def _reset_queue_state():
    cleanup_targets = []
    with app_module.jobs_lock:
        for job_info in app_module.jobs.values():
            cleanup_targets.append((job_info.get('file_path'), job_info.get('session_id')))
        app_module.jobs.clear()
        app_module.job_queue = deque()
        app_module.queued_job_params.clear()
        app_module.queue_identity_index.clear()

    with app_module.session_manager['session_lock']:
        app_module.session_manager['active_sessions'].clear()

    for file_path, session_id in cleanup_targets:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass
        if session_id:
            try:
                app_module.cleanup_user_session(session_id)
            except Exception:
                pass


@pytest.fixture(autouse=True)
def clean_queue_state():
    _reset_queue_state()
    yield
    _reset_queue_state()


def _upload(client, *, email='queue@example.com', company_id='acme', password='secret', filename='sample.xlsx', content=b'xlsx'):
    return client.post(
        '/upload',
        data={
            'email': email,
            'password': password,
            'company_id': company_id,
            'file': (io.BytesIO(content), filename),
        },
        content_type='multipart/form-data',
    )


def test_same_user_duplicate_tabs_reuse_single_waiting_job(client, monkeypatch):
    monkeypatch.setattr(app_module, 'MAX_ACTIVE_SESSIONS', 0)
    monkeypatch.setattr(app_module, 'get_system_resources', lambda: {'memory_mb': 0, 'cpu_percent': 0, 'active_sessions': 0})

    first = _upload(client, email='dup@example.com', filename='first.xlsx')
    second = _upload(client, email='dup@example.com', filename='second.xlsx')

    first_payload = first.get_json()
    second_payload = second.get_json()

    assert first.status_code == 202
    assert second.status_code == 202
    assert first_payload['status'] == 'queued'
    assert second_payload['status'] == 'queued'
    assert second_payload['existing_job'] is True
    assert second_payload['job_id'] == first_payload['job_id']

    with app_module.jobs_lock:
        assert len(app_module.job_queue) == 1
        assert len(app_module.queued_job_params) == 1


def test_cancel_removes_waiting_job_and_allows_fresh_enqueue(client, monkeypatch):
    monkeypatch.setattr(app_module, 'MAX_ACTIVE_SESSIONS', 0)
    monkeypatch.setattr(app_module, 'get_system_resources', lambda: {'memory_mb': 0, 'cpu_percent': 0, 'active_sessions': 0})

    queued = _upload(client, email='cancel@example.com')
    queued_payload = queued.get_json()
    job_id = queued_payload['job_id']

    cancel = client.post(f'/cancel/{job_id}')
    cancel_again = client.post(f'/cancel/{job_id}')
    replacement = _upload(client, email='cancel@example.com', filename='replacement.xlsx')

    assert cancel.status_code == 200
    assert cancel.get_json()['status'] == 'cancelled'
    assert cancel_again.status_code == 200
    assert cancel_again.get_json()['status'] == 'cancelled'
    assert replacement.status_code == 202
    assert replacement.get_json()['job_id'] != job_id

    with app_module.jobs_lock:
        assert job_id not in app_module.job_queue
        assert app_module.jobs[job_id]['status'] == 'cancelled'


def test_queue_status_poll_acts_as_heartbeat_and_stale_waiting_expires(client, monkeypatch):
    monkeypatch.setattr(app_module, 'MAX_ACTIVE_SESSIONS', 0)
    monkeypatch.setattr(app_module, 'get_system_resources', lambda: {'memory_mb': 0, 'cpu_percent': 0, 'active_sessions': 0})

    first = _upload(client, email='first@example.com')
    second = _upload(client, email='second@example.com')
    first_job_id = first.get_json()['job_id']
    second_job_id = second.get_json()['job_id']

    stale_at = time.time() - (app_module.QUEUE_HEARTBEAT_TIMEOUT_SEC + 5)
    with app_module.jobs_lock:
        app_module.jobs[first_job_id]['last_heartbeat_at'] = stale_at
        app_module.jobs[first_job_id]['lease_expires_at'] = stale_at

    app_module.prune_jobs(current_time=time.time())
    second_status = client.get(f'/status/{second_job_id}').get_json()

    with app_module.jobs_lock:
        assert app_module.jobs[first_job_id]['status'] == 'expired'
        assert app_module.jobs[second_job_id]['status'] == 'queued'
        assert app_module.jobs[second_job_id]['lease_expires_at'] > time.time()

    assert second_status['queue_position'] == 1


def test_detach_signal_expires_waiting_job_after_grace_period(client, monkeypatch):
    monkeypatch.setattr(app_module, 'MAX_ACTIVE_SESSIONS', 0)
    monkeypatch.setattr(app_module, 'get_system_resources', lambda: {'memory_mb': 0, 'cpu_percent': 0, 'active_sessions': 0})

    queued = _upload(client, email='detach@example.com')
    job_id = queued.get_json()['job_id']

    detach = client.post(f'/api/queue/detach/{job_id}')
    assert detach.status_code == 200

    with app_module.jobs_lock:
        disconnect_at = time.time() - (app_module.QUEUE_DISCONNECT_GRACE_SEC + 5)
        app_module.jobs[job_id]['disconnect_hint_at'] = disconnect_at
        app_module.jobs[job_id]['last_heartbeat_at'] = disconnect_at

    app_module.prune_jobs(current_time=time.time())

    with app_module.jobs_lock:
        assert app_module.jobs[job_id]['status'] == 'expired'


def test_single_user_running_job_can_complete_without_queue_duplication(client, monkeypatch):
    monkeypatch.setattr(app_module, 'MAX_ACTIVE_SESSIONS', 1)
    monkeypatch.setattr(app_module, 'get_system_resources', lambda: {'memory_mb': 0, 'cpu_percent': 0, 'active_sessions': 0})

    class ImmediateThread:
        def __init__(self, target=None, args=(), kwargs=None):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}
            self.daemon = False

        def start(self):
            if self.target:
                self.target(*self.args, **self.kwargs)

    def fake_run(job_id, email, password, file_path, session_dir, session_id, company_id, file_size):
        with app_module.jobs_lock:
            app_module.jobs[job_id]['status'] = 'completed'
            app_module.jobs[job_id]['login_status'] = 'success'
            app_module.jobs[job_id]['login_message'] = 'completed in test'
            app_module.jobs[job_id]['end_time'] = time.time()
            app_module.jobs[job_id]['last_updated'] = time.time()
            app_module.release_queue_identity_locked(job_id, app_module.jobs[job_id])
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        app_module.cleanup_user_session(session_id)
        app_module.unregister_session(session_id)

    monkeypatch.setattr(app_module.threading, 'Thread', ImmediateThread)
    monkeypatch.setattr(app_module, 'run_automation_impl', fake_run)

    started = _upload(client, email='run@example.com')
    payload = started.get_json()
    status_payload = client.get(f"/status/{payload['job_id']}").get_json()

    assert started.status_code == 200
    assert status_payload['status'] == 'completed'
    with app_module.jobs_lock:
        assert len(app_module.job_queue) == 0
