"""
FastAPI web application for X-Ray dashboard.
Provides API endpoints for the React frontend.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
import sys
import json
import tempfile
import io
from typing import Optional, Dict, Any, List

# Add parent directory to path to import xray
sys.path.insert(0, str(Path(__file__).parent.parent))
from xray.storage_sqlite import SQLiteStorage
from xray.rules import RuleConfig
from xray import XRay
from xray.workflow_engine import GenericWorkflowEngine
from xray.workflow import apply_filters_with_rules, rank_and_select_with_rules

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

app = FastAPI(title="X-Ray Dashboard API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:5174"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = SQLiteStorage()
rules_config = RuleConfig()  # Load rules from CSV
workflow_engine = GenericWorkflowEngine(storage=storage)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "X-Ray Dashboard API", "version": "1.0.0"}


@app.get("/api/executions")
async def list_executions(limit: int = 100):
    """API endpoint to list all executions."""
    executions = storage.list_executions(limit=limit)
    return executions


@app.get("/api/executions/{execution_id}")
async def get_execution(execution_id: str):
    """API endpoint to get a specific execution."""
    execution = storage.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@app.get("/api/rules")
async def get_rules():
    """API endpoint to get current rules configuration."""
    try:
        filters = rules_config.get_filters()
        ranking = rules_config.get_ranking_criteria()
        
        return {
            'filters': filters,
            'ranking': ranking,
            'rules_file': rules_config.rules_file,
            'all_rules': rules_config.rules
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rules")
async def set_rules(data: Dict[str, Any]):
    """API endpoint to set rules from frontend (CSV or JSON)."""
    try:
        if not data:
            raise HTTPException(status_code=400, detail="No data provided")
        
        rules_source = data.get('rules')
        rules_format = data.get('format', 'json')  # 'json' or 'csv'
        
        if not rules_source:
            raise HTTPException(status_code=400, detail="No rules provided")
        
        # Create temporary rules config
        if rules_format == 'csv':
            # Save CSV to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write(rules_source)
                temp_file = f.name
            
            new_rules = RuleConfig(temp_file)
        elif rules_format == 'json':
            # Parse JSON and create rules config
            try:
                if isinstance(rules_source, str):
                    rules_data = json.loads(rules_source)
                else:
                    rules_data = rules_source
                
                new_rules = RuleConfig(rules_data)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {rules_format}")
        
        # Return success with rules info
        return {
            'success': True,
            'rules_count': len(new_rules.rules),
            'filters': new_rules.get_filters(),
            'ranking': new_rules.get_ranking_criteria()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflow/run")
async def run_workflow(data: Dict[str, Any]):
    """API endpoint to run workflow with provided rules and input data."""
    try:
        if not data:
            raise HTTPException(status_code=400, detail="No data provided")
        
        # Get rules from request
        rules_source = data.get('rules')
        rules_format = data.get('rules_format', 'json')
        input_data = data.get('input_data', {})
        
        # Create rules config
        if rules_source:
            if rules_format == 'csv':
                with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                    f.write(rules_source)
                    temp_file = f.name
                rules = RuleConfig(temp_file)
            elif rules_format == 'json':
                if isinstance(rules_source, str):
                    rules_data = json.loads(rules_source)
                else:
                    rules_data = rules_source
                rules = RuleConfig(rules_data)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported rules format: {rules_format}")
        else:
            # Use default rules
            rules = RuleConfig()
        
        # Get execution name from request if provided
        execution_name = data.get('execution_name') or input_data.get('execution_name') or input_data.get('name')
        
        # Run workflow with custom function that accepts rules directly
        execution_id = run_workflow_with_rules(input_data, rules, execution_name=execution_name)
        
        return {
            'success': True,
            'execution_id': execution_id,
            'message': 'Workflow executed successfully'
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_workflow_with_rules(input_data: dict, rules: RuleConfig, execution_name: Optional[str] = None):
    """Run workflow with provided rules config."""
    # Get execution name from input_data or use provided name
    exec_name = execution_name or input_data.get('execution_name') or input_data.get('name') or "Workflow Execution"
    
    with XRay(storage=storage, name=exec_name) as xray:
        xray.add_metadata("workflow", "generic_multi_step")
        xray.add_metadata("name", exec_name)  # Add name to metadata for retrieval
        xray.add_metadata("input_data", input_data)
        xray.add_metadata("rules_source", "frontend_input")
        
        # Step 1: Generate candidates (extract from input_data or use provided candidates)
        candidates = input_data.get('candidates', [])
        if not candidates:
            # If no candidates provided, this is an error - candidates must be provided
            raise ValueError("No candidates provided in input_data. Please provide 'candidates' field.")
        
        xray.record_step(
            step_name="generate_candidates",
            step_type="transformation",
            input_data=input_data,
            output_data={
                "candidates_count": len(candidates),
                "candidates": candidates[:5]
            },
            reasoning=f"Generated {len(candidates)} candidate items"
        )
        
        # Step 2: Apply filters using xray library
        filter_result = apply_filters_with_rules(
            candidates, 
            rules, 
            step_name='apply_filters',
            reference=input_data.get('reference')
        )
        
        # Convert evaluations to canonical format with detailed reasoning
        canonical_evaluations = []
        for eval_item in filter_result["evaluations"]:
            checks = []
            filters_passed = eval_item.get('filters_passed_count', 0)
            total_filters = eval_item.get('total_filters', 0)
            
            for rule_name, result in eval_item.get("filter_results", {}).items():
                # Build detailed reason for each filter check with field and value
                detail = result.get("detail", result.get("reason", ""))
                field = result.get("field", rule_name)
                field_value = result.get("field_value", "N/A")
                expected = result.get("expected", "")
                actual = result.get("actual", f"{field} = {field_value}")
                
                if result.get("passed", False):
                    reason = f"✓ Passed {rule_name}: {field} = {field_value} satisfies {expected}"
                else:
                    reason = f"✗ Failed {rule_name}: {field} = {field_value} does not satisfy {expected}"
                
                checks.append({
                    "rule": rule_name,
                    "passed": result.get("passed", False),
                    "expected": expected or f"Check {rule_name}",
                    "actual": actual,
                    "reason": reason,
                    "field": field,
                    "field_value": field_value
                })
            
            # Add summary check showing overall filter status
            if total_filters > 0:
                if filters_passed == total_filters:
                    summary_reason = f"✓ PASSED all {total_filters} filters: {', '.join([name for name, r in eval_item.get('filter_results', {}).items() if r.get('passed', False)])}"
                else:
                    passed_filters = [name for name, r in eval_item.get('filter_results', {}).items() if r.get('passed', False)]
                    failed_filters = [name for name, r in eval_item.get('filter_results', {}).items() if not r.get('passed', True)]
                    summary_reason = f"Passed {filters_passed}/{total_filters} filters. Passed: {', '.join(passed_filters) if passed_filters else 'none'}. Failed: {', '.join(failed_filters) if failed_filters else 'none'}."
                
                checks.append({
                    "rule": "filter_summary",
                    "passed": filters_passed == total_filters,
                    "expected": f"Pass all {total_filters} filters",
                    "actual": f"Passed {filters_passed}/{total_filters} filters",
                    "reason": summary_reason
                })
            
            canonical_evaluations.append({
                "entity_id": eval_item.get("item_id", ""),
                "attributes": eval_item.get("metrics", {}),
                "checks": checks,
                "final_decision": "accepted" if eval_item.get("passed", False) else "rejected"
            })
        
        # Get rules in canonical format
        filter_rules = rules.get_filters('apply_filters')
        canonical_rules = []
        for rule in filter_rules:
            canonical_rules.append({
                "name": rule.get('name', 'unnamed'),
                "type": rule.get('rule_type', 'threshold'),
                "value": rule.get('value') or rule.get('min') or rule.get('max'),
                "source": "config"
            })
        
        filter_reasoning = rules.generate_filter_reasoning(
            filter_result["evaluations"],
            step_name="apply_filters"
        )
        
        xray.record_step(
            step_name="apply_filters",
            step_type="filter",
            input_data={
                "candidates_count": len(candidates),
                "reference": input_data.get('reference')
            },
            rules=canonical_rules,
            evaluations=canonical_evaluations,
            output_data={
                "total_evaluated": filter_result["total_evaluated"],
                "passed": filter_result["passed"],
                "failed": filter_result["failed"]
            },
            reasoning=filter_reasoning
        )
        
        # Step 3: Rank and select (using ALL evaluations, not just qualified) using xray library
        ranking_result = rank_and_select_with_rules(
            filter_result["evaluations"], 
            rules, 
            step_name='rank_and_select',
            reference=input_data.get('reference')
        )
        
        # Convert ranked candidates to canonical evaluations format with detailed reasoning
        canonical_ranked_evaluations = []
        for candidate in ranking_result["ranked_candidates"]:
            filters_passed = candidate.get('filters_passed_count', 0)
            total_filters = candidate.get('total_filters', 0)
            criteria_score = candidate.get('criteria_score', candidate.get('total_score', 0))
            rank = candidate.get('rank', 'N/A')
            
            checks = []
            
            # Add filter pass information
            if total_filters > 0:
                filter_results = candidate.get('filter_results', {})
                passed_filter_names = [name for name, r in filter_results.items() if r.get('passed', False)]
                
                if filters_passed == total_filters:
                    filter_reason = f"✓ Passed all {total_filters} filters: {', '.join(passed_filter_names)}"
                else:
                    filter_reason = f"Passed {filters_passed}/{total_filters} filters: {', '.join(passed_filter_names) if passed_filter_names else 'none'}"
                
                checks.append({
                    "rule": "filters_passed",
                    "passed": filters_passed == total_filters,
                    "expected": f"Pass all {total_filters} filters",
                    "actual": f"Passed {filters_passed}/{total_filters} filters",
                    "reason": filter_reason
                })
            
            # Add ranking score information
            score_breakdown = candidate.get('score_breakdown', {})
            breakdown_str = ", ".join([f"{k}={v}" for k, v in score_breakdown.items()]) if score_breakdown else ""
            
            ranking_reason = f"Rank #{rank} with criteria score: {criteria_score:.2f}"
            if breakdown_str:
                ranking_reason += f" (breakdown: {breakdown_str})"
            
            checks.append({
                "rule": "ranking_score",
                "passed": True,
                "expected": "Higher is better",
                "actual": f"Score: {criteria_score:.2f}",
                "reason": ranking_reason
            })
            
            canonical_ranked_evaluations.append({
                "entity_id": candidate.get("item_id", ""),
                "attributes": candidate.get("metrics", {}),
                "checks": checks,
                "final_decision": "selected" if candidate.get("item_id") == ranking_result["selection"].get("item_id") else "not_selected"
            })
        
        # Get ranking criteria as rules
        ranking_criteria = ranking_result["ranking_criteria"]
        canonical_ranking_rules = []
        if ranking_criteria.get("primary"):
            canonical_ranking_rules.append({
                "name": "primary_ranking",
                "type": "ranking",
                "value": ranking_criteria.get("primary"),
                "source": "config"
            })
        if ranking_criteria.get("secondary"):
            canonical_ranking_rules.append({
                "name": "secondary_ranking",
                "type": "ranking",
                "value": ranking_criteria.get("secondary"),
                "source": "config"
            })
        
        ranking_reasoning = rules.generate_ranking_reasoning(
            ranking_result["ranked_candidates"],
            ranking_result["selected_item"],
            step_name="rank_and_select"
        )
        
        xray.record_step(
            step_name="rank_and_select",
            step_type="ranking",
            input_data={
                "candidates_count": len(filter_result["qualified_candidates"]),
                "reference": input_data.get('reference')
            },
            rules=canonical_ranking_rules,
            evaluations=canonical_ranked_evaluations,
            output_data={
                "selected_item": ranking_result["selected_item"],
                "total_ranked": len(ranking_result["ranked_candidates"])
            },
            reasoning=ranking_reasoning
        )
        
        return xray.execution_id


# ============================================================================
# Generic Workflow System API Endpoints
# ============================================================================

@app.post("/api/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """
    Upload a dataset file (CSV, Excel, JSON) and detect schema.
    Returns dataset ID, schema, and preview.
    
    Note: Maximum file size is 100MB (configured in frontend).
    FastAPI/Starlette default limit is 100MB, which should be sufficient.
    If you need larger files, configure uvicorn with --limit-request-line and --limit-request-fields.
    """
    if not PANDAS_AVAILABLE:
        raise HTTPException(status_code=500, detail="pandas is required for file upload. Install with: pip install pandas openpyxl")
    
    try:
        # Read file content
        contents = await file.read()
        file_extension = file.filename.split('.')[-1].lower()
        
        # Quick check: if file is too small or looks binary, reject early
        if len(contents) < 10:
            raise HTTPException(status_code=400, detail="File appears to be empty or too small")
        
        # Remove null bytes (NUL characters) that can cause parsing errors
        # This handles files that may have been corrupted or have embedded nulls
        if b'\x00' in contents:
            # Count null bytes to decide if we should reject or clean
            null_byte_count = contents.count(b'\x00')
            null_byte_ratio = null_byte_count / len(contents)
            
            if null_byte_ratio > 0.1:  # More than 10% null bytes suggests binary
                raise HTTPException(
                    status_code=400, 
                    detail="File appears to be binary format. Please ensure you're uploading a text-based CSV file."
                )
            else:
                # Remove null bytes (likely encoding issues or corrupted text)
                contents = contents.replace(b'\x00', b'')
        
        # Parse based on file type
        df = None
        if file_extension == 'csv':
            # Try to detect encoding first using chardet if available
            detected_encoding = None
            try:
                import chardet
                detected = chardet.detect(contents[:10000])  # Sample first 10KB
                if detected and detected['encoding'] and detected['confidence'] > 0.7:
                    detected_encoding = detected['encoding']
            except ImportError:
                pass
            
            # Build encoding list with detected encoding first
            encodings = []
            if detected_encoding:
                encodings.append(detected_encoding)
            encodings.extend(['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252'])
            
            for encoding in encodings:
                try:
                    # Try with Python engine first (more forgiving)
                    # Use error_bad_lines parameter for older pandas, on_bad_lines for newer
                    try:
                        # Try newer pandas API first
                        df = pd.read_csv(
                            io.BytesIO(contents), 
                            encoding=encoding,
                            sep=None,  # Auto-detect separator
                            engine='python',
                            on_bad_lines='skip',  # Skip bad lines instead of erroring
                            quoting=1  # QUOTE_ALL
                        )
                    except TypeError:
                        # Fall back to older pandas API
                        df = pd.read_csv(
                            io.BytesIO(contents), 
                            encoding=encoding,
                            sep=None,
                            engine='python',
                            error_bad_lines=False,  # Skip bad lines (older pandas)
                            warn_bad_lines=False,
                            quoting=1
                        )
                    
                    # Validate that we got readable data
                    if df is not None and not df.empty:
                        # Check if column names are readable (not binary garbage)
                        first_col = str(df.columns[0]) if len(df.columns) > 0 else ""
                        # If column name is very long or has many non-printable chars, it's likely binary
                        if first_col and len(first_col) < 100:
                            # Check if it's mostly printable ASCII or common UTF-8 chars
                            printable_ratio = sum(1 for c in first_col[:50] if c.isprintable() or c.isspace()) / min(50, len(first_col))
                            if printable_ratio > 0.7:  # At least 70% printable
                                break
                        elif not first_col:
                            # Empty column name, try next encoding
                            df = None
                            continue
                except (UnicodeDecodeError, UnicodeError):
                    df = None
                    continue
                except Exception:
                    df = None
                    # Try with comma separator explicitly
                    try:
                        try:
                            df = pd.read_csv(
                                io.BytesIO(contents), 
                                encoding=encoding,
                                sep=',',
                                engine='python',
                                on_bad_lines='skip',
                                quoting=1
                            )
                        except TypeError:
                            df = pd.read_csv(
                                io.BytesIO(contents), 
                                encoding=encoding,
                                sep=',',
                                engine='python',
                                error_bad_lines=False,
                                warn_bad_lines=False,
                                quoting=1
                            )
                        # Validate again
                        if df is not None and not df.empty:
                            first_col = str(df.columns[0]) if len(df.columns) > 0 else ""
                            if first_col and len(first_col) < 100:
                                printable_ratio = sum(1 for c in first_col[:50] if c.isprintable() or c.isspace()) / min(50, len(first_col))
                                if printable_ratio > 0.7:
                                    break
                    except Exception:
                        df = None
                        continue
            
            if df is None or df.empty:
                # Last resort: decode with error handling and try again
                try:
                    # Decode bytes with error handling first
                    contents_str = contents.decode('utf-8', errors='replace')
                    try:
                        df = pd.read_csv(
                            io.StringIO(contents_str), 
                            sep=None,
                            engine='python',
                            on_bad_lines='skip',
                            quoting=1
                        )
                    except TypeError:
                        df = pd.read_csv(
                            io.StringIO(contents_str), 
                            sep=None,
                            engine='python',
                            error_bad_lines=False,
                            warn_bad_lines=False,
                            quoting=1
                        )
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Could not parse CSV file. Please ensure the file is a valid CSV with UTF-8 encoding: {str(e)}")
        elif file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(io.BytesIO(contents))
        elif file_extension == 'json':
            # Try multiple encodings for JSON as well
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'iso-8859-1', 'cp1252']
            for encoding in encodings:
                try:
                    contents_str = contents.decode(encoding)
                    df = pd.read_json(io.StringIO(contents_str))
                    break
                except (UnicodeDecodeError, UnicodeError, ValueError):
                    continue
            if df is None:
                # Last resort: use errors='replace'
                contents_str = contents.decode('utf-8', errors='replace')
                df = pd.read_json(io.StringIO(contents_str))
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")
        
        # Clean column names - remove any binary/encoding issues and BOM
        # First, check if columns look like binary data - if so, try using first data row as headers
        if len(df.columns) > 0 and not df.empty:
            first_col = str(df.columns[0])
            # If first column name looks like binary data (very long or many non-printable)
            non_printable_count = sum(1 for c in first_col[:100] if not (c.isprintable() or c.isspace()))
            if len(first_col) > 50 or non_printable_count > 10:
                # Try using first data row as column names
                try:
                    first_row = df.iloc[0]
                    potential_headers = []
                    for val in first_row:
                        header_str = str(val).strip() if pd.notna(val) else ""
                        # Clean potential header
                        if header_str.startswith('\ufeff'):
                            header_str = header_str[1:]
                        header_str = ''.join(c for c in header_str if c.isprintable() or c.isspace()).strip()
                        # Check if this looks like a real header (not binary)
                        if header_str and len(header_str) < 100 and sum(1 for c in header_str[:50] if c.isprintable() or c.isspace()) / min(50, len(header_str)) > 0.8:
                            potential_headers.append(header_str)
                        else:
                            potential_headers.append(f"column_{len(potential_headers) + 1}")
                    
                    # If we got reasonable headers, use them
                    if potential_headers and len(potential_headers[0]) < 100:
                        df.columns = potential_headers
                        df = df.iloc[1:].reset_index(drop=True)  # Remove first row (was headers)
                except Exception:
                    pass  # If that fails, continue with cleaning existing columns
        
        cleaned_columns = []
        for col in df.columns:
            col_str = str(col).strip()
            # Remove BOM if present
            if col_str.startswith('\ufeff'):
                col_str = col_str[1:]
            # Remove any non-printable characters
            col_str = ''.join(c for c in col_str if c.isprintable() or c.isspace()).strip()
            # If column name is still garbage or too long, use a default name
            if not col_str or len(col_str) > 100 or sum(1 for c in col_str[:50] if not (c.isprintable() or c.isspace())) > 5:
                col_str = f"column_{len(cleaned_columns) + 1}"
            cleaned_columns.append(col_str)
        
        df.columns = cleaned_columns
        
        # Validate DataFrame is valid
        if df is None or df.empty:
            raise HTTPException(status_code=400, detail="Could not parse file. File appears to be empty or invalid.")
        
        # Clean data values - remove any binary artifacts (only for string columns, be careful with large datasets)
        try:
            for col in df.columns:
                if df[col].dtype == 'object':  # String columns
                    # Only clean if column has string data
                    sample_val = df[col].dropna().iloc[0] if len(df[col].dropna()) > 0 else None
                    if sample_val and isinstance(sample_val, str):
                        # Clean only if needed (check if has non-printable chars)
                        if any(not (c.isprintable() or c.isspace()) for c in str(sample_val)[:100]):
                            df[col] = df[col].astype(str).apply(
                                lambda x: ''.join(c for c in str(x) if c.isprintable() or c.isspace()).strip() 
                                if pd.notna(x) and isinstance(x, str) else ("" if pd.isna(x) else x)
                            )
        except Exception as e:
            # If cleaning fails, continue with original data
            pass
        
        # Detect schema
        schema = {}
        for col in df.columns:
            try:
                dtype = str(df[col].dtype)
                # Infer type
                if 'int' in dtype:
                    schema[col] = "number"
                elif 'float' in dtype:
                    schema[col] = "number"
                elif 'bool' in dtype:
                    schema[col] = "boolean"
                else:
                    schema[col] = "string"
            except Exception:
                schema[col] = "string"  # Default to string if detection fails
        
        # Convert to list of dicts and clean data (limit preview to avoid memory issues)
        preview_rows = []
        try:
            for idx, row in df.head(10).iterrows():  # Only first 10 for preview
                clean_row = {}
                for col in df.columns:
                    try:
                        value = row[col]
                        # Clean the value
                        if pd.isna(value):
                            clean_row[col] = ""
                        elif isinstance(value, str):
                            # Remove non-printable characters, limit length
                            clean_value = ''.join(c for c in value if c.isprintable() or c.isspace()).strip()
                            clean_row[col] = clean_value[:500]  # Limit length
                        else:
                            clean_row[col] = value
                    except Exception:
                        clean_row[col] = ""
                preview_rows.append(clean_row)
        except Exception as e:
            # If preview generation fails, create minimal preview
            preview_rows = [{"error": f"Could not generate preview: {str(e)}"}]
        
        # Full dataset for storage (store as-is, clean on access)
        try:
            full_rows = df.fillna("").to_dict('records')
            # Clean full rows
            for row in full_rows:
                for key in list(row.keys()):
                    value = row[key]
                    if isinstance(value, str):
                        # Clean string values
                        row[key] = ''.join(c for c in value if c.isprintable() or c.isspace()).strip()
        except Exception as e:
            # If conversion fails, try simpler approach
            try:
                full_rows = df.to_dict('records')
            except Exception:
                raise HTTPException(status_code=400, detail=f"Could not convert data to records: {str(e)}")
        
        # Generate dataset ID
        import hashlib
        dataset_id = hashlib.md5(file.filename.encode() + str(len(full_rows)).encode()).hexdigest()[:8]
        
        # Store dataset (in-memory for now, can be extended to use storage)
        if not hasattr(storage, '_datasets'):
            storage._datasets = {}
        storage._datasets[dataset_id] = {
            "dataset_id": dataset_id,
            "filename": file.filename,
            "schema": schema,
            "rows": full_rows,
            "row_count": len(full_rows)
        }
        
        # Final validation - ensure schema keys are readable
        clean_schema = {}
        clean_fields = []
        for col in df.columns:
            try:
                col_clean = str(col).strip()
                # Remove BOM and non-printable chars
                if col_clean.startswith('\ufeff'):
                    col_clean = col_clean[1:]
                col_clean = ''.join(c for c in col_clean if c.isprintable() or c.isspace()).strip()
                # If still garbage, use default name
                if not col_clean or len(col_clean) > 100:
                    col_clean = f"column_{len(clean_fields) + 1}"
                if col_clean:
                    clean_schema[col_clean] = schema.get(col, "string")
                    clean_fields.append(col_clean)
            except Exception:
                # Skip problematic columns
                continue
        
        # Ensure we have at least some fields
        if not clean_fields:
            clean_fields = [f"column_{i+1}" for i in range(len(df.columns))]
            clean_schema = {f"column_{i+1}": "string" for i in range(len(df.columns))}
        
        # Map old column names to new clean names for preview data
        column_mapping = dict(zip(df.columns, clean_fields))
        clean_preview = []
        for row in preview_rows:
            clean_row = {}
            for old_col, new_col in column_mapping.items():
                clean_row[new_col] = row.get(old_col, "")
            clean_preview.append(clean_row)
        
        return {
            "dataset_id": dataset_id,
            "filename": file.filename,
            "schema": clean_schema,
            "row_count": len(full_rows),
            "preview": clean_preview,
            "fields": clean_fields
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Error processing file: {str(e)}"
        # Log full traceback for debugging
        print(f"File upload error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/api/datasets/{dataset_id}")
async def get_dataset(dataset_id: str):
    """Get dataset by ID."""
    if not hasattr(storage, '_datasets') or dataset_id not in storage._datasets:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    dataset = storage._datasets[dataset_id]
    return {
        "dataset_id": dataset_id,
        "filename": dataset["filename"],
        "schema": dataset["schema"],
        "row_count": dataset["row_count"],
        "fields": list(dataset["schema"].keys())
    }


@app.get("/api/datasets")
async def list_datasets():
    """List all uploaded datasets."""
    if not hasattr(storage, '_datasets'):
        return []
    
    return [
        {
            "dataset_id": dataset_id,
            "filename": data["filename"],
            "row_count": data["row_count"],
            "fields": list(data["schema"].keys())
        }
        for dataset_id, data in storage._datasets.items()
    ]


@app.post("/api/workflows")
async def create_workflow(workflow: Dict[str, Any]):
    """
    Create or update a workflow definition.
    
    Workflow format:
    {
        "workflow_id": "wf_1",
        "name": "Product Filtering",
        "steps": [...]
    }
    """
    workflow_id = workflow.get("workflow_id")
    if not workflow_id:
        import uuid
        workflow_id = f"wf_{uuid.uuid4().hex[:8]}"
        workflow["workflow_id"] = workflow_id
    
    # Save to persistent storage (SQLite)
    storage.save_workflow(workflow_id, workflow)
    
    # Also keep in memory for quick access
    if not hasattr(storage, '_workflows'):
        storage._workflows = {}
    storage._workflows[workflow_id] = workflow
    
    return {
        "success": True,
        "workflow_id": workflow_id,
        "workflow": workflow
    }


@app.get("/api/workflows")
async def list_workflows():
    """List all workflow definitions."""
    # Load from persistent storage
    workflows = storage.list_workflows()
    
    # Also sync to memory cache
    if not hasattr(storage, '_workflows'):
        storage._workflows = {}
    
    for wf_summary in workflows:
        wf_id = wf_summary["workflow_id"]
        if wf_id not in storage._workflows:
            # Load full workflow into memory cache
            full_workflow = storage.get_workflow(wf_id)
            if full_workflow:
                storage._workflows[wf_id] = full_workflow
    
    return workflows


@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow definition by ID."""
    # Try memory cache first
    if hasattr(storage, '_workflows') and workflow_id in storage._workflows:
        return storage._workflows[workflow_id]
    
    # Load from persistent storage
    workflow = storage.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Cache in memory
    if not hasattr(storage, '_workflows'):
        storage._workflows = {}
    storage._workflows[workflow_id] = workflow
    
    return workflow


