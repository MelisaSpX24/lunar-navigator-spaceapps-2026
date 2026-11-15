"""Validate the fresh real-data experiment artifact; not a synthetic NASA substitute.

Run visibility_budget_validation first and set NASA_VISIBILITY_BUDGET_EVIDENCE.
Existing real visibility tests separately execute live geometry/terrain again.
"""
import json,os
from pathlib import Path
import pytest
from app.data.manifest import sha256_file

@pytest.fixture(scope='module')
def experiment():
    path=os.environ.get('NASA_VISIBILITY_BUDGET_EVIDENCE')
    if not path:pytest.skip('Fresh actual NASA budget experiment not supplied')
    r=json.loads(Path(path).read_text())
    for role,source in r['sources'].items():
        ref=source['reference']
        assert sha256_file(Path(os.environ['NASA_LOLA_VALIDATION_DIR'])/ref['product_id'])==ref['raster_sha256']
    assert r['status']=='COMMAND_06_1_COMPLETE_WITH_LIMITATIONS'
    return r


def test_actual_three_utc_completeness(experiment):
    samples=experiment['runs']['complete_series']['samples']
    assert len(samples)==3
    for hour,r in zip([8,9,10],samples):
        assert f'T{hour:02}:00:00' in r['request']['utc']
        assert r['sun']['state']=='NONE' and r['earth']['state']=='FULL'
        for b in ['sun','earth']:
            assert r[b]['unknown_fraction']==0
            assert r[b]['performance']['unknown_directions']==[]
            assert len(r['kernel_ids'])==5
        assert r['performance']['accounting']['failed_budget_attempts']==0


def test_actual_low_budget_is_not_missing_terrain(experiment):
    series=experiment['runs']['low_series']
    assert series['performance']['unknown_bodies']==4
    for r in series['samples'][1:]:
        for b in ['sun','earth']:
            assert r[b]['visible_fraction'] is None
            assert {d['reason'] for d in r[b]['performance']['unknown_directions']}=={'COMPUTATION_BUDGET_EXCEEDED'}


def test_actual_256_convergence(experiment):
    a,b=[experiment['runs'][k] for k in ['first64','real256']]
    for body in ['sun','earth']:
        assert a[body]['visible_fraction']==b[body]['visible_fraction']
        assert b[body]['unknown_fraction']==0
        assert a[body]['center_clearance_deg']==b[body]['center_clearance_deg']
    assert b['performance']['accounting']['completed_rays']>0


def test_actual_1024_status_and_cost(experiment):
    if experiment['real1024_status']=='COMPLETED':
        r=experiment['runs']['real1024']
        assert r['request']['disk_samples']==1024
        assert r['performance']['accounting']['completed_rays']>0
        assert r['sun']['unknown_fraction']==r['earth']['unknown_fraction']==0
    else:
        assert experiment['real1024_status']=='REAL_NASA_1024_NOT_COMPLETED_RESOURCE_LIMIT'
        assert 'real1024' not in experiment['runs']


def test_actual_cache_accounting(experiment):
    repeat=experiment['runs']['repeat64']['performance']['accounting']
    assert repeat['cache_hits']==130 and repeat['completed_rays']==repeat['dem_samples']==0
    small=experiment['cache_capacity_diagnostic']['accounting']
    assert small['cache_evictions']==2 and small['completed_rays']==4
