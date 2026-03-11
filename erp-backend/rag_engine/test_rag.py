from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

embeddings = OllamaEmbeddings(model="mxbai-embed-large")
vs = Chroma(
    collection_name="erp_apis",
    embedding_function=embeddings,
    persist_directory="./erp_chroma_db"
)

queries = [
    "prime de fin annee salaire avantages sociaux",
    "prime de fin d'année",
    "avantages sociaux mutuelle transport",
]

for query in queries:
    print(f"\n=== QUERY: {query} ===")
    results = vs.similarity_search_with_score(
        query,
        k=6,
        filter={"category": {"$in": ["policy", "procedure", "glossaire", "internal_communication"]}}
    )
    for doc, score in results:
        fname = doc.metadata.get("filename", "?")
        print(f"  Score: {score:.4f} | File: {fname}")
        print(f"  Preview: {doc.page_content[:80]}")
        print()