@app.post("/api/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, data: Dict[str, Any]):
    """
    Execute a workflow on a dataset.
    
    Request body:
    {
        "dataset_id": "dataset_123",
        "execution_name": "My Execution"
    }
    """
    # Get workflow (try memory cache, then persistent storage)
    workflow = None
    if hasattr(storage, '_workflows') and workflow_id in storage._workflows:
        workflow = storage._workflows[workflow_id]
    else:
        workflow = storage.get_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Get dataset
    dataset_id = data.get("dataset_id")
    if not dataset_id:
        raise HTTPException(status_code=400, detail="dataset_id is required")
    
    if not hasattr(storage, '_datasets') or dataset_id not in storage._datasets:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    dataset = storage._datasets[dataset_id]
    rows = dataset["rows"]
    
    # Execute workflow
    execution_name = data.get("execution_name", workflow.get("name", "Workflow Execution"))
    execution_id = workflow_engine.execute_workflow(
        workflow_definition=workflow,
        dataset=rows,
        execution_name=execution_name
    )
    
    return {
        "success": True,
        "execution_id": execution_id,
        "workflow_id": workflow_id,
        "dataset_id": dataset_id,
        "message": "Workflow executed successfully"
    }


if __name__ == '__main__':
    import uvicorn
    print("=" * 60)
    print("Starting X-Ray Dashboard API")
    print("=" * 60)
    print(f"API: http://localhost:8000")
    print(f"API Docs: http://localhost:8000/docs")
    print(f"Rules file: {rules_config.rules_file}")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000)

