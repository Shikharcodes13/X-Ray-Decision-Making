"""
Examples of using different rule data sources with automatic reasoning generation.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from xray.rules import RuleConfig
import json


def example_csv_rules():
    """Example: Load rules from CSV file."""
    print("=" * 60)
    print("Example 1: CSV Rules")
    print("=" * 60)
    
    rules = RuleConfig("rules.csv")
    
    print(f"Loaded {len(rules.rules)} rules from CSV")
    print(f"Source type: {rules.source_type}")
    print()
    
    # Show filters
    filters = rules.get_filters("apply_filters")
    print(f"Filters for 'apply_filters': {len(filters)}")
    for f in filters:
        print(f"  - {f.get('name')}: {f.get('field')} {f.get('rule_type')}")
    print()


def example_json_rules():
    """Example: Load rules from JSON file."""
    print("=" * 60)
    print("Example 2: JSON Rules")
    print("=" * 60)
    
    # Create example JSON rules
    json_rules = {
        "rules": [
            {
                "step": "apply_filters",
                "type": "filter",
                "name": "value_range",
                "field": "value",
                "rule_type": "range",
                "min": 25.0,
                "max": 100.0,
                "description": "Value must be between 25-100"
            },
            {
                "step": "apply_filters",
                "type": "filter",
                "name": "min_score",
                "field": "score",
                "rule_type": "min",
                "value": 2.0,
                "description": "Minimum score of 2.0"
            },
            {
                "step": "rank_and_select",
                "type": "ranking",
                "primary": "count",
                "secondary": "score",
                "description": "Rank by count, then score"
            }
        ]
    }
    
    # Save to file for example
    with open("rules_example.json", "w") as f:
        json.dump(json_rules, f, indent=2)
    
    # Load from JSON
    rules = RuleConfig("rules_example.json")
    
    print(f"Loaded {len(rules.rules)} rules from JSON")
    print(f"Source type: {rules.source_type}")
    print()
    
    # Show filters
    filters = rules.get_filters("apply_filters")
    print(f"Filters for 'apply_filters': {len(filters)}")
    for f in filters:
        print(f"  - {f.get('name')}: {f.get('field')} {f.get('rule_type')}")
    print()


def example_dict_rules():
    """Example: Load rules from Python dictionary."""
    print("=" * 60)
    print("Example 3: Dictionary Rules")
    print("=" * 60)
    
    # Define rules as dictionary
    rules_dict = {
        "rules": [
            {
                "step": "apply_filters",
                "type": "filter",
                "name": "category_filter",
                "field": "category",
                "rule_type": "equals",
                "value": "A",
                "description": "Category must be A"
            }
        ]
    }
    
    # Load from dictionary
    rules = RuleConfig(rules_dict)
    
    print(f"Loaded {len(rules.rules)} rules from dictionary")
    print(f"Source type: {rules.source_type}")
    print()
    
    # Show filters
    filters = rules.get_filters("apply_filters")
    print(f"Filters for 'apply_filters': {len(filters)}")
    for f in filters:
        print(f"  - {f.get('name')}: {f.get('field')} {f.get('rule_type')}")
    print()


def example_automatic_reasoning():
    """Example: Automatic reasoning generation."""
    print("=" * 60)
    print("Example 4: Automatic Reasoning Generation")
    print("=" * 60)
    
    rules = RuleConfig("rules.csv")
    
    # Mock items to filter
    items = [
        {"id": "1", "name": "Item A", "price": 30.0, "rating": 4.5, "reviews": 200},
        {"id": "2", "name": "Item B", "price": 10.0, "rating": 3.5, "reviews": 50},
        {"id": "3", "name": "Item C", "price": 50.0, "rating": 4.0, "reviews": 150},
    ]
    
    # Apply filters
    evaluations = rules.apply_filters(items, step_name="apply_filters")
    
    # Generate automatic reasoning
    reasoning = rules.generate_filter_reasoning(evaluations, step_name="apply_filters")
    
    print("Automatic Reasoning Generated:")
    print("-" * 60)
    print(reasoning)
    print()
    
    # Show evaluation results
    print("Evaluation Results:")
    print("-" * 60)
    for eval_result in evaluations:
        status = "✓ PASSED" if eval_result['passed'] else "✗ FAILED"
        print(f"{status}: {eval_result['item_name']}")
        if not eval_result['passed']:
            failed_filters = [
                name for name, result in eval_result['filter_results'].items()
                if not result.get('passed', True)
            ]
            print(f"  Failed filters: {', '.join(failed_filters)}")
    print()


def example_ranking_reasoning():
    """Example: Ranking reasoning generation."""
    print("=" * 60)
    print("Example 5: Ranking Reasoning Generation")
    print("=" * 60)
    
    rules = RuleConfig("rules.csv")
    
    # Mock ranked candidates
    ranked_candidates = [
        {
            "item_id": "1",
            "item_name": "Item A",
            "total_score": 0.95,
            "score_breakdown": {
                "review_count_score": 1.0,
                "rating_score": 0.9,
                "price_proximity_score": 0.85
            },
            "metrics": {"review_count": 1000, "rating": 4.5, "price": 30.0}
        },
        {
            "item_id": "2",
            "item_name": "Item B",
            "total_score": 0.75,
            "score_breakdown": {
                "review_count_score": 0.8,
                "rating_score": 0.7,
                "price_proximity_score": 0.6
            },
            "metrics": {"review_count": 800, "rating": 4.0, "price": 35.0}
        }
    ]
    
    selected_item = {"id": "1", "name": "Item A"}
    
    # Generate automatic reasoning
    reasoning = rules.generate_ranking_reasoning(
        ranked_candidates,
        selected_item,
        step_name="rank_and_select"
    )
    
    print("Automatic Ranking Reasoning:")
    print("-" * 60)
    print(reasoning)
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Rules System Examples")
    print("=" * 60 + "\n")
    
    # Run examples
    try:
        example_csv_rules()
    except Exception as e:
        print(f"Error in CSV example: {e}\n")
    
    try:
        example_json_rules()
    except Exception as e:
        print(f"Error in JSON example: {e}\n")
    
    try:
        example_dict_rules()
    except Exception as e:
        print(f"Error in dictionary example: {e}\n")
    
    try:
        example_automatic_reasoning()
    except Exception as e:
        print(f"Error in reasoning example: {e}\n")
    
    try:
        example_ranking_reasoning()
    except Exception as e:
        print(f"Error in ranking example: {e}\n")
    
    print("=" * 60)
    print("Examples Complete!")
    print("=" * 60)

