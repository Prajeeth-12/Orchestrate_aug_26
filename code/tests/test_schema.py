"""
Test: Output CSV schema validation.
Ensures output.csv matches the competition contract exactly.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

OUTPUT_PATH = REPO_ROOT / 'output.csv'
MESSAGES_PATH = REPO_ROOT / 'dataset' / 'messages.csv'

VALID_ACTIONS = {'notify', 'digest', 'mute'}
VALID_TYPES = {
    'personal', 'urgent', 'event', 'payment', 'business_update',
    'promotion', 'greeting', 'forward', 'spam', 'scam', 'unknown'
}
REQUIRED_COLUMNS = ['message_id', 'action', 'message_type', 'reason', 'confidence', 'evidence_message_ids']


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"Output file not found: {OUTPUT_PATH}"


def test_correct_columns():
    df = pd.read_csv(OUTPUT_PATH)
    for col in REQUIRED_COLUMNS:
        assert col in df.columns, f"Missing column: {col}"


def test_row_count_matches():
    messages = pd.read_csv(MESSAGES_PATH)
    output = pd.read_csv(OUTPUT_PATH)
    assert len(output) == len(messages), (
        f"Row count mismatch: output has {len(output)}, messages has {len(messages)}"
    )


def test_all_message_ids_present():
    messages = pd.read_csv(MESSAGES_PATH)
    output = pd.read_csv(OUTPUT_PATH)
    expected_ids = set(messages['message_id'])
    output_ids = set(output['message_id'])
    missing = expected_ids - output_ids
    assert not missing, f"Missing message_ids in output: {missing}"


def test_valid_actions():
    df = pd.read_csv(OUTPUT_PATH)
    invalid = df[~df['action'].isin(VALID_ACTIONS)]
    assert len(invalid) == 0, f"Invalid actions found: {invalid['action'].unique()}"


def test_valid_message_types():
    df = pd.read_csv(OUTPUT_PATH)
    invalid = df[~df['message_type'].isin(VALID_TYPES)]
    assert len(invalid) == 0, f"Invalid message_types: {invalid['message_type'].unique()}"


def test_confidence_range():
    df = pd.read_csv(OUTPUT_PATH)
    out_of_range = df[(df['confidence'] < 0) | (df['confidence'] > 1)]
    assert len(out_of_range) == 0, f"Confidence out of [0,1]: {out_of_range[['message_id', 'confidence']]}"


def test_no_empty_reasons():
    df = pd.read_csv(OUTPUT_PATH)
    empty = df[df['reason'].isna() | (df['reason'].str.strip() == '')]
    assert len(empty) == 0, f"Empty reasons for: {empty['message_id'].tolist()}"


def test_evidence_format():
    df = pd.read_csv(OUTPUT_PATH)
    for _, row in df.iterrows():
        ev = str(row['evidence_message_ids'])
        if ev != 'none':
            parts = ev.split(';')
            for part in parts:
                assert part.startswith('message_'), (
                    f"Invalid evidence format for {row['message_id']}: '{part}'"
                )


if __name__ == '__main__':
    tests = [
        test_output_exists, test_correct_columns, test_row_count_matches,
        test_all_message_ids_present, test_valid_actions, test_valid_message_types,
        test_confidence_range, test_no_empty_reasons, test_evidence_format,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed.")
