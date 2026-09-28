import random
import requests
import json
import os
from backend.utils import logger

class EmbeddingService:
    def __init__(self, model_name: str = "nomic-embed-text"):
        self.model_name = model_name
        
        # Load config
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "config.json"))
        self.ollama_url = "http://localhost:11434"

        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    cfg = json.load(f)
                    self.ollama_url = cfg.get("ollama_url", self.ollama_url)
                    self.model_name = cfg.get("embedding_model", self.model_name)
            except:
                pass

        # Fallback check for .env
        from dotenv import load_dotenv
        load_dotenv()
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", self.ollama_url)
        self.model_name = os.getenv("EMBEDDING_MODEL", self.model_name)

    def get_embedding(self, text: str) -> list:
        """
        Generates a text embedding vector.
        Queries the local Ollama embeddings service, falling back to a deterministic mock vector if offline.
        """
        try:
            logger.info(f"Querying local Ollama embeddings model '{self.model_name}'...")
            response = requests.post(
                f"{self.ollama_url.rstrip('/')}/api/embeddings",
                json={
                    "model": self.model_name,
                    "prompt": text
                },
                timeout=5.0
            )
            if response.status_code == 200:
                vector = response.json().get("embedding")
                if vector and isinstance(vector, list):
                    logger.info(f"Successfully generated local embedding with dimensions: {len(vector)}")
                    return vector
        except Exception as e:
            logger.warning(f"Ollama embedding lookup failed: {str(e)}. Using deterministic mock vector.")

        # Seed by text hash to have consistent embeddings for same text
        val = sum(ord(c) for c in text)
        random.seed(val)
        
        vector = [random.uniform(-1.0, 1.0) for _ in range(384)]
        # Normalize vector
        sq_sum = sum(v*v for v in vector)
        norm = sq_sum ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]
            
        return vector
