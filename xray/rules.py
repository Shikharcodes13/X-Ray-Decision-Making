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
        
        if not field or field not in item:
            return {
                'passed': False,
                'detail': f'Field "{field}" not found in item'
            }
        
        item_value = item[field]
        
        if rule_type == 'range':
            if min_val is not None and max_val is not None:
                passed = min_val <= item_value <= max_val
                detail = f'{item_value} is {"within" if passed else "outside"} range {min_val}-{max_val}'
                return {'passed': passed, 'detail': detail}
        
        elif rule_type == 'min':
            if value is not None:
                passed = item_value >= value
                detail = f'{item_value} {"≥" if passed else "<"} {value}'
                return {'passed': passed, 'detail': detail}
        
        elif rule_type == 'max':
            if value is not None:
                passed = item_value <= value
                detail = f'{item_value} {"≤" if passed else ">"} {value}'
                return {'passed': passed, 'detail': detail}
        
        elif rule_type == 'equals':
            if value is not None:
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
            
            for filter_rule in filter_rules:
                filter_name = filter_rule.get('name', 'unnamed_filter')
                result = self.apply_filter(item, filter_rule)
                filter_results[filter_name] = result
                
                if not result['passed']:
                    all_passed = False
            
            evaluations.append({
                'item_id': item_id,
                'item_name': item_name,
                'passed': all_passed,
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
        
        # Build reasoning
        reasoning_parts = [
            f"Applied {len(filter_rules)} filter rule(s) to {total} candidate(s):"
        ]
        
        for desc in filter_descriptions:
            reasoning_parts.append(f"  • {desc}")
        
        reasoning_parts.append(f"\nResult: {passed} passed, {failed} failed")
        
        # Add details about failures if any
        if failed > 0:
            failed_items = [e for e in evaluations if not e.get('passed', False)]
            failed_reasons = []
            
            for item in failed_items[:5]:  # Show first 5 failures
                item_name = item.get('item_name', 'Unknown')
                failed_filters = [
                    name for name, result in item.get('filter_results', {}).items()
                    if not result.get('passed', True)
                ]
                if failed_filters:
                    failed_reasons.append(f"  • {item_name}: failed {', '.join(failed_filters)}")
            
            if failed_reasons:
                reasoning_parts.append("\nFailed items:")
                reasoning_parts.extend(failed_reasons)
                if failed > 5:
                    reasoning_parts.append(f"  ... and {failed - 5} more")
        
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
        
        # Build reasoning
        reasoning_parts = [
            f"Ranked {len(ranked_candidates)} candidate(s) using criteria: {criteria_desc}"
        ]
        
        # Show top 3 ranked items
        top_items = ranked_candidates[:3]
        for i, item in enumerate(top_items, 1):
            item_name = item.get('item_name', 'Unknown')
            total_score = item.get('total_score', 0)
            score_breakdown = item.get('score_breakdown', {})
            
            breakdown_str = ", ".join([
                f"{k}={v}" for k, v in score_breakdown.items()
            ])
            
            reasoning_parts.append(
                f"  {i}. {item_name} (score: {total_score:.2f}, breakdown: {breakdown_str})"
            )
        
        if selected_item:
            selected_name = selected_item.get('name') or selected_item.get('id', 'Unknown')
            reasoning_parts.append(f"\nSelected: {selected_name}")
            
            # Find selected item in ranked list
            selected_rank = next(
                (i + 1 for i, item in enumerate(ranked_candidates) 
                 if item.get('item_id') == selected_item.get('id')),
                None
            )
            
            if selected_rank:
                reasoning_parts.append(
                    f"Reason: Ranked #{selected_rank} with highest overall score based on {criteria_desc}"
                )
        
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

