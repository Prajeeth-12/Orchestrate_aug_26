"""
Test: Pipeline produces identical output on repeated runs (determinism).
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd


def test_deterministic_output():
    from agent_orchestrator import AgentOrchestrator
    from train_pipeline import MessageRoutingPipeline
    from utils.data_loader import DatasetLoader

    dataset_path = str(REPO_ROOT / 'dataset')
    model_dir = str(REPO_ROOT / 'models')
    messages_path = REPO_ROOT / 'dataset' / 'messages.csv'

    messages = pd.read_csv(messages_path).head(10)

    results_a = []
    results_b = []

    for run_results in [results_a, results_b]:
        data_loader = DatasetLoader(dataset_path=dataset_path)
        pipeline = MessageRoutingPipeline(data_loader)
        pipeline.load(model_dir=model_dir)
        orchestrator = AgentOrchestrator(pipeline)

        for _, row in messages.iterrows():
            run_results.append(orchestrator.process_message(row))

    for i in range(len(results_a)):
        a = results_a[i]
        b = results_b[i]
        msg_id = a['message_id']
        assert a['action'] == b['action'], (
            f"{msg_id}: action differs: {a['action']} vs {b['action']}"
        )
        assert a['message_type'] == b['message_type'], (
            f"{msg_id}: type differs: {a['message_type']} vs {b['message_type']}"
        )
        assert abs(a['confidence'] - b['confidence']) < 1e-6, (
            f"{msg_id}: confidence differs: {a['confidence']} vs {b['confidence']}"
        )
        assert a['evidence_message_ids'] == b['evidence_message_ids'], (
            f"{msg_id}: evidence differs"
        )

    print(f"  Verified determinism for {len(results_a)} messages across 2 runs.")


if __name__ == '__main__':
    try:
        test_deterministic_output()
        print("  PASS  test_deterministic_output")
    except AssertionError as e:
        print(f"  FAIL  test_deterministic_output: {e}")
