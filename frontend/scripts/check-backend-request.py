"""Validate actual frontend-produced requests without writing to backend/ or HTTP."""
import json
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo / 'backend'))
from app.models.analysis import AnalysisRequest
from pydantic import ValidationError

requests = json.loads((repo / 'frontend/.validation/mission-requests.json').read_text())
assert len(requests) == 10, 'Run the current Vitest suite to produce fresh request samples'
for request in requests:
    AnalysisRequest.model_validate(request)

negative = []
for patch in ({'unexpected': True}, {'site': {**requests[0]['site'], 'longitude_deg_east': 360}},
              {'site': {**requests[0]['site'], 'latitude_deg': -90}},
              {'time': {**requests[0]['time'], 'duration_s': 0}}):
    negative.append({**requests[0], **patch})
for request in negative:
    try:
        AnalysisRequest.model_validate(request)
    except ValidationError:
        continue
    raise AssertionError('Backend unexpectedly accepted an invalid control')
print(f'PASS: {len(requests)} actual frontend JSON requests accepted; {len(negative)} invalid controls rejected. No API request or backend write.')
