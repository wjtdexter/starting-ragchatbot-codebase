"""Real system integration test to diagnose 'query failed' issue"""

import pytest
import os
import sys

# Mark as integration test
pytestmark = pytest.mark.integration


class TestRealSystemIntegration:
    """Test real RAG system to diagnose 'query failed' issue"""

    @pytest.fixture
    def real_config(self):
        """Use real config from the system"""
        # Add backend to path
        backend_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(backend_dir))

        from config import config
        return config

    def test_config_has_api_key(self, real_config):
        """Test: ANTHROPIC_API_KEY is configured"""
        assert real_config.ANTHROPIC_API_KEY, "ANTHROPIC_API_KEY is missing!"
        assert real_config.ANTHROPIC_API_KEY != "", "ANTHROPIC_API_KEY is empty!"
        print(f"✓ API Key found (length: {len(real_config.ANTHROPIC_API_KEY)})")

    def test_chromadb_exists(self, real_config):
        """Test: ChromaDB database exists and has data"""
        import chromadb
        from chromadb.config import Settings

        # Check if database directory exists
        db_path = real_config.CHROMA_PATH
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(__file__), db_path)

        assert os.path.exists(db_path), f"ChromaDB path does not exist: {db_path}"
        print(f"✓ ChromaDB directory exists: {db_path}")

        # Try to connect and check collections
        try:
            client = chromadb.PersistentClient(
                path=db_path,
                settings=Settings(anonymized_telemetry=False)
            )

            # Check collections exist
            collections = client.list_collections()
            collection_names = [c.name for c in collections]
            print(f"✓ Collections found: {collection_names}")

            assert "course_catalog" in collection_names, "course_catalog collection missing"
            assert "course_content" in collection_names, "course_content collection missing"

            # Check data counts
            catalog = client.get_collection("course_catalog")
            content = client.get_collection("course_content")

            catalog_count = catalog.count()
            content_count = content.count()

            print(f"✓ course_catalog: {catalog_count} items")
            print(f"✓ course_content: {content_count} items")

            assert catalog_count > 0, "course_catalog is empty!"
            assert content_count > 0, "course_content is empty!"

        except Exception as e:
            pytest.fail(f"Failed to connect to ChromaDB: {e}")

    def test_vector_store_initialization(self, real_config):
        """Test: VectorStore can be initialized and queried"""
        from vector_store import VectorStore

        try:
            store = VectorStore(
                chroma_path=real_config.CHROMA_PATH,
                embedding_model=real_config.EMBEDDING_MODEL,
                max_results=real_config.MAX_RESULTS
            )
            print("✓ VectorStore initialized successfully")

            # Try a simple search
            results = store.search(query="test", limit=1)
            print(f"✓ Search executed: error={results.error}, is_empty={results.is_empty()}")

        except Exception as e:
            pytest.fail(f"VectorStore initialization/search failed: {e}")

    def test_anthropic_api_connection(self, real_config):
        """Test: Can connect to Anthropic API"""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=real_config.ANTHROPIC_API_KEY)

            # Simple API call to test connection
            response = client.messages.create(
                model=real_config.ANTHROPIC_MODEL,
                max_tokens=10,
                temperature=0,
                messages=[{"role": "user", "content": "Say 'OK' if you can read this"}]
            )

            assert response.content[0].text, "No response from API"
            print(f"✓ Anthropic API connected: {response.content[0].text}")

        except Exception as e:
            pytest.fail(f"Anthropic API connection failed: {e}")

    def test_full_query_pipeline(self, real_config):
        """Test: Complete query pipeline with real system"""
        from rag_system import RAGSystem

        try:
            # Initialize real RAG system
            rag = RAGSystem(real_config)
            print("✓ RAGSystem initialized")

            # Try a real query
            answer, sources = rag.query("What is RAG?")
            print(f"✓ Query executed successfully")
            print(f"  Answer length: {len(answer)} chars")
            print(f"  Sources count: {len(sources)}")
            print(f"  First 100 chars of answer: {answer[:100]}...")

            assert answer, "Answer is empty!"
            assert isinstance(answer, str), "Answer should be string"
            assert isinstance(sources, list), "Sources should be list"

        except Exception as e:
            pytest.fail(f"Full query pipeline failed: {e}\n{type(e).__name__}: {str(e)}")

    def test_error_message_format(self, real_config):
        """Test: Check what error message the system returns"""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)

        try:
            response = client.post(
                "/api/query",
                json={"query": "What is RAG?"}
            )

            print(f"Response status code: {response.status_code}")

            if response.status_code != 200:
                print(f"Response detail: {response.json()}")
            else:
                data = response.json()
                print(f"✓ Query succeeded")
                print(f"  Answer preview: {data.get('answer', '')[:100]}...")
                print(f"  Sources: {data.get('sources', [])}")

        except Exception as e:
            pytest.fail(f"Endpoint test failed: {e}")


# Add Path import
from pathlib import Path
