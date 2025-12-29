"""
Generic multi-step workflow demo using X-Ray.
This demonstrates a domain-agnostic workflow that uses CSV-based rules.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from xray import XRay, SQLiteStorage
from xray.rules import RuleConfig
import random
import json


def step1_generate_candidates(input_data: dict) -> list:
    """
    Step 1: Generate candidates (domain-agnostic).
    In a real system, this could be an API call, database query, etc.
    """
    # This is just mock data - in reality, this would come from your system
    # The structure is flexible - any dict/list structure works
    candidates = input_data.get('candidates', [])
    
    # If no candidates provided, generate some mock ones
    if not candidates:
        num_candidates = input_data.get('num_candidates', 10)
        candidates = [
            {
                'id': f'item_{i}',
                'name': f'Item {i}',
                'value': random.uniform(10, 100),
                'score': random.uniform(1, 5),
                'count': random.randint(10, 10000),
                'category': random.choice(['A', 'B', 'C'])
            }
            for i in range(num_candidates)
        ]
    
    return candidates


def step2_apply_filters(candidates: list, rules: RuleConfig, reference: dict = None) -> dict:
    """
    Step 2: Apply filters using CSV-based rules (domain-agnostic).
    """
    evaluations = rules.apply_filters(candidates, step_name='apply_filters')
    
    qualified = [c for c, e in zip(candidates, evaluations) if e['passed']]
    
    # Get filter definitions for display
    filter_rules = rules.get_filters('apply_filters')
    filters_applied = {}
    for rule in filter_rules:
        filters_applied[rule.get('name', 'unnamed')] = {
            'field': rule.get('field'),
            'rule_type': rule.get('rule_type'),
            'value': rule.get('value'),
            'min': rule.get('min'),
            'max': rule.get('max'),
            'description': rule.get('description', '')
        }
    
    return {
        'evaluations': evaluations,
        'qualified_candidates': qualified,
        'filters_applied': filters_applied,
        'total_evaluated': len(candidates),
        'passed': len(qualified),
        'failed': len(candidates) - len(qualified)
    }


def step3_rank_and_select(candidates: list, rules: RuleConfig, reference: dict = None) -> dict:
    """
    Step 3: Rank and select using CSV-based criteria (domain-agnostic).
    """
    if not candidates:
        return {
            'selected_item': None,
            'reason': 'No qualified candidates'
        }
    
    ranking_criteria = rules.get_ranking_criteria('rank_and_select')
    
    if not ranking_criteria:
        # Default ranking if no rules defined
        ranking_criteria = {'primary': 'count', 'secondary': 'score'}
    
    primary = ranking_criteria.get('primary', 'count')
    secondary = ranking_criteria.get('secondary')
    tertiary = ranking_criteria.get('tertiary')
    
    ranked = []
    
    for candidate in candidates:
        # Get values for ranking (flexible field access)
        primary_val = candidate.get(primary, 0)
        secondary_val = candidate.get(secondary, 0) if secondary else 0
        tertiary_val = candidate.get(tertiary, 0) if tertiary else 0
        
        # Normalize scores (0-1 scale)
        max_primary = max(c.get(primary, 0) for c in candidates) if primary else 1
        primary_score = primary_val / max_primary if max_primary > 0 else 0
        
        max_secondary = max(c.get(secondary, 0) for c in candidates) if secondary else 1
        secondary_score = secondary_val / max_secondary if max_secondary > 0 else 0
        
        max_tertiary = max(c.get(tertiary, 0) for c in candidates) if tertiary else 1
        tertiary_score = tertiary_val / max_tertiary if max_tertiary > 0 else 0
        
        # Weighted score
        total_score = (
            primary_score * 0.5 +
            secondary_score * 0.3 +
            tertiary_score * 0.2
        )
        
        ranked.append({
            'item_id': candidate.get('id', str(candidates.index(candidate))),
            'item_name': candidate.get('name') or candidate.get('title') or 'Item',
            'metrics': candidate,
            'score_breakdown': {
                f'{primary}_score': round(primary_score, 2),
                f'{secondary}_score': round(secondary_score, 2) if secondary else 0,
                f'{tertiary}_score': round(tertiary_score, 2) if tertiary else 0
            },
            'total_score': round(total_score, 2)
        })
    
    # Sort by total score
    ranked.sort(key=lambda x: x['total_score'], reverse=True)
    
    # Add rank numbers
    for i, item in enumerate(ranked):
        item['rank'] = i + 1
    
    selected = ranked[0]
    
    return {
        'ranked_candidates': ranked,
        'selection': {
            'item_id': selected['item_id'],
            'item_name': selected['item_name'],
            'reason': f"Highest overall score ({selected['total_score']}) - best {primary} ({selected['metrics'].get(primary, 'N/A')})"
        },
        'selected_item': {
            'id': selected['item_id'],
            'name': selected['item_name'],
            **selected['metrics']
        },
        'ranking_criteria': ranking_criteria
    }


def run_generic_workflow(input_data: dict, rules_file: str = "rules.csv"):
    """
    Run a generic multi-step workflow using X-Ray.
    
    Args:
        input_data: Input data for the workflow (domain-agnostic)
        rules_file: Path to CSV file with rules
    """
    storage = SQLiteStorage()
    rules = RuleConfig(rules_file=rules_file)
    
    with XRay(storage=storage, name="generic_multi_step") as xray:
        xray.add_metadata("workflow", "generic_multi_step")
        xray.add_metadata("input_data", input_data)
        xray.add_metadata("rules_file", rules_file)
        
        # Step 1: Generate candidates
        candidates = step1_generate_candidates(input_data)
        
        xray.record_step(
            step_name="generate_candidates",
            step_type="transformation",
            input_data=input_data,
            output_data={
                "candidates_count": len(candidates),
                "candidates": candidates[:5]  # Show first 5
            },
            reasoning=f"Generated {len(candidates)} candidate items"
        )
        
        # Step 2: Apply filters
        filter_result = step2_apply_filters(candidates, rules, input_data.get('reference'))
        
        # Convert evaluations to canonical format
        canonical_evaluations = []
        for eval_item in filter_result["evaluations"]:
            # Convert filter_results to checks format
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
        
        # Generate automatic reasoning based on rules
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
        
        # Generate automatic reasoning based on rules
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
        
        return {
            "execution_id": xray.execution_id,
            "selected_item": ranking_result["selected_item"]
        }


if __name__ == "__main__":
    # Example: Generic workflow with any data structure
    input_data = {
        "num_candidates": 15,
        "reference": {
            "value": 50.0  # Reference value for range calculations
        }
    }
    
    print("Running Generic Multi-Step Workflow...")
    print(f"Input: {json.dumps(input_data, indent=2)}")
    print()
    
    result = run_generic_workflow(input_data, rules_file="rules.csv")
    
    print(f"[SUCCESS] Execution ID: {result['execution_id']}")
    print(f"[SUCCESS] Selected Item: {result['selected_item']['name']}")
    print(f"   ID: {result['selected_item']['id']}")
    print(f"   Value: {result['selected_item'].get('value', 'N/A')}")
    print(f"   Score: {result['selected_item'].get('score', 'N/A')}")
    print()
    print(f"[INFO] View in dashboard: http://localhost:5000/execution/{result['execution_id']}")

