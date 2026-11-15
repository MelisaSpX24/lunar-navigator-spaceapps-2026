"""Validate test-only response fixtures against the unchanged backend model."""
import json
import sys
from copy import deepcopy
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo / 'backend'))
from app.models.analysis import AnalysisResult
from pydantic import ValidationError

fixtures = json.loads((repo / 'frontend/.validation/analysis-result-fixtures.json').read_text())
assert len(fixtures) == 3, 'Run Vitest first to emit the current fixture JSON'
for fixture in fixtures:
    result = AnalysisResult.model_validate(fixture)
    assert result.data_origin == 'TEST_FIXTURE'

invalid = []
for key in ('sun', 'earth'):
    sample = deepcopy(fixtures[0])
    sample['series'][0][key]['disk_visible_fraction'] = 2
    invalid.append(sample)
sample = deepcopy(fixtures[0])
sample['score']['components'][0]['weight'] = -1
invalid.append(sample)
sample = deepcopy(fixtures[0])
sample['sources'][0]['sha256'] = 'invalid'
invalid.append(sample)
for fixture in invalid:
    try:
        AnalysisResult.model_validate(fixture)
    except ValidationError:
        continue
    raise AssertionError('Backend accepted an invalid test control')
print('PASS: 3 TEST_FIXTURE result JSONs accepted; 4 invalid controls rejected. Model compatibility only, not NASA scientific validation. No HTTP or backend write.')
