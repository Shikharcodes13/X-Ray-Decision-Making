"""
High-level workflow functions for X-Ray library.
Provides convenient functions for common multi-step workflows using RuleConfig.
"""

from typing import Dict, Any, List, Optional
from xray import XRay
from xray.rules import RuleConfig


def apply_filters_with_rules(
    candidates: List[Dict[str, Any]], 
    rules: RuleConfig, 
    step_name: Optional[str] = None,
    reference: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Apply filters using RuleConfig (domain-agnostic).
    
    Args:
        candidates: List of candidate items to filter
        rules: RuleConfig instance with filter rules
        step_name: Optional step name to get filters for
        reference: Optional reference item for relative filters
        
    Returns:
        Dictionary with:
            - evaluations: List of evaluation results
            - qualified_candidates: List of items that passed all filters
            - filters_applied: Dictionary of applied filter definitions
            - total_evaluated: Total number of candidates
            - passed: Number that passed
            - failed: Number that failed
    """
    evaluations = rules.apply_filters(candidates, step_name=step_name)
    
    qualified = [c for c, e in zip(candidates, evaluations) if e['passed']]
    
    # Get filter definitions for display
    filter_rules = rules.get_filters(step_name)
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


def rank_and_select_with_rules(
    evaluations: List[Dict[str, Any]], 
    rules: RuleConfig, 
    step_name: Optional[str] = None,
    reference: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Rank and select using RuleConfig criteria (domain-agnostic).
    Ranks ALL items by: (1) number of filters passed, (2) then by ranking criteria.
    
    Args:
        evaluations: List of evaluation results from filtering step
        rules: RuleConfig instance with ranking criteria
        step_name: Optional step name to get ranking criteria for
        reference: Optional reference item for relative ranking
        
    Returns:
        Dictionary with:
            - ranked_candidates: List of ranked candidates with scores
            - selection: Selected item info
            - selected_item: Full selected item data
            - ranking_criteria: Criteria used for ranking
    """
    if not evaluations:
        return {
            'selected_item': None,
            'reason': 'No candidates to rank',
            'ranked_candidates': [],
            'selection': {},
            'ranking_criteria': {}
        }
    
    ranking_criteria = rules.get_ranking_criteria(step_name)
    
    if not ranking_criteria:
        # Default ranking if no rules defined
        ranking_criteria = {'primary': 'count', 'secondary': 'score'}
    
    primary = ranking_criteria.get('primary', 'count')
    secondary = ranking_criteria.get('secondary')
    tertiary = ranking_criteria.get('tertiary')
    
    ranked = []
    
    for eval_item in evaluations:
        candidate = eval_item.get('metrics', {})
        filters_passed = eval_item.get('filters_passed_count', 0)
        total_filters = eval_item.get('total_filters', 0)
        
        # Get values for ranking (flexible field access - case-insensitive)
        primary_val = _get_field_value_case_insensitive(candidate, primary, 0)
        secondary_val = _get_field_value_case_insensitive(candidate, secondary, 0) if secondary else 0
        tertiary_val = _get_field_value_case_insensitive(candidate, tertiary, 0) if tertiary else 0
        
        # Normalize scores (0-1 scale) - only for items that have the field
        all_candidates = [e.get('metrics', {}) for e in evaluations]
        max_primary = max(_get_field_value_case_insensitive(c, primary, 0) for c in all_candidates) if primary else 1
        primary_score = primary_val / max_primary if max_primary > 0 else 0
        
        max_secondary = max(_get_field_value_case_insensitive(c, secondary, 0) for c in all_candidates) if secondary else 1
        secondary_score = secondary_val / max_secondary if max_secondary > 0 else 0
        
        max_tertiary = max(_get_field_value_case_insensitive(c, tertiary, 0) for c in all_candidates) if tertiary else 1
        tertiary_score = tertiary_val / max_tertiary if max_tertiary > 0 else 0
        
        # Weighted score for ranking criteria
        criteria_score = (
            primary_score * 0.5 +
            secondary_score * 0.3 +
            tertiary_score * 0.2
        )
        
        ranked.append({
            'item_id': eval_item.get('item_id', candidate.get('id', '')),
            'item_name': eval_item.get('item_name', candidate.get('name') or candidate.get('title') or 'Item'),
            'metrics': candidate,
            'filters_passed_count': filters_passed,
            'total_filters': total_filters,
            'filter_results': eval_item.get('filter_results', {}),
            'score_breakdown': {
                f'{primary}_score': round(primary_score, 2),
                f'{secondary}_score': round(secondary_score, 2) if secondary else 0,
                f'{tertiary}_score': round(tertiary_score, 2) if tertiary else 0
            },
            'criteria_score': round(criteria_score, 2),
            'total_score': round(criteria_score, 2)  # Will be used for secondary ranking
        })
    
    # Sort by: (1) filters_passed_count (desc), (2) then by criteria_score (desc)
    # Items that pass all filters are ranked first
    ranked.sort(key=lambda x: (
        x['filters_passed_count'] == x['total_filters'],  # True (1) for all passed, False (0) otherwise
        x['filters_passed_count'],  # Then by number of filters passed
        x['criteria_score']  # Then by criteria score
    ), reverse=True)
    
    # Add rank numbers
    for i, item in enumerate(ranked):
        item['rank'] = i + 1
    
    selected = ranked[0] if ranked else None
    
    if not selected:
        return {
            'ranked_candidates': [],
            'selection': {},
            'selected_item': None,
            'ranking_criteria': ranking_criteria
        }
    
    # Build selection reason
    if selected['filters_passed_count'] == selected['total_filters']:
        reason = f"Passed all {selected['total_filters']} filters"
        if primary:
            reason += f" - best {primary} ({selected['metrics'].get(primary, 'N/A')})"
    else:
        reason = f"Passed {selected['filters_passed_count']}/{selected['total_filters']} filters"
        if primary:
            reason += f" - best {primary} ({selected['metrics'].get(primary, 'N/A')}) among items with {selected['filters_passed_count']} filters passed"
    
    return {
        'ranked_candidates': ranked,
        'selection': {
            'item_id': selected['item_id'],
            'item_name': selected['item_name'],
            'reason': reason
        },
        'selected_item': {
            'id': selected['item_id'],
            'name': selected['item_name'],
            **selected['metrics']
        },
        'ranking_criteria': ranking_criteria
    }


def _get_field_value_case_insensitive(data: Dict[str, Any], field_name: str, default: Any = None) -> Any:
    """Get field value with case-insensitive matching."""
    if not field_name:
        return default
    
    field_lower = field_name.lower()
    for key in data.keys():
        if key.lower() == field_lower:
            return data.get(key, default)
    
    return default

