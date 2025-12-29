"""
Generic Workflow Execution Engine
Executes user-defined workflows on any dataset without hardcoded logic.
"""

from typing import Dict, Any, List, Optional
from xray import XRay
from xray.storage_sqlite import SQLiteStorage


class GenericWorkflowEngine:
    """
    Generic workflow execution engine that works with any data structure.
    No hardcoded business logic - everything is data-driven.
    """
    
    def __init__(self, storage=None):
        self.storage = storage or SQLiteStorage()
    
    def execute_workflow(
        self,
        workflow_definition: Dict[str, Any],
        dataset: List[Dict[str, Any]],
        execution_name: Optional[str] = None
    ) -> str:
        """
        Execute a user-defined workflow on a dataset.
        
        Args:
            workflow_definition: Workflow definition with steps and rules
            dataset: List of data rows (each row is a dict)
            execution_name: Optional name for this execution
            
        Returns:
            execution_id: ID of the created execution
            
        Workflow Definition Format:
        {
            "workflow_id": "wf_1",
            "name": "Product Filtering",
            "steps": [
                {
                    "id": "step_1",
                    "type": "filter",
                    "label": "Filter by Rating",
                    "input_fields": ["rating"],
                    "rule": {
                        "operator": ">=",
                        "value": 4
                    }
                },
                {
                    "id": "step_2",
                    "type": "filter",
                    "label": "Filter by Price",
                    "input_fields": ["price"],
                    "rule": {
                        "operator": "<=",
                        "value": 50
                    }
                },
                {
                    "id": "step_3",
                    "type": "ranking",
                    "label": "Rank by Score",
                    "input_fields": ["score"],
                    "rule": {
                        "order": "desc"
                    }
                }
            ]
        }
        """
        workflow_id = workflow_definition.get("workflow_id", "generic_workflow")
        workflow_name = workflow_definition.get("name", "Generic Workflow")
        steps = workflow_definition.get("steps", [])
        
        with XRay(storage=self.storage, name=execution_name or workflow_name) as xray:
            xray.add_metadata("workflow_id", workflow_id)
            xray.add_metadata("workflow_name", workflow_name)
            xray.add_metadata("dataset_size", len(dataset))
            xray.add_metadata("workflow_definition", workflow_definition)
            
            # Track data through pipeline
            current_data = dataset.copy()
            
            for step_def in steps:
                step_id = step_def.get("id", f"step_{len(xray.steps) + 1}")
                step_type = step_def.get("type", "filter")
                step_label = step_def.get("label", step_id)
                input_fields = step_def.get("input_fields", [])
                rule = step_def.get("rule", {})
                
                # Execute step based on type
                if step_type == "filter":
                    result = self._execute_filter_step(
                        step_id=step_id,
                        step_label=step_label,
                        data=current_data,
                        input_fields=input_fields,
                        rule=rule
                    )
                elif step_type == "ranking":
                    result = self._execute_ranking_step(
                        step_id=step_id,
                        step_label=step_label,
                        data=current_data,
                        input_fields=input_fields,
                        rule=rule
                    )
                elif step_type == "transformation":
                    result = self._execute_transformation_step(
                        step_id=step_id,
                        step_label=step_label,
                        data=current_data,
                        input_fields=input_fields,
                        rule=rule
                    )
                else:
                    # Unknown step type - pass through
                    result = {
                        "data": current_data,
                        "evaluations": [],
                        "output": {"message": f"Unknown step type: {step_type}"}
                    }
                
                # Record step in X-Ray
                evaluations = result.get("evaluations", [])
                output_data = result.get("output", {})
                reasoning = result.get("reasoning", f"Executed {step_label}")
                
                # Convert rule to canonical format
                canonical_rules = [{
                    "name": step_label,
                    "type": step_type,
                    "value": rule,
                    "source": "workflow_definition"
                }]
                
                xray.record_step(
                    step_name=step_id,
                    step_type=step_type,
                    input_data={
                        "input_count": len(current_data),
                        "input_fields": input_fields,
                        "rule": rule
                    },
                    rules=canonical_rules,
                    evaluations=evaluations,
                    output_data=output_data,
                    reasoning=reasoning
                )
                
                # Update current data for next step
                current_data = result.get("data", current_data)
            
            return xray.execution_id
    
    def _execute_filter_step(
        self,
        step_id: str,
        step_label: str,
        data: List[Dict[str, Any]],
        input_fields: List[str],
        rule: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a filter step."""
        operator = rule.get("operator", "==")
        value = rule.get("value")
        
        passed = []
        failed = []
        evaluations = []
        
        for row in data:
            # Get entity ID (use first field or generate)
            entity_id = row.get("id") or row.get("_id") or str(hash(str(row)))
            
            # Evaluate rule on input fields
            field_values = {}
            all_passed = True
            checks = []
            
            for field in input_fields:
                # Case-insensitive field matching
                field_lower = field.lower()
                matched_field = None
                for key in row.keys():
                    if key.lower() == field_lower:
                        matched_field = key
                        break
                
                if not matched_field:
                    all_passed = False
                    checks.append({
                        "rule": f"{field} {operator} {value}",
                        "passed": False,
                        "expected": f"{field} should be {operator} {value}",
                        "actual": f"Field '{field}' not found",
                        "reason": f"Field '{field}' does not exist in row"
                    })
                    continue
                
                field_value = row[matched_field]
                field_values[field] = field_value
                
                # Evaluate condition
                passed_check = self._evaluate_condition(field_value, operator, value)
                
                checks.append({
                    "rule": f"{field} {operator} {value}",
                    "passed": passed_check,
                    "expected": f"{field} should be {operator} {value}",
                    "actual": str(field_value),
                    "reason": "Passed" if passed_check else f"Value {field_value} does not satisfy {operator} {value}"
                })
                
                if not passed_check:
                    all_passed = False
            
            # Create evaluation
            evaluation = {
                "entity_id": entity_id,
                "attributes": {k: v for k, v in row.items() if k not in ["id", "_id"]},
                "checks": checks,
                "final_decision": "accepted" if all_passed else "rejected"
            }
            evaluations.append(evaluation)
            
            if all_passed:
                passed.append(row)
            else:
                failed.append(row)
        
        reasoning = f"{step_label}: {len(passed)} passed, {len(failed)} failed out of {len(data)} total"
        
        return {
            "data": passed,
            "evaluations": evaluations,
            "output": {
                "total": len(data),
                "passed": len(passed),
                "failed": len(failed)
            },
            "reasoning": reasoning
        }
    
    def _execute_ranking_step(
        self,
        step_id: str,
        step_label: str,
        data: List[Dict[str, Any]],
        input_fields: List[str],
        rule: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a ranking step."""
        order = rule.get("order", "desc")  # "asc" or "desc"
        limit = rule.get("limit")  # Optional limit
        
        if not input_fields:
            # No fields specified - return as is
            return {
                "data": data,
                "evaluations": [],
                "output": {"message": "No ranking fields specified"},
                "reasoning": f"{step_label}: No ranking performed (no fields specified)"
            }
        
        # Sort by first field (primary), then by subsequent fields
        def sort_key(row):
            values = []
            for field in input_fields:
                # Case-insensitive field matching
                field_lower = field.lower()
                matched_field = None
                for key in row.keys():
                    if key.lower() == field_lower:
                        matched_field = key
                        break
                
                val = row.get(matched_field) if matched_field else None
                if val is None:
                    val = float('-inf') if order == "desc" else float('inf')
                values.append(val)
            return tuple(values)
        
        sorted_data = sorted(data, key=sort_key, reverse=(order == "desc"))
        
        if limit:
            sorted_data = sorted_data[:limit]
        
        # Create evaluations with rankings
        evaluations = []
        for rank, row in enumerate(sorted_data, 1):
            entity_id = row.get("id") or row.get("_id") or str(hash(str(row)))
            
            # Calculate score based on ranking fields (case-insensitive)
            score = 0
            for field in input_fields:
                field_lower = field.lower()
                matched_field = None
                for key in row.keys():
                    if key.lower() == field_lower:
                        matched_field = key
                        break
                if matched_field and isinstance(row.get(matched_field), (int, float)):
                    score += row.get(matched_field, 0)
            
            evaluations.append({
                "entity_id": entity_id,
                "attributes": {k: v for k, v in row.items() if k not in ["id", "_id"]},
                "checks": [{
                    "rule": f"Rank by {', '.join(input_fields)} ({order})",
                    "passed": True,
                    "expected": f"Rank {rank}",
                    "actual": f"Rank {rank} with score {score}",
                    "reason": f"Ranked {rank} based on {', '.join(input_fields)}"
                }],
                "final_decision": "selected" if rank == 1 else "not_selected"
            })
        
        reasoning = f"{step_label}: Ranked {len(sorted_data)} items by {', '.join(input_fields)} ({order})"
        
        return {
            "data": sorted_data,
            "evaluations": evaluations,
            "output": {
                "total_ranked": len(sorted_data),
                "ranking_fields": input_fields,
                "order": order
            },
            "reasoning": reasoning
        }
    
    def _execute_transformation_step(
        self,
        step_id: str,
        step_label: str,
        data: List[Dict[str, Any]],
        input_fields: List[str],
        rule: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a transformation step (pass-through for now)."""
        # Transformations can be extended later
        return {
            "data": data,
            "evaluations": [],
            "output": {"message": "Transformation step executed"},
            "reasoning": f"{step_label}: Processed {len(data)} items"
        }
    
    def _evaluate_condition(self, value: Any, operator: str, expected: Any) -> bool:
        """Evaluate a condition with proper type handling."""
        try:
            # Convert both to strings for comparison if either is a string
            value_str = str(value).strip() if isinstance(value, str) else value
            expected_str = str(expected).strip() if isinstance(expected, str) else expected
            
            # Determine if we're comparing strings
            is_string_comparison = isinstance(value, str) or isinstance(expected, str)
            
            if operator == "==":
                if is_string_comparison:
                    # Case-insensitive string equality
                    return str(value_str).lower() == str(expected_str).lower()
                return value == expected
            elif operator == "!=":
                if is_string_comparison:
                    return str(value_str).lower() != str(expected_str).lower()
                return value != expected
            elif operator == "contains":
                # String contains (case-insensitive)
                return str(expected_str).lower() in str(value_str).lower()
            elif operator == "not_contains":
                # String does not contain (case-insensitive)
                return str(expected_str).lower() not in str(value_str).lower()
            elif operator == "starts_with":
                # String starts with (case-insensitive)
                return str(value_str).lower().startswith(str(expected_str).lower())
            elif operator == "ends_with":
                # String ends with (case-insensitive)
                return str(value_str).lower().endswith(str(expected_str).lower())
            elif operator == "in":
                # Value in list
                if isinstance(expected, (list, tuple)):
                    if is_string_comparison:
                        return str(value_str).lower() in [str(e).lower() for e in expected]
                    return value in expected
                return False
            elif operator == "not_in":
                # Value not in list
                if isinstance(expected, (list, tuple)):
                    if is_string_comparison:
                        return str(value_str).lower() not in [str(e).lower() for e in expected]
                    return value not in expected
                return True
            elif operator == ">":
                # Numeric comparison only
                if is_string_comparison:
                    # For strings, use case-insensitive lexicographic comparison
                    return str(value_str).lower() > str(expected_str).lower()
                return value > expected
            elif operator == ">=":
                # Numeric comparison only
                if is_string_comparison:
                    # For strings, use case-insensitive lexicographic comparison
                    return str(value_str).lower() >= str(expected_str).lower()
                return value >= expected
            elif operator == "<":
                if is_string_comparison:
                    # For strings, use case-insensitive lexicographic comparison
                    return str(value_str).lower() < str(expected_str).lower()
                return value < expected
            elif operator == "<=":
                if is_string_comparison:
                    # For strings, use case-insensitive lexicographic comparison
                    return str(value_str).lower() <= str(expected_str).lower()
                return value <= expected
            else:
                return False
        except (TypeError, ValueError):
            return False

