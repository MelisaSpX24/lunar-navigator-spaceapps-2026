"""Evaluate existing window evidence without opening NASA files or sessions."""

import argparse, json
from pathlib import Path
from app.science.operation_models import OperationEvaluationRequest
from app.science.operations import evaluate_operation
from app.science.window_models import WindowSearchResult


def load_windows(path):
    value = json.loads(Path(path).read_text())
    # Command 07 envelope contains a complete original pilot model, not a summary.
    return WindowSearchResult.model_validate(
        value["pilot"] if value.get("command") == "07" else value
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--request", type=Path, required=True)
    p.add_argument("--windows", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Refusing overwrite")
    request = OperationEvaluationRequest.model_validate_json(a.request.read_text())
    result = evaluate_operation(request, load_windows(a.windows))
    with a.output.open("x") as f:
        json.dump(result.model_dump(mode="json"), f, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
