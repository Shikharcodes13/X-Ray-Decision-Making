"""
Demo application: Competitor Product Selection

This demonstrates the X-Ray library by simulating a multi-step workflow
to find the best competitor product for a given seller's product.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from xray import XRay, Storage
import random
import time


# Mock data for demonstration
MOCK_PRODUCTS = [
    {"asin": "B0COMP01", "title": "HydroFlask 32oz Wide Mouth", "price": 44.99, "rating": 4.5, "reviews": 8932, "category": "Sports & Outdoors"},
    {"asin": "B0COMP02", "title": "Yeti Rambler 26oz", "price": 34.99, "rating": 4.4, "reviews": 5621, "category": "Sports & Outdoors"},
    {"asin": "B0COMP03", "title": "Generic Water Bottle", "price": 8.99, "rating": 3.2, "reviews": 45, "category": "Sports & Outdoors"},
    {"asin": "B0COMP04", "title": "Bottle Cleaning Brush Set", "price": 12.99, "rating": 4.6, "reviews": 3421, "category": "Sports & Outdoors"},
    {"asin": "B0COMP05", "title": "Replacement Lid for HydroFlask", "price": 15.99, "rating": 4.3, "reviews": 892, "category": "Sports & Outdoors"},
    {"asin": "B0COMP06", "title": "Water Bottle Carrier Bag with Strap", "price": 18.99, "rating": 4.1, "reviews": 234, "category": "Sports & Outdoors"},
    {"asin": "B0COMP07", "title": "Stanley Adventure Quencher 40oz", "price": 35.00, "rating": 4.3, "reviews": 4102, "category": "Sports & Outdoors"},
    {"asin": "B0COMP08", "title": "CamelBak Chute Mag 32oz", "price": 29.99, "rating": 4.2, "reviews": 5234, "category": "Sports & Outdoors"},
    {"asin": "B0COMP09", "title": "Klean Kanteen Classic 27oz", "price": 27.99, "rating": 4.0, "reviews": 3124, "category": "Sports & Outdoors"},
    {"asin": "B0COMP10", "title": "S'well Stainless Steel 25oz", "price": 45.00, "rating": 4.6, "reviews": 6789, "category": "Sports & Outdoors"},
    {"asin": "B0COMP11", "title": "Takeya Actives 24oz", "price": 19.99, "rating": 4.1, "reviews": 4567, "category": "Sports & Outdoors"},
    {"asin": "B0COMP12", "title": "Contigo Autoseal 24oz", "price": 16.99, "rating": 3.9, "reviews": 2890, "category": "Sports & Outdoors"},
    {"asin": "B0COMP13", "title": "Iron Flask 32oz", "price": 24.99, "rating": 4.4, "reviews": 5678, "category": "Sports & Outdoors"},
    {"asin": "B0COMP14", "title": "Simple Modern 32oz", "price": 22.99, "rating": 4.2, "reviews": 4321, "category": "Sports & Outdoors"},
    {"asin": "B0COMP15", "title": "Owala FreeSip 32oz", "price": 32.99, "rating": 4.5, "reviews": 7890, "category": "Sports & Outdoors"},
]


def generate_keywords(product_title: str, category: str) -> list:
    """Step 1: Generate search keywords (simulated LLM call)."""
    time.sleep(0.1)  # Simulate API call
    
    # Simple keyword extraction (in real scenario, this would be an LLM call)
    keywords = [
        product_title.lower(),
        f"{category.lower()} {product_title.split()[0]}",
    ]
    
    return keywords


def search_products(keyword: str, limit: int = 50) -> list:
    """Step 2: Search for candidate products (mock API)."""
    time.sleep(0.2)  # Simulate API call
    
    # Simulate search by returning random products
    # In reality, this would call an actual search API
    results = random.sample(MOCK_PRODUCTS, min(limit, len(MOCK_PRODUCTS)))
    
    return results


def apply_filters(candidates: list, reference_product: dict) -> dict:
    """Step 3: Apply filters to narrow down candidates."""
    ref_price = reference_product["price"]
    price_min = ref_price * 0.5
    price_max = ref_price * 2.0
    min_rating = 3.8
    min_reviews = 100
    
    filters_applied = {
        "price_range": {"min": price_min, "max": price_max, "rule": "0.5x - 2x of reference price"},
        "min_rating": {"value": min_rating, "rule": "Must be at least 3.8 stars"},
        "min_reviews": {"value": min_reviews, "rule": "Must have at least 100 reviews"}
    }
    
    evaluations = []
    passed = []
    
    for candidate in candidates:
        filter_results = {}
        
        # Price filter
        price_check = price_min <= candidate["price"] <= price_max
        filter_results["price_range"] = {
            "passed": price_check,
            "detail": f"${candidate['price']:.2f} is {'within' if price_check else 'outside'} ${price_min:.2f}-${price_max:.2f}"
        }
        
        # Rating filter
        rating_check = candidate["rating"] >= min_rating
        filter_results["min_rating"] = {
            "passed": rating_check,
            "detail": f"{candidate['rating']} {'>=' if rating_check else '<'} {min_rating}"
        }
        
        # Reviews filter
        reviews_check = candidate["reviews"] >= min_reviews
        filter_results["min_reviews"] = {
            "passed": reviews_check,
            "detail": f"{candidate['reviews']} {'>=' if reviews_check else '<'} {min_reviews}"
        }
        
        qualified = price_check and rating_check and reviews_check
        
        evaluations.append({
            "asin": candidate["asin"],
            "title": candidate["title"],
            "metrics": {
                "price": candidate["price"],
                "rating": candidate["rating"],
                "reviews": candidate["reviews"]
            },
            "filter_results": filter_results,
            "qualified": qualified
        })
        
        if qualified:
            passed.append(candidate)
    
    return {
        "evaluations": evaluations,
        "qualified_candidates": passed,
        "filters_applied": filters_applied,
        "total_evaluated": len(candidates),
        "passed": len(passed),
        "failed": len(candidates) - len(passed)
    }


def rank_and_select(candidates: list, reference_product: dict) -> dict:
    """Step 4: Rank candidates and select the best one."""
    if not candidates:
        return {"selected_competitor": None, "reason": "No qualified candidates"}
    
    # Ranking criteria: review count (primary), rating (secondary), price proximity (tertiary)
    ranked = []
    
    for candidate in candidates:
        # Normalize scores (0-1 scale)
        max_reviews = max(c["reviews"] for c in candidates)
        review_score = candidate["reviews"] / max_reviews if max_reviews > 0 else 0
        
        max_rating = max(c["rating"] for c in candidates)
        rating_score = candidate["rating"] / max_rating if max_rating > 0 else 0
        
        # Price proximity: closer to reference price is better
        ref_price = reference_product["price"]
        price_diff = abs(candidate["price"] - ref_price)
        max_price_diff = max(abs(c["price"] - ref_price) for c in candidates)
        price_proximity_score = 1 - (price_diff / max_price_diff) if max_price_diff > 0 else 0
        
        # Weighted total score
        total_score = (
            review_score * 0.5 +  # Primary: review count
            rating_score * 0.3 +  # Secondary: rating
            price_proximity_score * 0.2  # Tertiary: price proximity
        )
        
        ranked.append({
            "asin": candidate["asin"],
            "title": candidate["title"],
            "metrics": {
                "price": candidate["price"],
                "rating": candidate["rating"],
                "reviews": candidate["reviews"]
            },
            "score_breakdown": {
                "review_count_score": round(review_score, 2),
                "rating_score": round(rating_score, 2),
                "price_proximity_score": round(price_proximity_score, 2)
            },
            "total_score": round(total_score, 2)
        })
    
    # Sort by total score descending
    ranked.sort(key=lambda x: x["total_score"], reverse=True)
    
    # Add rank numbers
    for i, item in enumerate(ranked):
        item["rank"] = i + 1
    
    selected = ranked[0]
    
    return {
        "ranked_candidates": ranked,
        "selection": {
            "asin": selected["asin"],
            "title": selected["title"],
            "reason": f"Highest overall score ({selected['total_score']}) - top review count ({selected['metrics']['reviews']}) with strong rating ({selected['metrics']['rating']}★)"
        },
        "selected_competitor": {
            "asin": selected["asin"],
            "title": selected["title"],
            "price": selected["metrics"]["price"],
            "rating": selected["metrics"]["rating"],
            "reviews": selected["metrics"]["reviews"]
        },
        "ranking_criteria": {
            "primary": "review_count",
            "secondary": "rating",
            "tertiary": "price_proximity"
        }
    }


def run_competitor_selection(reference_product: dict):
    """
    Main workflow: Find the best competitor product.
    
    Args:
        reference_product: Dictionary with product details (title, category, price, etc.)
    """
    storage = Storage()
    
    with XRay(storage=storage) as xray:
        xray.add_metadata("workflow", "competitor_selection")
        xray.add_metadata("reference_product", reference_product)
        
        # Step 1: Generate keywords
        keywords = generate_keywords(reference_product["title"], reference_product["category"])
        
        xray.record_step(
            step_name="keyword_generation",
            input_data={
                "product_title": reference_product["title"],
                "category": reference_product["category"]
            },
            output_data={
                "keywords": keywords,
                "model": "gpt-4 (simulated)"
            },
            reasoning="Extracted key product attributes: material (stainless steel), capacity (32oz), feature (insulated)"
        )
        
        # Step 2: Search for candidates
        all_candidates = []
        for keyword in keywords:
            candidates = search_products(keyword, limit=25)
            all_candidates.extend(candidates)
        
        # Remove duplicates
        seen_asins = set()
        unique_candidates = []
        for candidate in all_candidates:
            if candidate["asin"] not in seen_asins:
                unique_candidates.append(candidate)
                seen_asins.add(candidate["asin"])
        
        xray.record_step(
            step_name="candidate_search",
            input_data={
                "keywords": keywords,
                "limit": 50
            },
            output_data={
                "total_results": len(MOCK_PRODUCTS),
                "candidates_fetched": len(unique_candidates),
                "candidates": unique_candidates[:10]  # Show first 10 in output
            },
            reasoning=f"Fetched {len(unique_candidates)} unique candidates from search; {len(MOCK_PRODUCTS)} total matches found"
        )
        
        # Step 3: Apply filters
        filter_result = apply_filters(unique_candidates, reference_product)
        
        xray.record_step(
            step_name="apply_filters",
            input_data={
                "candidates_count": len(unique_candidates),
                "reference_product": reference_product
            },
            filters_applied=filter_result["filters_applied"],
            evaluations=filter_result["evaluations"],
            output_data={
                "total_evaluated": filter_result["total_evaluated"],
                "passed": filter_result["passed"],
                "failed": filter_result["failed"]
            },
            reasoning=f"Applied price, rating, and review count filters to narrow candidates from {len(unique_candidates)} to {filter_result['passed']}"
        )
        
        # Step 4: Rank and select
        ranking_result = rank_and_select(filter_result["qualified_candidates"], reference_product)
        
        xray.record_step(
            step_name="rank_and_select",
            input_data={
                "candidates_count": len(filter_result["qualified_candidates"]),
                "reference_product": reference_product
            },
            ranking_criteria=ranking_result["ranking_criteria"],
            ranked_candidates=ranking_result["ranked_candidates"],
            selection=ranking_result["selection"],
            output_data={
                "selected_competitor": ranking_result["selected_competitor"]
            },
            reasoning=ranking_result["selection"]["reason"]
        )
        
        return {
            "execution_id": xray.execution_id,
            "selected_competitor": ranking_result["selected_competitor"]
        }


if __name__ == "__main__":
    # Example: Find competitor for a seller's product
    reference_product = {
        "asin": "B0XYZ123",
        "title": "Stainless Steel Water Bottle 32oz Insulated",
        "category": "Sports & Outdoors",
        "price": 29.99,
        "rating": 4.2,
        "reviews": 1247
    }
    
    print("🔍 Running Competitor Selection Workflow...")
    print(f"Reference Product: {reference_product['title']}")
    print()
    
    result = run_competitor_selection(reference_product)
    
    print(f"✅ Execution ID: {result['execution_id']}")
    print(f"✅ Selected Competitor: {result['selected_competitor']['title']}")
    print(f"   Price: ${result['selected_competitor']['price']}")
    print(f"   Rating: {result['selected_competitor']['rating']}★")
    print(f"   Reviews: {result['selected_competitor']['reviews']}")
    print()
    print(f"📊 View in dashboard: http://localhost:5000/execution/{result['execution_id']}")

