"""
Migrate WhatsApp chat data from ChromaDB to Pinecone

This script reads the existing ChromaDB vector database and migrates
all vectors to Pinecone cloud vector database.

Usage:
    python3 migrate_to_pinecone.py
"""

import os
import chromadb
from chromadb.config import Settings
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Configuration
VECTOR_DB_FOLDER = "VectorDB"
COLLECTION_NAME = "whatsapp_running_chat"
PINECONE_INDEX_NAME = "whatsapp-chat"

def main():
    print("="*60)
    print("ChromaDB to Pinecone Migration")
    print("="*60)
    print()

    # Check for required environment variables
    pinecone_api_key = os.getenv('PINECONE_API_KEY')
    openai_api_key = os.getenv('OPENAI_API_KEY')

    if not pinecone_api_key:
        print("❌ Error: PINECONE_API_KEY not found in .env file")
        print("Please add: PINECONE_API_KEY=your-pinecone-api-key")
        return

    if not openai_api_key:
        print("❌ Error: OPENAI_API_KEY not found in .env file")
        return

    # Initialize Pinecone
    print("[Step 1/4] Connecting to Pinecone...")
    pc = Pinecone(api_key=pinecone_api_key)

    # Create or get index
    print(f"[Step 2/4] Setting up Pinecone index '{PINECONE_INDEX_NAME}'...")

    # Check if index exists
    existing_indexes = pc.list_indexes()
    index_names = [index.name for index in existing_indexes]

    if PINECONE_INDEX_NAME not in index_names:
        print(f"Creating new index: {PINECONE_INDEX_NAME}")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=1536,  # OpenAI text-embedding-3-small dimension
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )

        # Wait for index to be ready
        print("Waiting for index to be ready...")
        time.sleep(10)
    else:
        print(f"Index '{PINECONE_INDEX_NAME}' already exists")

    # Connect to index
    index = pc.Index(PINECONE_INDEX_NAME)
    print(f"✅ Connected to Pinecone index")

    # Load ChromaDB
    print(f"[Step 3/4] Loading ChromaDB from '{VECTOR_DB_FOLDER}'...")

    if not os.path.exists(VECTOR_DB_FOLDER):
        print(f"❌ Error: VectorDB folder not found at {VECTOR_DB_FOLDER}")
        print("Please run 'python3 whatsappvector.py' first to create the database")
        return

    chroma_client = chromadb.PersistentClient(
        path=VECTOR_DB_FOLDER,
        settings=Settings(anonymized_telemetry=False)
    )

    try:
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
        print(f"✅ Loaded ChromaDB collection: {COLLECTION_NAME}")
    except Exception as e:
        print(f"❌ Error loading collection: {e}")
        return

    # Get all data from ChromaDB
    print(f"[Step 4/4] Migrating vectors to Pinecone...")

    # Get all items from ChromaDB
    results = collection.get(
        include=['embeddings', 'documents', 'metadatas']
    )

    if not results['ids']:
        print("❌ No data found in ChromaDB collection")
        return

    total_vectors = len(results['ids'])
    print(f"Found {total_vectors} vectors to migrate")

    # Prepare vectors for Pinecone
    vectors_to_upsert = []

    for i, (id, embedding, document, metadata) in enumerate(zip(
        results['ids'],
        results['embeddings'],
        results['documents'],
        results['metadatas']
    )):
        # Pinecone vector format: (id, embedding, metadata)
        # Add the document text to metadata for retrieval
        metadata_with_text = metadata.copy() if metadata else {}
        metadata_with_text['text'] = document

        vectors_to_upsert.append({
            'id': id,
            'values': embedding,
            'metadata': metadata_with_text
        })

    # Upsert to Pinecone in batches
    batch_size = 100
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i:i + batch_size]
        index.upsert(vectors=batch)
        print(f"Migrated batch {i//batch_size + 1}/{(len(vectors_to_upsert)-1)//batch_size + 1}")

    # Verify migration
    stats = index.describe_index_stats()
    print()
    print("="*60)
    print("✅ MIGRATION COMPLETE!")
    print("="*60)
    print(f"Total vectors migrated: {total_vectors}")
    print(f"Pinecone index stats: {stats['total_vector_count']} vectors")
    print(f"Index name: {PINECONE_INDEX_NAME}")
    print()
    print("You can now use the production app with Pinecone!")
    print("="*60)

if __name__ == "__main__":
    main()
