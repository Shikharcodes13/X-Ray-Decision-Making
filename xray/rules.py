"""
Rule configuration system for X-Ray.
Supports multiple data sources: CSV files, JSON files, and Google Sheets.
Rules define filters, ranking criteria, and other decision logic.
"""

import csv
import json
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from urllib.parse import urlparse


class RuleConfig:
    """
    Loads and manages rules from multiple data sources.
    Supports CSV files, JSON files, and Google Sheets.
    Rules define filters, ranking criteria, and other decision logic.
    """
    
    def __init__(self, rules_source: Optional[Union[str, Dict, List]] = None):
        """
        Initialize rule configuration.
        
        Args:
            rules_source: Can be:
                - Path to CSV file (e.g., "rules.csv")
                - Path to JSON file (e.g., "rules.json")
                - Google Sheets URL or ID (requires gspread)
                - Dictionary with rules data
                - List of rule dictionaries
                - None: uses default "rules.csv"
        """
        self.rules_source = rules_source or "rules.csv"
        self.rules: List[Dict[str, Any]] = []
        self.source_type = None
        self.load_rules()
    
    def _detect_source_type(self, source: Union[str, Dict, List]) -> str:
        """Detect the type of rules source."""
        if isinstance(source, dict):
            return 'dict'
        elif isinstance(source, list):
            return 'list'
        elif isinstance(source, str):
            source_lower = source.lower()
            if source_lower.endswith('.json'):
                return 'json'
            elif source_lower.endswith('.csv'):
                return 'csv'
            elif 'docs.google.com' in source_lower or 'drive.google.com' in source_lower:
                return 'google_sheets'
            elif len(source) > 10 and '/' not in source and '\\' not in source:
                # Might be a Google Sheets ID
                return 'google_sheets_id'
            else:
                # Default to CSV
                return 'csv'
        return 'csv'
    
    def _load_from_csv(self, file_path: str):
        """Load rules from CSV file."""
        rules_path = Path(file_path)
        
        if not rules_path.exists():
            print(f"Warning: Rules file not found: {file_path}")
            self.rules = []
            return
        
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.rules = list(reader)
            self._normalize_rules()
        except Exception as e:
            print(f"Warning: Could not load rules from {file_path}: {e}")
            self.rules = []
    
    def _load_from_json(self, file_path: str):
        """Load rules from JSON file."""
        rules_path = Path(file_path)
        
        if not rules_path.exists():
            print(f"Warning: Rules file not found: {file_path}")
            self.rules = []
            return
        
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different JSON structures
            if isinstance(data, list):
                self.rules = data
            elif isinstance(data, dict) and 'rules' in data:
                self.rules = data['rules']
            else:
                self.rules = []
            
            self._normalize_rules()
        except Exception as e:
            print(f"Warning: Could not load rules from {file_path}: {e}")
            self.rules = []
    
    def _load_from_google_sheets(self, source: str):
        """Load rules from Google Sheets."""
        try:
            import gspread
            from google.oauth2.service_account import Credentials
        except ImportError:
            print("Warning: gspread and google-auth not installed. Install with: pip install gspread google-auth")
            print("Falling back to CSV if available...")
            # Try to fall back to CSV
            csv_path = source.replace('.csv', '') + '.csv' if not source.endswith('.csv') else source
            if Path(csv_path).exists():
                self._load_from_csv(csv_path)
            else:
                self.rules = []
            return
        
        try:
            # Extract sheet ID from URL or use as-is
            sheet_id = self._extract_sheet_id(source)
            
            # Try to authenticate (user needs to set up credentials)
            # For now, we'll provide instructions
            print("Warning: Google Sheets integration requires authentication setup.")
            print("Please export your Google Sheet as CSV and use that instead, or set up OAuth2 credentials.")
            self.rules = []
        except Exception as e:
            print(f"Warning: Could not load rules from Google Sheets: {e}")
            self.rules = []
    
    def _extract_sheet_id(self, source: str) -> str:
        """Extract Google Sheets ID from URL or return as-is."""
        if 'docs.google.com' in source or 'drive.google.com' in source:
            # Extract ID from URL
            parts = source.split('/')
            for part in parts:
                if len(part) > 20 and part not in ['spreadsheets', 'd', 'edit']:
                    return part
        return source
    
    def _load_from_dict(self, data: Dict):
        """Load rules from dictionary."""
        if 'rules' in data:
            self.rules = data['rules']
        else:
            # Assume the dict itself is a single rule, or convert to list
            self.rules = [data] if data else []
        self._normalize_rules()
    
    def _load_from_list(self, data: List):
        """Load rules from list."""
        self.rules = data
        self._normalize_rules()
    
    def _normalize_rules(self):
        """Convert string values to appropriate types in rules."""
        for rule in self.rules:
            if 'value' in rule and rule['value']:
                try:
                    if isinstance(rule['value'], str) and '.' in rule['value']:
                        rule['value'] = float(rule['value'])
                    elif isinstance(rule['value'], str):
                        try:
                            rule['value'] = int(rule['value'])
                        except ValueError:
                            pass  # Keep as string
                except (ValueError, TypeError):
                    pass
            
            if 'min' in rule and rule['min']:
                try:
                    if isinstance(rule['min'], str):
                        rule['min'] = float(rule['min'])
                except (ValueError, TypeError):
                    pass
            
            if 'max' in rule and rule['max']:
                try:
                    if isinstance(rule['max'], str):
                        rule['max'] = float(rule['max'])
                except (ValueError, TypeError):
                    pass
    
    def load_rules(self):
        """Load rules from the configured source."""
        self.source_type = self._detect_source_type(self.rules_source)
        
        if self.source_type == 'csv':
            self._load_from_csv(self.rules_source)
        elif self.source_type == 'json':
            self._load_from_json(self.rules_source)
        elif self.source_type == 'google_sheets' or self.source_type == 'google_sheets_id':
            self._load_from_google_sheets(self.rules_source)
        elif self.source_type == 'dict':
            self._load_from_dict(self.rules_source)
        elif self.source_type == 'list':
            self._load_from_list(self.rules_source)
        else:
            self.rules = []
    
    def get_filters(self, step_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get filter rules.
        
        Args:
            step_name: Optional step name to filter by
        
        Returns:
            List of filter rule dictionaries
        """
        filters = [r for r in self.rules if r.get('type', '').lower() == 'filter']
        
        if step_name:
            filters = [f for f in filters if f.get('step', '').lower() == step_name.lower()]
        
        return filters
    
    def get_ranking_criteria(self, step_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get ranking criteria.
        
        Args:
            step_name: Optional step name to filter by
        
        Returns:
            Ranking criteria dictionary or None
        """
        rankings = [r for r in self.rules if r.get('type', '').lower() == 'ranking']
        
        if step_name:
            rankings = [r for r in rankings if r.get('step', '').lower() == step_name.lower()]
        
        if rankings:
            ranking = rankings[0]  # Use first ranking rule
            return {
                'primary': ranking.get('primary', ''),
                'secondary': ranking.get('secondary', ''),
                'tertiary': ranking.get('tertiary', '')
            }
        
        return None
    
    def apply_filter(self, item: Dict[str, Any], filter_rule: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply a single filter rule to an item.
        
        Args:
            item: Item to filter
            filter_rule: Filter rule definition
        
        Returns:
            Dictionary with 'passed' (bool) and 'detail' (str) keys
        """
        field = filter_rule.get('field', '')
        rule_type = filter_rule.get('rule_type', '').lower()
        value = filter_rule.get('value')
        min_val = filter_rule.get('min')
        max_val = filter_rule.get('max')
        
        # Case-insensitive field matching
        if not field:
            return {
                'passed': False,
                'detail': f'Field "{field}" not found in item'
            }
        
        # Find field with case-insensitive matching
        field_lower = field.lower()
        matched_field = None
        for key in item.keys():
            if key.lower() == field_lower:
                matched_field = key
                break
        
        if not matched_field:
            return {
                'passed': False,
                'detail': f'Field "{field}" not found in item'
            }
        
        item_value = item[matched_field]
        
        if rule_type == 'range':
            if min_val is not None and max_val is not None:
                passed = min_val <= item_value <= max_val
                detail = f'{item_value} is {"within" if passed else "outside"} range {min_val}-{max_val}'
                return {'passed': passed, 'detail': detail}
        
        elif rule_type == 'min':
            if value is not None:
                # Case-insensitive string comparison for strings
                if isinstance(item_value, str) or isinstance(value, str):
                    passed = str(item_value).lower() >= str(value).lower()
                else:
                    passed = item_value >= value
                detail = f'{item_value} {"≥" if passed else "<"} {value}'
                return {'passed': passed, 'detail': detail}
        
        elif rule_type == 'max':
            if value is not None:
                # Case-insensitive string comparison for strings
                if isinstance(item_value, str) or isinstance(value, str):
                    passed = str(item_value).lower() <= str(value).lower()
                else:
                    passed = item_value <= value
                detail = f'{item_value} {"≤" if passed else ">"} {value}'
                return {'passed': passed, 'detail': detail}
        
        elif rule_type == 'equals':
            if value is not None:
                # Case-insensitive string comparison
                if isinstance(item_value, str) or isinstance(value, str):
                    passed = str(item_value).lower() == str(value).lower()
                else:
                    passed = item_value == value
                detail = f'{item_value} {"==" if passed else "!="} {value}'
                return {'passed': passed, 'detail': detail}
        
        elif rule_type == 'contains':
            if value is not None:
                passed = str(value).lower() in str(item_value).lower()
                detail = f'"{value}" {"found in" if passed else "not found in"} "{item_value}"'
                return {'passed': passed, 'detail': detail}
        
        # Default: pass if rule type not recognized
        return {
            'passed': True,
            'detail': f'Unknown rule type: {rule_type}'
        }
    
    def apply_filters(self, items: List[Dict[str, Any]], step_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Apply all filter rules to a list of items.
        
        Args:
            items: List of items to filter
            step_name: Optional step name to get filters for
        
        Returns:
            List of evaluation results with filter results for each item
        """
        filter_rules = self.get_filters(step_name)
        
        if not filter_rules:
            # No filters defined - all items pass
            return [
                {
                    'item_id': str(i),
                    'item_name': item.get('name') or item.get('title') or str(i),
                    'passed': True,
                    'filter_results': {},
                    'metrics': item
                }
                for i, item in enumerate(items)
            ]
        
        evaluations = []
        
        for item in items:
            item_id = item.get('id') or item.get('asin') or str(items.index(item))
            item_name = item.get('name') or item.get('title') or item_id
            
            filter_results = {}
            all_passed = True
            filters_passed_count = 0
            
            for filter_rule in filter_rules:
                filter_name = filter_rule.get('name', 'unnamed_filter')
                field = filter_rule.get('field', '')
                rule_type = filter_rule.get('rule_type', '')
                value = filter_rule.get('value')
                min_val = filter_rule.get('min')
                max_val = filter_rule.get('max')
                
                result = self.apply_filter(item, filter_rule)
                
                # Get actual item value for the field
                field_lower = field.lower()
                matched_field = None
                item_value = None
                for key in item.keys():
                    if key.lower() == field_lower:
                        matched_field = key
                        item_value = item[key]
                        break
                
                # Enhance result with field and value information
                result['field'] = field
                result['field_value'] = item_value
                result['rule_type'] = rule_type
                if rule_type == 'range':
                    result['expected'] = f"{field} in [{min_val}-{max_val}]"
                elif rule_type == 'min':
                    result['expected'] = f"{field} >= {value}"
                elif rule_type == 'max':
                    result['expected'] = f"{field} <= {value}"
                elif rule_type == 'equals':
                    result['expected'] = f"{field} == {value}"
                elif rule_type == 'contains':
                    result['expected'] = f"{field} contains '{value}'"
                else:
                    result['expected'] = f"{field} {rule_type} {value if value is not None else ''}"
                
                result['actual'] = f"{field} = {item_value}" if item_value is not None else f"{field} = N/A"
                
                filter_results[filter_name] = result
                
                if result['passed']:
                    filters_passed_count += 1
                else:
                    all_passed = False
            
            evaluations.append({
                'item_id': item_id,
                'item_name': item_name,
                'passed': all_passed,
                'filters_passed_count': filters_passed_count,
                'total_filters': len(filter_rules),
                'filter_results': filter_results,
                'metrics': item
            })
        
        return evaluations
    
    def generate_filter_reasoning(
        self, 
        evaluations: List[Dict[str, Any]], 
        step_name: Optional[str] = None
    ) -> str:
        """
        Generate automatic reasoning explanation for filter application.
        
        Args:
            evaluations: List of evaluation results from apply_filters()
            step_name: Optional step name for context
        
        Returns:
            Human-readable reasoning string
        """
        filter_rules = self.get_filters(step_name)
        
        if not filter_rules:
            return f"No filters defined for step '{step_name or 'default'}'. All {len(evaluations)} items passed."
        
        total = len(evaluations)
        passed = sum(1 for e in evaluations if e.get('passed', False))
        failed = total - passed
        
        # Build description of filters applied
        filter_descriptions = []
        for rule in filter_rules:
            rule_name = rule.get('name', 'unnamed')
            field = rule.get('field', '')
            rule_type = rule.get('rule_type', '')
            description = rule.get('description', '')
            
            # Build filter description
            filter_desc = f"{rule_name} ({field}"
            if rule_type == 'range':
                min_val = rule.get('min')
                max_val = rule.get('max')
                if min_val is not None and max_val is not None:
                    filter_desc += f": {min_val}-{max_val}"
            elif rule_type == 'min':
                value = rule.get('value')
                if value is not None:
                    filter_desc += f": ≥{value}"
            elif rule_type == 'max':
                value = rule.get('value')
                if value is not None:
                    filter_desc += f": ≤{value}"
            elif rule_type == 'equals':
                value = rule.get('value')
                if value is not None:
                    filter_desc += f": =={value}"
            elif rule_type == 'contains':
                value = rule.get('value')
                if value is not None:
                    filter_desc += f": contains '{value}'"
            
            filter_desc += ")"
            if description:
                filter_desc += f" - {description}"
            
            filter_descriptions.append(filter_desc)
        
        # Build main reasoning summary at the top
        reasoning_parts = []
        
        # Main summary: Why items were chosen
        filter_names = [rule.get('name', 'unnamed') for rule in filter_rules]
        filter_names_str = ", ".join(filter_names)
        
        if passed > 0:
            # Get items that passed all filters
            all_passed_items = [e for e in evaluations if e.get('passed', False)]
            if all_passed_items:
                # Get top item metrics for context
                top_item = all_passed_items[0]
                metrics = top_item.get('metrics', {})
                metric_strs = []
                for key in ['price', 'rating', 'reviews', 'value', 'score', 'count']:
                    if key in metrics:
                        if key == 'price':
                            metric_strs.append(f"${metrics[key]:.2f}")
                        elif key == 'rating':
                            metric_strs.append(f"{metrics[key]}★")
                        else:
                            metric_strs.append(f"{metrics[key]}")
                
                metrics_summary = f" ({', '.join(metric_strs)})" if metric_strs else ""
                
                reasoning_parts.append(
                    f"Main Reasoning: {passed} candidate(s) passed all {len(filter_rules)} filter(s): {filter_names_str}. "
                    f"Top candidate: {top_item.get('item_name', 'Unknown')}{metrics_summary}. "
                    f"All items will be ranked by number of filters passed, then by ranking criteria."
                )
            else:
                reasoning_parts.append(
                    f"Main Reasoning: {passed} candidate(s) passed all {len(filter_rules)} filter(s): {filter_names_str}. "
                    f"Items ranked by number of filters passed ({len(filter_rules)} total), then by ranking criteria."
                )
        else:
            # Find items with highest filter count
            max_filters_passed = max((e.get('filters_passed_count', 0) for e in evaluations), default=0)
            if max_filters_passed > 0:
                top_items = [e for e in evaluations if e.get('filters_passed_count', 0) == max_filters_passed]
                top_item = top_items[0] if top_items else None
                
                if top_item:
                    metrics = top_item.get('metrics', {})
                    metric_strs = []
                    for key in ['price', 'rating', 'reviews', 'value', 'score', 'count']:
                        if key in metrics:
                            if key == 'price':
                                metric_strs.append(f"${metrics[key]:.2f}")
                            elif key == 'rating':
                                metric_strs.append(f"{metrics[key]}★")
                            else:
                                metric_strs.append(f"{metrics[key]}")
                    
                    metrics_summary = f" ({', '.join(metric_strs)})" if metric_strs else ""
                    
                    reasoning_parts.append(
                        f"Main Reasoning: No candidates passed all {len(filter_rules)} filter(s): {filter_names_str}. "
                        f"Top candidate passed {max_filters_passed}/{len(filter_rules)} filters: {top_item.get('item_name', 'Unknown')}{metrics_summary}. "
                        f"Items ranked by number of filters passed ({max_filters_passed} max), then by ranking criteria."
                    )
                else:
                    reasoning_parts.append(
                        f"Main Reasoning: No candidates passed all {len(filter_rules)} filter(s): {filter_names_str}. "
                        f"Items ranked by number of filters passed, then by ranking criteria."
                    )
            else:
                reasoning_parts.append(
                    f"Main Reasoning: No candidates passed any of the {len(filter_rules)} filter(s): {filter_names_str}. "
                    f"Items ranked by number of filters passed (0 max), then by ranking criteria."
                )
        
        reasoning_parts.append("")
        reasoning_parts.append(f"Filters Applied ({len(filter_rules)} total):")
        
        for desc in filter_descriptions:
            reasoning_parts.append(f"  • {desc}")
        
        reasoning_parts.append(f"\nSummary: {passed} out of {total} candidates passed all {len(filter_rules)} filter(s), {failed} failed")
        
        # Show detailed evaluation for each candidate (similar to user's example)
        reasoning_parts.append("\nCandidates Evaluated:")
        
        # Sort by filters_passed_count (desc) to show best matches first
        sorted_evaluations = sorted(
            evaluations, 
            key=lambda e: (e.get('filters_passed_count', 0), e.get('item_name', '')),
            reverse=True
        )
        
        for item in sorted_evaluations[:10]:  # Show top 10
            item_name = item.get('item_name', 'Unknown')
            filters_passed = item.get('filters_passed_count', 0)
            total_filters = item.get('total_filters', 0)
            
            # Build filter status string
            filter_statuses = []
            for filter_name, result in item.get('filter_results', {}).items():
                status = "✓" if result.get('passed', False) else "✗"
                filter_statuses.append(f"{status} {filter_name}")
            
            filter_status_str = ", ".join(filter_statuses) if filter_statuses else "no filters"
            
            # Get key metrics for display
            metrics = item.get('metrics', {})
            metric_strs = []
            for key in ['price', 'rating', 'reviews', 'value', 'score', 'count']:
                if key in metrics:
                    if key == 'price':
                        metric_strs.append(f"${metrics[key]:.2f}")
                    elif key == 'rating':
                        metric_strs.append(f"{metrics[key]}★")
                    else:
                        metric_strs.append(f"{metrics[key]}")
            
            metrics_str = f" ({', '.join(metric_strs)})" if metric_strs else ""
            
            # Build detailed failure reasons with actual field values
            failed_details = []
            passed_details = []
            
            for filter_name, result in item.get('filter_results', {}).items():
                detail = result.get('detail', '')
                passed = result.get('passed', False)
                
                # Extract field name and value from filter rule
                filter_rule = next((r for r in filter_rules if r.get('name') == filter_name), None)
                if filter_rule:
                    field = filter_rule.get('field', '')
                    rule_type = filter_rule.get('rule_type', '')
                    value = filter_rule.get('value')
                    min_val = filter_rule.get('min')
                    max_val = filter_rule.get('max')
                    
                    # Get actual item value from metrics
                    item_value = metrics.get(field, 'N/A')
                    
                    # Try to extract from detail if available
                    if item_value == 'N/A' and detail:
                        # Try to parse value from detail string (e.g., "$34.99 is within range...")
                        import re
                        # Look for common patterns in detail
                        if field in detail.lower():
                            # Try to extract the value mentioned in detail
                            value_match = re.search(r'(\$?[\d.]+|[\w]+)', detail)
                            if value_match:
                                item_value = value_match.group(1)
                    
                    # Build comparison string
                    if rule_type == 'equals':
                        comp_str = f"{field} == {value}"
                    elif rule_type == 'min':
                        comp_str = f"{field} >= {value}"
                    elif rule_type == 'max':
                        comp_str = f"{field} <= {value}"
                    elif rule_type == 'range':
                        comp_str = f"{field} in [{min_val}-{max_val}]"
                    elif rule_type == 'contains':
                        comp_str = f"{field} contains '{value}'"
                    else:
                        comp_str = f"{filter_name}"
                    
                    if passed:
                        passed_details.append(f"{comp_str} (actual: {item_value})")
                    else:
                        failed_details.append(f"{comp_str} (actual: {item_value})")
            
            if filters_passed == total_filters:
                status_marker = "✓"
                status_text = f"PASSED all {total_filters} filters"
                if passed_details:
                    status_text += f" - {', '.join(passed_details[:3])}"  # Show first 3 passed
                    if len(passed_details) > 3:
                        status_text += f" and {len(passed_details) - 3} more"
            else:
                status_marker = "✗"
                if failed_details:
                    status_text = f"FAILED: {', '.join(failed_details[:3])}"  # Show first 3 failed
                    if len(failed_details) > 3:
                        status_text += f" and {len(failed_details) - 3} more"
                else:
                    status_text = f"Passed {filters_passed}/{total_filters} filters"
            
            # Use tree structure format - determine if this is the last item to show
            is_last_in_display = (item == sorted_evaluations[min(9, len(sorted_evaluations)-1)]) or (len(sorted_evaluations) <= 10 and item == sorted_evaluations[-1])
            
            if is_last_in_display:
                # Last item in the displayed list
                reasoning_parts.append(
                    f"  └── {status_marker} {item_name}{metrics_str} - {status_text}")
            else:
                reasoning_parts.append(
                    f"  ├── {status_marker} {item_name}{metrics_str} - {status_text}")
        
        if len(evaluations) > 10:
            remaining = len(evaluations) - 10
            passed_remaining = sum(1 for e in sorted_evaluations[10:] if e.get('passed', False))
            failed_remaining = remaining - passed_remaining
            reasoning_parts.append(f"  └── ... ({remaining} more: {passed_remaining} passed, {failed_remaining} failed)")
        
        return "\n".join(reasoning_parts)
    
    def generate_ranking_reasoning(
        self,
        ranked_candidates: List[Dict[str, Any]],
        selected_item: Optional[Dict[str, Any]] = None,
        step_name: Optional[str] = None
    ) -> str:
        """
        Generate automatic reasoning explanation for ranking and selection.
        
        Args:
            ranked_candidates: List of ranked candidates with scores
            selected_item: The selected item (if any)
            step_name: Optional step name for context
        
        Returns:
            Human-readable reasoning string
        """
        ranking_criteria = self.get_ranking_criteria(step_name)
        
        if not ranked_candidates:
            return "No candidates available for ranking."
        
        if not ranking_criteria:
            # Default ranking explanation
            if selected_item:
                return f"Selected '{selected_item.get('name', 'item')}' from {len(ranked_candidates)} candidate(s) using default ranking."
            return f"Ranked {len(ranked_candidates)} candidate(s) using default criteria."
        
        # Build criteria description
        criteria_parts = []
        if ranking_criteria.get('primary'):
            criteria_parts.append(f"primary: {ranking_criteria['primary']}")
        if ranking_criteria.get('secondary'):
            criteria_parts.append(f"secondary: {ranking_criteria['secondary']}")
        if ranking_criteria.get('tertiary'):
            criteria_parts.append(f"tertiary: {ranking_criteria['tertiary']}")
        
        criteria_desc = ", ".join(criteria_parts)
        
        # Build main reasoning summary at the top
        reasoning_parts = []
        
        if selected_item:
            selected_rank_item = next(
                (item for item in ranked_candidates 
                 if item.get('item_id') == selected_item.get('id')),
                None
            )
            
            if selected_rank_item:
                selected_name = selected_item.get('name') or selected_item.get('id', 'Unknown')
                filters_passed = selected_rank_item.get('filters_passed_count', 0)
                total_filters = selected_rank_item.get('total_filters', 0)
                criteria_score = selected_rank_item.get('criteria_score', 0)
                rank = selected_rank_item.get('rank', 1)
                
                # Get filter names that were passed
                filter_results = selected_rank_item.get('filter_results', {})
                passed_filter_names = [name for name, r in filter_results.items() if r.get('passed', False)]
                
                if filters_passed == total_filters and total_filters > 0:
                    main_reason = (
                        f"Main Reasoning: Selected '{selected_name}' (Rank #{rank}) because it passed all {total_filters} filters: "
                        f"{', '.join(passed_filter_names)}. "
                        f"Ranking score: {criteria_score:.2f} based on {criteria_desc}."
                    )
                elif total_filters > 0:
                    main_reason = (
                        f"Main Reasoning: Selected '{selected_name}' (Rank #{rank}) because it passed {filters_passed}/{total_filters} filters "
                        f"({', '.join(passed_filter_names) if passed_filter_names else 'none'}), "
                        f"which is the highest among items with {filters_passed} filters passed. "
                        f"Ranking score: {criteria_score:.2f} based on {criteria_desc}."
                    )
                else:
                    main_reason = (
                        f"Main Reasoning: Selected '{selected_name}' (Rank #{rank}) with ranking score: {criteria_score:.2f} "
                        f"based on {criteria_desc}."
                    )
                
                reasoning_parts.append(main_reason)
            else:
                reasoning_parts.append(
                    f"Main Reasoning: Ranked {len(ranked_candidates)} candidate(s) by: (1) filters passed, (2) then by criteria: {criteria_desc}"
                )
        else:
            reasoning_parts.append(
                f"Main Reasoning: Ranked {len(ranked_candidates)} candidate(s) by: (1) filters passed, (2) then by criteria: {criteria_desc}"
            )
        
        reasoning_parts.append("")
        reasoning_parts.append(f"Ranking Details:")
        
        # Show top 5 ranked items with filter information
        top_items = ranked_candidates[:5]
        for i, item in enumerate(top_items, 1):
            item_name = item.get('item_name', 'Unknown')
            filters_passed = item.get('filters_passed_count', 0)
            total_filters = item.get('total_filters', 0)
            criteria_score = item.get('criteria_score', item.get('total_score', 0))
            
            # Get key metrics for display
            metrics = item.get('metrics', {})
            metric_strs = []
            for key in ['price', 'rating', 'reviews', 'value', 'score', 'count']:
                if key in metrics:
                    if key == 'price':
                        metric_strs.append(f"${metrics[key]:.2f}")
                    elif key == 'rating':
                        metric_strs.append(f"{metrics[key]}★")
                    else:
                        metric_strs.append(f"{metrics[key]}")
            
            metrics_str = f" ({', '.join(metric_strs)})" if metric_strs else ""
            
            reasoning_parts.append(
                f"  {i}. {item_name}{metrics_str} - {filters_passed}/{total_filters} filters passed, criteria score: {criteria_score:.2f}"
            )
        
        if selected_item:
            selected_name = selected_item.get('name') or selected_item.get('id', 'Unknown')
            reasoning_parts.append(f"\nFinal Recommendation:")
            reasoning_parts.append(f"Selected: {selected_name}")
            
            # Find selected item in ranked list
            selected_rank_item = next(
                (item for item in ranked_candidates 
                 if item.get('item_id') == selected_item.get('id')),
                None
            )
            
            if selected_rank_item:
                filters_passed = selected_rank_item.get('filters_passed_count', 0)
                total_filters = selected_rank_item.get('total_filters', 0)
                rank = selected_rank_item.get('rank', 'N/A')
                criteria_score = selected_rank_item.get('criteria_score', 0)
                
                # Get key metrics for display
                metrics = selected_rank_item.get('metrics', {})
                metric_strs = []
                for key in ['price', 'rating', 'reviews', 'value', 'score', 'count']:
                    if key in metrics:
                        if key == 'price':
                            metric_strs.append(f"${metrics[key]:.2f}")
                        elif key == 'rating':
                            metric_strs.append(f"{metrics[key]}★")
                        else:
                            metric_strs.append(f"{metrics[key]}")
                
                metrics_str = f" ({', '.join(metric_strs)})" if metric_strs else ""
                
                if filters_passed == total_filters:
                    reason = f"Ranked #{rank} - PASSED ALL {total_filters} FILTERS{metrics_str}"
                    if criteria_desc:
                        primary_field = criteria_desc.split(',')[0].split(':')[1].strip() if ':' in criteria_desc else 'score'
                        primary_value = metrics.get(primary_field, 'N/A')
                        reason += f", highest {primary_field} ({primary_value})"
                else:
                    reason = f"Ranked #{rank} - passed {filters_passed}/{total_filters} filters (highest among items with {filters_passed} filters passed){metrics_str}"
                    if criteria_desc:
                        primary_field = criteria_desc.split(',')[0].split(':')[1].strip() if ':' in criteria_desc else 'score'
                        primary_value = metrics.get(primary_field, 'N/A')
                        reason += f", best {primary_field} ({primary_value})"
                
                reasoning_parts.append(f"Reasoning: {reason}")
                reasoning_parts.append(f"Ranking Score: {criteria_score:.2f}")
        
        return "\n".join(reasoning_parts)
    
    def generate_step_reasoning(
        self,
        step_name: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        evaluations: Optional[List[Dict[str, Any]]] = None,
        ranked_candidates: Optional[List[Dict[str, Any]]] = None,
        selected_item: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate automatic reasoning for any step based on available data.
        
        Args:
            step_name: Name of the step
            input_data: Input data for the step
            output_data: Output data from the step
            evaluations: Filter evaluation results (for filter steps)
            ranked_candidates: Ranked candidates (for ranking steps)
            selected_item: Selected item (for selection steps)
        
        Returns:
            Human-readable reasoning string
        """
        step_lower = step_name.lower()
        
        # Generate reasoning based on step type
        if 'filter' in step_lower and evaluations is not None:
            return self.generate_filter_reasoning(evaluations, step_name)
        
        elif ('rank' in step_lower or 'select' in step_lower) and ranked_candidates is not None:
            return self.generate_ranking_reasoning(ranked_candidates, selected_item, step_name)
        
        # Generic reasoning for other steps
        reasoning_parts = [f"Executed step: {step_name}"]
        
        if input_data:
            input_summary = self._summarize_data(input_data)
            if input_summary:
                reasoning_parts.append(f"Input: {input_summary}")
        
        if output_data:
            output_summary = self._summarize_data(output_data)
            if output_summary:
                reasoning_parts.append(f"Output: {output_summary}")
        
        return " | ".join(reasoning_parts)
    
    def _summarize_data(self, data: Dict[str, Any]) -> str:
        """Create a brief summary of data for reasoning."""
        if not data:
            return ""
        
        summary_parts = []
        
        # Common fields to summarize
        if 'candidates_count' in data:
            summary_parts.append(f"{data['candidates_count']} candidates")
        if 'total_evaluated' in data:
            summary_parts.append(f"{data['total_evaluated']} evaluated")
        if 'passed' in data:
            summary_parts.append(f"{data['passed']} passed")
        if 'failed' in data:
            summary_parts.append(f"{data['failed']} failed")
        if 'selected_item' in data:
            item = data['selected_item']
            if item:
                name = item.get('name') or item.get('id', 'item')
                summary_parts.append(f"selected: {name}")
        
        return ", ".join(summary_parts) if summary_parts else ""

