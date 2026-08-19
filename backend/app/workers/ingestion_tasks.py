from app.workers.celery_app import celery_app
from app.ingestion.pipeline import process_document

@celery_app.task(bind=True)
def process_document_async(self, file_bytes: bytes, file_name: str, product_id: str):
    """Asynchronous document ingestion task."""
    try:
        result = process_document(file_bytes, file_name, product_id)
        return result
    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise