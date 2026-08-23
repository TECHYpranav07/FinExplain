"""
Ingest the 5 documents from documents/top5 into dedicated evaluation products.
"""
import os
import sys
import uuid

sys.path.insert(0, r"d:\Projects\fine-explain\backend")

from app.db.supabase_client import get_supabase_client
from app.ingestion.pipeline import process_document

TOP5_DIR = r"d:\Projects\fine-explain\documents\top5"
EVAL_USER_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"

DOC_CONFIGS = [
    {
        "key": "axis_lap",
        "file": "loan-against-property-agreement-english---08062026.pdf",
        "product_name": "Axis Finance Loan Against Property",
        "issuer": "Axis Finance Limited",
        "product_type": "loan_against_property",
    },
    {
        "key": "axis_pl",
        "file": "pl-loan-agreement-english-v290325.pdf",
        "product_name": "Axis Finance Personal Loan Agreement",
        "issuer": "Axis Finance Limited",
        "product_type": "personal_loan",
    },
    {
        "key": "sib_onescore_pl",
        "file": "tandc_sib_onescore_personal_loan.pdf",
        "product_name": "South Indian Bank OneScore Personal Loan",
        "issuer": "South Indian Bank",
        "product_type": "personal_loan",
    },
    {
        "key": "hdfc_home_loan",
        "file": "HDFC-Bank-Home-Loan-Agreement.pdf",
        "product_name": "HDFC Bank Home Loan Agreement",
        "issuer": "HDFC Bank Limited",
        "product_type": "home_loan",
    },
    {
        "key": "gss_term_loan",
        "file": "gss-term-loan-agreement-ccd-5.pdf",
        "product_name": "GSS Term Loan CCD Facility",
        "issuer": "GSS Financial / CCD",
        "product_type": "term_loan",
    },
]

def main():
    supabase = get_supabase_client()
    created_map = {}

    print("=" * 80)
    print("INGESTING TOP 5 DOCUMENTS FOR BENCHMARK")
    print("=" * 80)

    for item in DOC_CONFIGS:
        file_path = os.path.join(TOP5_DIR, item["file"])
        if not os.path.exists(file_path):
            print(f"[ERROR] File not found: {file_path}")
            continue

        # 1. Create or retrieve Product in Supabase
        existing_prods = (
            supabase.table("products")
            .select("*")
            .eq("name", item["product_name"])
            .eq("user_id", EVAL_USER_ID)
            .execute()
            .data
        )

        if existing_prods:
            product = existing_prods[0]
            product_id = product["id"]
            print(f"\n[Product Exists] {item['product_name']} -> {product_id}")
        else:
            product_id = str(uuid.uuid4())
            new_prod = {
                "id": product_id,
                "name": item["product_name"],
                "issuer": item["issuer"],
                "effective_date": "2026-08-01",
                "user_id": EVAL_USER_ID,
            }
            supabase.table("products").insert(new_prod).execute()
            print(f"\n[Created Product] {item['product_name']} -> {product_id}")

        # 2. Ingest Document via process_document
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        try:
            res = process_document(
                file_bytes=file_bytes,
                file_name=item["file"],
                product_id=product_id,
                user_id=EVAL_USER_ID,
            )
            print(f"[Ingestion Result] {item['file']} -> {res.get('status', 'ok')} (Doc ID: {res.get('document_id')})")
        except Exception as e:
            print(f"[Ingestion Error] {item['file']}: {e}")

        created_map[item["key"]] = {
            "product_id": product_id,
            "product_name": item["product_name"],
            "filename": item["file"],
        }

    print("\n" + "=" * 80)
    print("MAPPING SUMMARY:")
    for k, v in created_map.items():
        print(f"  {k}: {v['product_id']} | {v['product_name']} ({v['filename']})")
    print("=" * 80)

if __name__ == "__main__":
    main()
