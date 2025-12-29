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
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from xray.storage_sqlite import SQLiteStorage
from xray.rules import RuleConfig
from xray import XRay
from xray.workflow_engine import GenericWorkflowEngine
from demo.generic_workflow import step1_generate_candidates, step2_apply_filters, step3_rank_and_select

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
        
        # Run workflow with custom function that accepts rules directly
        execution_id = run_workflow_with_rules(input_data, rules)
        
        return {
            'success': True,
            'execution_id': execution_id,
            'message': 'Workflow executed successfully'
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_workflow_with_rules(input_data: dict, rules: RuleConfig):
    """Run workflow with provided rules config."""
    with XRay(storage=storage, name="generic_multi_step") as xray:
        xray.add_metadata("workflow", "generic_multi_step")
        xray.add_metadata("input_data", input_data)
        xray.add_metadata("rules_source", "frontend_input")
        
        # Step 1: Generate candidates
        candidates = step1_generate_candidates(input_data)
        
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
        
        # Step 2: Apply filters
        filter_result = step2_apply_filters(candidates, rules, input_data.get('reference'))
        
        # Convert evaluations to canonical format
        canonical_evaluations = []
        for eval_item in filter_result["evaluations"]:
            checks = []
            for rule_name, result in eval_item.get("filter_results", {}).items():
                checks.append({
                    "rule": rule_name,
                    "passed": result.get("passed", False),
                    "expected": result.get("expected", ""),
                    "actual": result.get("actual", ""),
                    "reason": result.get("detail", result.get("reason", ""))
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
        
        # Step 3: Rank and select
        ranking_result = step3_rank_and_select(
            filter_result["qualified_candidates"], 
            rules, 
            input_data.get('reference')
        )
        
        # Convert ranked candidates to canonical evaluations format
        canonical_ranked_evaluations = []
        for candidate in ranking_result["ranked_candidates"]:
            canonical_ranked_evaluations.append({
                "entity_id": candidate.get("item_id", ""),
                "attributes": candidate.get("metrics", {}),
                "checks": [
                    {
                        "rule": "ranking_score",
                        "passed": True,
                        "expected": "Higher is better",
                        "actual": candidate.get("total_score", 0),
                        "reason": f"Rank {candidate.get('rank', 'N/A')} with score {candidate.get('total_score', 0)}"
                    }
                ],
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
        
        # Parse based on file type
        df = None
        if file_extension == 'csv':
            df = pd.read_csv(io.BytesIO(contents))
        elif file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(io.BytesIO(contents))
        elif file_extension == 'json':
            df = pd.read_json(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")
        
        # Detect schema
        schema = {}
        for col in df.columns:
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
        
        # Convert to list of dicts
        rows = df.fillna("").to_dict('records')
        
        # Generate dataset ID
        import hashlib
        dataset_id = hashlib.md5(file.filename.encode() + str(len(rows)).encode()).hexdigest()[:8]
        
        # Store dataset (in-memory for now, can be extended to use storage)
        if not hasattr(storage, '_datasets'):
            storage._datasets = {}
        storage._datasets[dataset_id] = {
            "dataset_id": dataset_id,
            "filename": file.filename,
            "schema": schema,
            "rows": rows,
            "row_count": len(rows)
        }
        
        # Return preview (first 10 rows)
        preview = rows[:10]
        
        return {
            "dataset_id": dataset_id,
            "filename": file.filename,
            "schema": schema,
            "row_count": len(rows),
            "preview": preview,
            "fields": list(schema.keys())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


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

