import os
import sys
import json

# Ensure the project root is on sys.path so backtest_engine can be imported
TEST_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.normpath(os.path.join(TEST_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backtest_engine import run_backtest


def test_backtest_runs_and_outputs_metrics(tmp_path):
    csv_path = os.path.join(PROJECT_ROOT, "data", "EURUSD_M15_sample.csv")
    out_file = tmp_path / "results.json"
    result = run_backtest(csv_path, "classic", output_file=str(out_file))
    assert result is not None
    assert "metrics" in result
    metrics = result["metrics"]
    assert "total_trades" in metrics
    assert "final_balance" in metrics
    # metrics should be numeric
    assert isinstance(metrics.get("final_balance"), (int, float))
