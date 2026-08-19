from typing import List, Dict, Any

def compare_loan_products(product_a: Dict[str, Any], product_b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare two loan products side by side.
    """
    return {
        "product_a": {
            "name": product_a.get("name"),
            "issuer": product_a.get("issuer"),
            "effective_date": product_a.get("effective_date"),
        },
        "product_b": {
            "name": product_b.get("name"),
            "issuer": product_b.get("issuer"),
            "effective_date": product_b.get("effective_date"),
        },
        "comparison_points": [
            {"attribute": "Issuer", "val_a": product_a.get("issuer"), "val_b": product_b.get("issuer")},
            {"attribute": "Effective Date", "val_a": product_a.get("effective_date"), "val_b": product_b.get("effective_date")}
        ]
    }
