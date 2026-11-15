"""Read-only cross-check against an isolated PR #28 checkout. No source/data writes.
Run with that backend's environment and PYTHONDONTWRITEBYTECODE=1.
"""
import argparse
import json
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--backend-root', type=Path, required=True)
parser.add_argument('--fixtures', type=Path, required=True)
args = parser.parse_args()
sys.dont_write_bytecode = True
sys.path[:0] = [str(args.backend_root / 'backend'), str(args.backend_root)]
from app.models.analysis import AnalysisRequest, AnalysisResult
from app.services.models import AnalysisJobRequest
from app.jobs.models import ScientificJobAccepted, ScientificJobStatus, ScientificJobResult

values = json.loads(args.fixtures.read_text())
for key, model in [('request', AnalysisRequest), ('job_request', AnalysisJobRequest),
                   ('accepted', ScientificJobAccepted), ('status', ScientificJobStatus),
                   ('result', ScientificJobResult), ('analysis', AnalysisResult)]:
    model.model_validate(values[key])
    print(f'PASS {model.__name__}')
print('Controlled fixture format compatibility only; not NASA scientific validation.')

sparse=AnalysisJobRequest.model_validate(values['sparse_job_request'])
assert sparse.analysis.operation.requirements.model_fields_set == {'min_sun_visible_s'}
assert sparse.analysis.operation.requirements.model_dump()['min_solar_disk_visible_fraction'] == 0.5
print('PASS explicit requirement activation retained independently of expanded defaults')
