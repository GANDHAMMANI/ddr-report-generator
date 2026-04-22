import uuid
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict
from app.utils.logger import logger


# ── Chunking ──────────────────────────────────────────────────────────────────
def chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> List[str]:
    """Split markdown into overlapping chunks preserving sentence boundaries."""
    chunks = []
    sentences = text.replace('\n\n', '\n').split('\n')
    current = []
    current_len = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        words = sentence.split()
        current_len += len(words)
        current.append(sentence)

        if current_len >= chunk_size:
            chunks.append(' '.join(current))
            # Keep overlap
            overlap_words = ' '.join(current).split()[-overlap:]
            current = [' '.join(overlap_words)]
            current_len = len(overlap_words)

    if current:
        chunks.append(' '.join(current))

    return [c for c in chunks if len(c.strip()) > 50]


# ── ChromaDB RAG ──────────────────────────────────────────────────────────────
class DocumentRAG:
    """
    ChromaDB-backed RAG retriever.
    Embeds document chunks locally using sentence-transformers.
    Retrieves semantically relevant chunks for each query.
    """

    def __init__(self, collection_name: str):
        self.client = chromadb.Client()  # In-memory — no disk needed
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"  # Fast, 80MB, works offline
        )
        # Fresh collection per job
        col_name = f"{collection_name}_{uuid.uuid4().hex[:8]}"
        self.collection = self.client.create_collection(
            name=col_name,
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"ChromaDB collection created: {col_name}")

    def index_document(self, text: str, source: str):
        """Chunk and index a document."""
        chunks = chunk_text(text)
        logger.info(f"Indexing {source}: {len(chunks)} chunks")

        # Add in batches of 50
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            self.collection.add(
                documents=batch,
                ids=[f"{source}_chunk_{i+j}" for j, _ in enumerate(batch)],
                metadatas=[{"source": source, "chunk_index": i+j} for j, _ in enumerate(batch)]
            )

        logger.info(f"Indexed {len(chunks)} chunks from {source}")

    def retrieve(self, query: str, n_results: int = 8, source_filter: str = None) -> List[str]:
        """Retrieve top-k semantically relevant chunks for a query."""
        where = {"source": source_filter} if source_filter else None
        results = self.collection.query(
            query_texts=[query],
            n_results=min(n_results, self.collection.count()),
            where=where,
        )
        chunks = results["documents"][0] if results["documents"] else []
        return chunks

    def retrieve_multi(self, queries: List[str], n_per_query: int = 5,
                       source_filter: str = None) -> str:
        """Run multiple queries and return deduplicated relevant content."""
        seen = set()
        all_chunks = []

        for query in queries:
            chunks = self.retrieve(query, n_results=n_per_query,
                                   source_filter=source_filter)
            for chunk in chunks:
                if chunk not in seen:
                    seen.add(chunk)
                    all_chunks.append(chunk)

        result = "\n\n---\n\n".join(all_chunks)
        logger.info(f"Retrieved {len(all_chunks)} unique chunks for {len(queries)} queries")
        return result


# ── Query Templates ───────────────────────────────────────────────────────────

INSPECTION_QUERIES = [
    "property name client company owner",
    "property address location street city",
    "inspection date inspector name",
    "area observations defects issues found",
    "severity critical high medium low",
    "missing information not available unclear",
    "recommendations repair replace",
    "thermal anomaly temperature finding",
]

THERMAL_QUERIES = [
    "client XYC corporation who ordered inspection",
    "client name company XYC corporation",
    "property name location ABC company",
    "property address street city",
    "service date inspection date",
    "equipment used FLIR camera thermographer",
    "critical severe alert advisory finding",
    "temperature max min rise reference point",
    "area location switchyard transformer breaker",
    "repair cost recommendation replace",
    "anomaly fault connection overheating bushing",
    "FPE stab-lok breaker panelboard",
    "missing cover junction box panel",
]