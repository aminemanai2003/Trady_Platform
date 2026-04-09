import threading
import time

from django.apps import AppConfig


class RagTutorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rag_tutor"
    verbose_name = "RAG Strategy Tutor"

    def ready(self) -> None:
        """Pre-warm the sentence-transformers model in a background thread.

        We delay by 5 seconds so that all other app ready() hooks (deepface,
        facenet-pytorch, etc.) finish loading their PyTorch models first.
        Concurrent PyTorch meta-tensor init otherwise causes a load conflict.
        """
        def _warm() -> None:
            time.sleep(5)  # wait for all apps to finish loading
            try:
                from .services.ollama_service import get_embedding_huggingface  # noqa: PLC0415
                get_embedding_huggingface("warmup")
            except Exception:  # noqa: BLE001
                pass  # failure during warmup is non-fatal

        t = threading.Thread(target=_warm, name="rag-model-warmup", daemon=True)
        t.start()
