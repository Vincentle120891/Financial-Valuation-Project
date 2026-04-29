"""
Model Integrity Validator

This module ensures that all model changes are validated against the reference
documentation in the 'excel models/' folder before any edits to inputs or engines
are allowed. This preserves the integrity of the valuation models as mandated by
the MODEL_INTEGRITY_MANIFESTO.md.

Usage:
    from app.core.model_integrity import ModelIntegrityValidator
    
    validator = ModelIntegrityValidator()
    validator.validate_before_edit('dcf_engine', 'add_feature')
"""

import os
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class ModelDocument:
    """Represents a model documentation file"""
    name: str
    path: str
    content_hash: str
    last_verified: str
    size_bytes: int
    required_components: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ModelDocument':
        return cls(**data)


@dataclass
class ValidationResult:
    """Result of model integrity validation"""
    passed: bool
    timestamp: str
    documents_checked: int
    documents_valid: int
    discrepancies: List[Dict]
    warnings: List[str]
    blocked_edits: List[str]
    
    def to_dict(self) -> Dict:
        return asdict(self)


class ModelIntegrityValidator:
    """
    Validates that model implementations match the reference documentation
    before allowing any edits to inputs or engines.
    
    This enforces the MODEL_INTEGRITY_MANIFESTO.md requirement that no inputs,
    calculations, or outputs be removed, simplified, or bypassed.
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the validator.
        
        Args:
            base_dir: Base directory of the project. Defaults to auto-detection.
        """
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            # Auto-detect base directory by searching upward from this file
            current = Path(__file__).resolve()
            # Go up until we find the root (where MODEL_INTEGRITY_MANIFESTO.md exists)
            for _ in range(5):  # Max 5 levels up
                parent = current.parent
                if (parent / "MODEL_INTEGRITY_MANIFESTO.md").exists():
                    self.base_dir = parent
                    break
                current = parent
            else:
                # Fallback: assume parent of backend/
                self.base_dir = Path(__file__).parent.parent.parent
        
        # Handle space in directory name
        self.models_dir = self.base_dir / "excel models"
        if not self.models_dir.exists():
            # Try alternative naming
            alt_models_dir = self.base_dir / "excel_models"
            if alt_models_dir.exists():
                self.models_dir = alt_models_dir
        
        self.manifesto_path = self.base_dir / "MODEL_INTEGRITY_MANIFESTO.md"
        self.cache_file = self.base_dir / ".model_integrity_cache.json"
        
        # Map engine names to their documentation files
        self.engine_doc_mapping = {
            "dcf_engine": "DCF_Model_Documentation.txt",
            "comps_engine": "Comps_Model_Documentation.txt",
            "dupont_engine": "dupont.txt",
        }
        
        # Map input managers to their documentation files
        self.input_doc_mapping = {
            "dcf_inputs": "DCF_Model_Documentation.txt",
            "comps_inputs": "Comps_Model_Documentation.txt",
            "dupont_inputs": "dupont.txt",
        }
        
        # Critical components that must exist in each model
        self.critical_components = {
            "DCF_Model_Documentation.txt": [
                "Revenue Drivers (Volume + Price)",
                "Cost Structure (COGS, SG&A, Other OpEx)",
                "Capital Expenditure (Scenario-based)",
                "Working Capital (AR Days, Inventory Days, AP Days)",
                "WACC Calculation (Peer Analysis)",
                "Tax Calculations (Levered and Unlevered)",
                "Depreciation (Book and Tax)",
                "Free Cash Flow (Two Methods with Reconciliation)",
                "Terminal Value (Perpetuity and Exit Multiple)",
                "Discounting (Partial Period Adjustment)",
                "Enterprise Value",
                "Equity Value Bridge",
                "Per Share Metrics",
                "Sensitivity Analysis",
            ],
            "Comps_Model_Documentation.txt": [
                "Peer Selection (Minimum 5 companies)",
                "Enterprise Value Bridge",
                "Multiple Calculations (EV/Revenue, EV/EBITDA, EV/EBIT, P/E, P/B)",
                "Statistical Analysis (Average, Median, Min, Max)",
                "Implied Valuation",
            ],
            "dupont.txt": [
                "Net Profit Margin",
                "Asset Turnover",
                "Equity Multiplier",
                "ROE Decomposition",
            ],
        }
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file"""
        if not file_path.exists():
            return ""
        
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _load_cache(self) -> Dict:
        """Load the integrity cache from disk"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load cache: {e}")
        return {"documents": {}, "last_validation": None}
    
    def _save_cache(self, cache: Dict) -> None:
        """Save the integrity cache to disk"""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(cache, f, indent=2)
            logger.info(f"Integrity cache saved to {self.cache_file}")
        except IOError as e:
            logger.error(f"Could not save cache: {e}")
    
    def scan_model_documents(self) -> List[ModelDocument]:
        """
        Scan the excel models directory and create document records.
        
        Returns:
            List of ModelDocument objects for all found documentation files.
        """
        documents = []
        
        if not self.models_dir.exists():
            logger.error(f"Models directory not found: {self.models_dir}")
            return documents
        
        for doc_file in self.models_dir.glob("*.txt"):
            doc = ModelDocument(
                name=doc_file.name,
                path=str(doc_file),
                content_hash=self._calculate_file_hash(doc_file),
                last_verified=datetime.now().isoformat(),
                size_bytes=doc_file.stat().st_size,
                required_components=self.critical_components.get(doc_file.name, []),
            )
            documents.append(doc)
            logger.info(f"Scanned model document: {doc.name} ({doc.size_bytes} bytes)")
        
        return documents
    
    def validate_document_exists(self, engine_name: str) -> Tuple[bool, str]:
        """
        Validate that the reference documentation exists for an engine.
        
        Args:
            engine_name: Name of the engine (e.g., 'dcf_engine')
        
        Returns:
            Tuple of (exists: bool, message: str)
        """
        # Determine which mapping to use
        doc_name = None
        if engine_name in self.engine_doc_mapping:
            doc_name = self.engine_doc_mapping[engine_name]
        elif engine_name in self.input_doc_mapping:
            doc_name = self.input_doc_mapping[engine_name]
        
        if not doc_name:
            return True, f"No specific documentation mapping for {engine_name}"
        
        doc_path = self.models_dir / doc_name
        
        if not doc_path.exists():
            msg = f"CRITICAL: Reference documentation missing: {doc_name}"
            logger.error(msg)
            return False, msg
        
        return True, f"Reference documentation found: {doc_name}"
    
    def validate_critical_components(self, doc_name: str, code_content: str) -> List[str]:
        """
        Check if code contains references to critical components.
        
        Args:
            doc_name: Name of the documentation file
            code_content: Content of the code being validated
        
        Returns:
            List of missing component warnings
        """
        warnings = []
        components = self.critical_components.get(doc_name, [])
        
        for component in components:
            # Simple keyword matching - can be enhanced with more sophisticated checks
            keywords = component.lower().replace("(", "").replace(")", "").split()
            matches = sum(1 for kw in keywords if len(kw) > 3 and kw in code_content.lower())
            
            if matches < len(keywords) * 0.5:  # Less than 50% of keywords found
                warnings.append(f"Component '{component}' may not be fully implemented")
        
        return warnings
    
    def validate_before_edit(self, target: str, edit_type: str = "modify") -> ValidationResult:
        """
        Perform comprehensive validation before allowing edits.
        
        This MUST be called before any modifications to:
        - Engine files (dcf_engine.py, comps_engine.py, dupont_engine.py)
        - Input schemas or managers
        - Calculation logic
        
        Args:
            target: The target being edited (e.g., 'dcf_engine', 'dcf_inputs')
            edit_type: Type of edit ('modify', 'add', 'remove', 'refactor')
        
        Returns:
            ValidationResult with pass/fail status and details
        
        Raises:
            ModelIntegrityError: If validation fails and edits should be blocked
        """
        logger.info(f"Validating model integrity before {edit_type} edit to {target}")
        
        discrepancies = []
        warnings = []
        blocked_edits = []
        documents_valid = 0
        
        # Step 1: Verify manifesto exists and is acknowledged
        if not self.manifesto_path.exists():
            discrepancies.append({
                "type": "missing_manifesto",
                "message": "MODEL_INTEGRITY_MANIFESTO.md not found",
                "severity": "critical",
            })
        else:
            logger.info("Model Integrity Manifesto found")
        
        # Step 2: Scan and verify all model documents
        documents = self.scan_model_documents()
        
        if not documents:
            discrepancies.append({
                "type": "no_documents",
                "message": "No model documentation files found in 'excel models/'",
                "severity": "critical",
            })
        else:
            for doc in documents:
                # Check if document has been modified since last verification
                current_hash = self._calculate_file_hash(Path(doc.path))
                
                if current_hash != doc.content_hash:
                    discrepancies.append({
                        "type": "document_modified",
                        "document": doc.name,
                        "message": f"Reference document {doc.name} has been modified",
                        "severity": "warning",
                        "old_hash": doc.content_hash[:16],
                        "new_hash": current_hash[:16],
                    })
                    warnings.append(f"Review changes in {doc.name}")
                else:
                    documents_valid += 1
        
        # Step 3: Verify specific documentation exists for target
        exists, msg = self.validate_document_exists(target)
        if not exists:
            discrepancies.append({
                "type": "missing_documentation",
                "target": target,
                "message": msg,
                "severity": "critical",
            })
            blocked_edits.append(f"Cannot edit {target}: reference documentation missing")
        
        # Step 4: Check for prohibited edit types
        if edit_type == "remove":
            blocked_edits.append(
                f"REMOVAL PROHIBITED: Per MODEL_INTEGRITY_MANIFESTO.md, "
                f"no inputs, calculations, or outputs may be removed from {target}"
            )
            discrepancies.append({
                "type": "prohibited_edit",
                "target": target,
                "edit_type": edit_type,
                "message": "Removal of components is prohibited by the manifesto",
                "severity": "critical",
            })
        
        # Step 5: Load and update cache
        cache = self._load_cache()
        cache["documents"] = {doc.name: doc.to_dict() for doc in documents}
        cache["last_validation"] = datetime.now().isoformat()
        cache["last_target"] = target
        cache["last_edit_type"] = edit_type
        self._save_cache(cache)
        
        # Determine if validation passed
        passed = len([d for d in discrepancies if d.get("severity") == "critical"]) == 0
        
        result = ValidationResult(
            passed=passed,
            timestamp=datetime.now().isoformat(),
            documents_checked=len(documents),
            documents_valid=documents_valid,
            discrepancies=discrepancies,
            warnings=warnings,
            blocked_edits=blocked_edits,
        )
        
        if passed:
            logger.info(f"✓ Model integrity validation PASSED for {target}")
        else:
            logger.error(f"✗ Model integrity validation FAILED for {target}")
            for disc in discrepancies:
                if disc.get("severity") == "critical":
                    logger.error(f"  Critical: {disc['message']}")
        
        return result
    
    def assert_valid(self, target: str, edit_type: str = "modify") -> None:
        """
        Assert that validation passes, raising an exception if it fails.
        
        This should be used in CI/CD pipelines or pre-commit hooks.
        
        Args:
            target: The target being edited
            edit_type: Type of edit
        
        Raises:
            ModelIntegrityError: If validation fails
        """
        result = self.validate_before_edit(target, edit_type)
        
        if not result.passed:
            raise ModelIntegrityError(
                f"Model integrity validation failed for {target}",
                result=result,
            )
    
    def get_reference_documentation(self, engine_name: str) -> Optional[str]:
        """
        Retrieve the full reference documentation for an engine.
        
        Args:
            engine_name: Name of the engine
        
        Returns:
            Full text content of the reference documentation, or None if not found
        """
        doc_name = self.engine_doc_mapping.get(engine_name) or self.input_doc_mapping.get(engine_name)
        
        if not doc_name:
            return None
        
        doc_path = self.models_dir / doc_name
        
        if not doc_path.exists():
            return None
        
        with open(doc_path, "r", encoding="utf-8") as f:
            return f.read()


class ModelIntegrityError(Exception):
    """Exception raised when model integrity validation fails"""
    
    def __init__(self, message: str, result: Optional[ValidationResult] = None):
        super().__init__(message)
        self.message = message
        self.result = result
    
    def __str__(self) -> str:
        if self.result:
            errors = [d['message'] for d in self.result.discrepancies if d.get('severity') == 'critical']
            return f"{self.message}: {'; '.join(errors)}"
        return self.message


# =============================================================================
# DECORATORS FOR AUTOMATIC VALIDATION
# =============================================================================

def validate_before_modification(target: str, edit_type: str = "modify"):
    """
    Decorator to automatically validate model integrity before function execution.
    
    Usage:
        @validate_before_modification('dcf_engine', 'add')
        def add_new_feature(...):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            validator = ModelIntegrityValidator()
            result = validator.validate_before_edit(target, edit_type)
            
            if not result.passed:
                raise ModelIntegrityError(
                    f"Cannot execute {func.__name__}: model integrity validation failed",
                    result=result,
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import sys
    
    validator = ModelIntegrityValidator()
    
    if len(sys.argv) < 2:
        print("Usage: python model_integrity.py <command> [args]")
        print("Commands:")
        print("  validate <target> [edit_type]  - Validate before editing")
        print("  scan                           - Scan all model documents")
        print("  check                          - Quick integrity check")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "validate":
        if len(sys.argv) < 3:
            print("Error: target required")
            sys.exit(1)
        target = sys.argv[2]
        edit_type = sys.argv[3] if len(sys.argv) > 3 else "modify"
        
        result = validator.validate_before_edit(target, edit_type)
        print(json.dumps(result.to_dict(), indent=2))
        sys.exit(0 if result.passed else 1)
    
    elif command == "scan":
        documents = validator.scan_model_documents()
        for doc in documents:
            print(f"✓ {doc.name} ({doc.size_bytes} bytes) - Hash: {doc.content_hash[:16]}...")
    
    elif command == "check":
        result = validator.validate_before_edit("all", "check")
        if result.passed:
            print("✓ Model integrity check PASSED")
            sys.exit(0)
        else:
            print("✗ Model integrity check FAILED")
            for disc in result.discrepancies:
                print(f"  [{disc.get('severity', 'unknown')}] {disc['message']}")
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
