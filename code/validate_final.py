import pandas as pd

def validate():
    df = pd.read_csv('output.csv')
    samples = pd.read_csv('dataset/sample_messages.csv')
    
    # Schema
    assert len(df) == 110, f"Expected 110, got {len(df)}"
    assert df['message_id'].nunique() == 110
    
    # Accuracy on samples
    sample_out = pd.read_csv('sample_output.csv')
    merged = samples.merge(sample_out, on='message_id', suffixes=('_true', '_pred'))
    
    action_acc = (merged['action_true'] == merged['action_pred']).mean()
    type_acc = (merged['message_type_true'] == merged['message_type_pred']).mean()
    
    print(f"Action: {action_acc*100:.1f}%")
    print(f"Type: {type_acc*100:.1f}%")
    
    assert action_acc == 1.0, f"Action accuracy dropped to {action_acc*100:.1f}%!"
    assert type_acc >= 0.85, f"Type accuracy {type_acc*100:.1f}% < 85% target"
    
    print("✓ ALL CHECKS PASS")

if __name__ == "__main__":
    validate()
