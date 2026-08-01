"""
GPU Setup Verification Script

Tests CUDA, PyTorch, and XGBoost GPU support before running training.
Run this first to ensure your RTX 4050 is properly configured.
"""

import sys
from pathlib import Path

def test_cuda():
    """Test CUDA availability via nvidia-smi"""
    print("\n" + "="*80)
    print("1. NVIDIA GPU CHECK (nvidia-smi)")
    print("="*80)

    import subprocess
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        print(result.stdout)
        print("✓ NVIDIA GPU detected via nvidia-smi")
        return True
    except FileNotFoundError:
        print("✗ nvidia-smi not found - NVIDIA drivers may not be installed")
        return False
    except Exception as e:
        print(f"✗ Error running nvidia-smi: {e}")
        return False


def test_pytorch_gpu():
    """Test PyTorch GPU support"""
    print("\n" + "="*80)
    print("2. PYTORCH GPU CHECK")
    print("="*80)

    try:
        import torch
        print(f"✓ PyTorch version: {torch.__version__}")

        if torch.cuda.is_available():
            print(f"✓ CUDA available: True")
            print(f"✓ CUDA version: {torch.version.cuda}")
            print(f"✓ GPU device count: {torch.cuda.device_count()}")

            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                print(f"\n  GPU {i}: {torch.cuda.get_device_name(i)}")
                print(f"    - VRAM: {props.total_memory / 1024**3:.2f} GB")
                print(f"    - Compute capability: {props.major}.{props.minor}")
                print(f"    - Multi-processors: {props.multi_processor_count}")

            # Test GPU tensor operations
            print("\n  Testing GPU tensor operations...")
            x = torch.rand(1000, 1000).cuda()
            y = torch.rand(1000, 1000).cuda()
            z = torch.matmul(x, y)
            print(f"  ✓ Matrix multiplication on GPU successful")
            print(f"  ✓ GPU memory used: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")

            torch.cuda.empty_cache()
            return True
        else:
            print("✗ CUDA not available in PyTorch")
            print("  Install with: pip install torch==2.2.0+cu118 --index-url https://download.pytorch.org/whl/cu118")
            return False

    except ImportError:
        print("✗ PyTorch not installed")
        print("  Install with: pip install torch==2.2.0+cu118 --index-url https://download.pytorch.org/whl/cu118")
        return False
    except Exception as e:
        print(f"✗ Error testing PyTorch GPU: {e}")
        return False


def test_xgboost_gpu():
    """Test XGBoost GPU support"""
    print("\n" + "="*80)
    print("3. XGBOOST GPU CHECK")
    print("="*80)

    try:
        import xgboost as xgb
        import numpy as np

        print(f"✓ XGBoost version: {xgb.__version__}")

        # Create small test dataset
        X = np.random.rand(1000, 10)
        y = np.random.randint(0, 3, 1000)

        # Test GPU training
        print("\n  Testing GPU training...")
        dtrain = xgb.DMatrix(X, label=y)

        params = {
            'tree_method': 'gpu_hist',
            'gpu_id': 0,
            'predictor': 'gpu_predictor',
            'objective': 'multi:softprob',
            'num_class': 3,
            'max_depth': 3,
            'verbosity': 0
        }

        try:
            model = xgb.train(params, dtrain, num_boost_round=10)
            print("  ✓ XGBoost GPU training successful")

            # Test prediction
            preds = model.predict(dtrain)
            print(f"  ✓ XGBoost GPU prediction successful")
            print(f"  ✓ Prediction shape: {preds.shape}")

            return True

        except Exception as e:
            print(f"  ✗ XGBoost GPU training failed: {e}")
            print("  Note: If you see 'gpu_hist not available', rebuild XGBoost with GPU support")
            return False

    except ImportError:
        print("✗ XGBoost not installed")
        print("  Install with: pip install xgboost")
        return False
    except Exception as e:
        print(f"✗ Error testing XGBoost GPU: {e}")
        return False


def test_dependencies():
    """Test other required dependencies"""
    print("\n" + "="*80)
    print("4. DEPENDENCIES CHECK")
    print("="*80)

    required_packages = {
        'pandas': 'pandas',
        'numpy': 'numpy',
        'sklearn': 'scikit-learn',
        'tqdm': 'tqdm',
        'joblib': 'joblib'
    }

    all_installed = True

    for import_name, package_name in required_packages.items():
        try:
            module = __import__(import_name)
            version = getattr(module, '__version__', 'unknown')
            print(f"✓ {package_name}: {version}")
        except ImportError:
            print(f"✗ {package_name} not installed")
            print(f"  Install with: pip install {package_name}")
            all_installed = False

    return all_installed


def test_data_files():
    """Test that required data files exist"""
    print("\n" + "="*80)
    print("5. DATA FILES CHECK")
    print("="*80)

    project_root = Path(__file__).parent.parent
    required_files = [
        "dataset/sample_messages.csv",
        "dataset/messages.csv",
        "dataset/users.csv",
        "dataset/message_history.csv",
        "dataset/message_events.csv"
    ]

    all_exist = True

    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            size = full_path.stat().st_size / 1024
            print(f"✓ {file_path} ({size:.1f} KB)")
        else:
            print(f"✗ {file_path} - NOT FOUND")
            all_exist = False

    return all_exist


def main():
    """Run all GPU setup tests"""
    print("\n" + "="*80)
    print("GPU SETUP VERIFICATION FOR RTX 4050")
    print("Message Notification Router Training Pipeline")
    print("="*80)

    results = {
        'CUDA': test_cuda(),
        'PyTorch GPU': test_pytorch_gpu(),
        'XGBoost GPU': test_xgboost_gpu(),
        'Dependencies': test_dependencies(),
        'Data Files': test_data_files()
    }

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8s} - {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "="*80)

    if all_passed:
        print("✅ ALL TESTS PASSED - Ready for GPU training!")
        print("\nNext step:")
        print("  python code/train_pipeline.py")
    else:
        print("⚠ SOME TESTS FAILED - Fix issues before training")
        print("\nTroubleshooting:")
        print("  1. Install missing packages: pip install -r code/requirements.txt")
        print("  2. Update PyTorch for CUDA: pip install torch==2.2.0+cu118 --index-url https://download.pytorch.org/whl/cu118")
        print("  3. Check NVIDIA drivers: nvidia-smi")
        print("  4. Ensure data files are in dataset/ directory")

    print("="*80 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
