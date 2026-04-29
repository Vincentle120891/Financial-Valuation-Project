#!/bin/bash
# Install Git Hooks for Model Integrity
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

echo "Installing model integrity hooks..."
mkdir -p "$HOOKS_DIR"

cat > "$HOOKS_DIR/pre-commit" << 'HOOKEOF'
#!/usr/bin/env python3
import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

def main():
    print("=" * 70)
    print("MODEL INTEGRITY PRE-COMMIT CHECK")
    print("=" * 70)
    
    try:
        from app.core.model_integrity import ModelIntegrityValidator, ModelIntegrityError
    except ImportError as e:
        print(f"Warning: Could not import validator: {e}")
        return 0
    
    validator = ModelIntegrityValidator()
    import subprocess
    result = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True)
    
    if result.returncode != 0:
        return 1
    
    staged_files = [f for f in result.stdout.strip().split("\n") if f]
    if not staged_files:
        print("No staged files to check")
        return 0
    
    engine_files = [f for f in staged_files if "engine" in f.lower() and f.endswith(".py")]
    input_files = [f for f in staged_files if "input" in f.lower() and f.endswith(".py")]
    
    validation_errors = []
    for engine_file in engine_files:
        target = Path(engine_file).stem
        try:
            validator.assert_valid(target, edit_type="modify")
            print(f"OK: {engine_file}")
        except ModelIntegrityError:
            validation_errors.append(engine_file)
    
    for input_file in input_files:
        target = Path(input_file).stem
        try:
            validator.assert_valid(target, edit_type="modify")
            print(f"OK: {input_file}")
        except ModelIntegrityError:
            validation_errors.append(input_file)
    
    if validation_errors:
        print("FAILED: Model integrity validation failed")
        return 1
    
    print("PASSED: Model integrity check OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
HOOKEOF

chmod +x "$HOOKS_DIR/pre-commit"
echo "Pre-commit hook installed successfully!"
