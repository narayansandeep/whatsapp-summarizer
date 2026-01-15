"""
WhatsApp Chat Vector Database Creator

This script reads WhatsApp chat data from the "WhatsApp Chat" folder,
parses the messages, and creates a vector database using ChromaDB and OpenAI embeddings.

Usage:
    python3 whatsappvector.py

The vector database will be stored in the "VectorDB" folder.
"""

import os
import re
from datetime import datetime
from typing import List, Dict
import chromadb
from chromadb.config import Settings
from openai import OpenAI
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
WHATSAPP_CHAT_FOLDER = "WhatsApp Chat"
VECTOR_DB_FOLDER = "VectorDB"
CHAT_FILE_NAME = "_chat.txt"
COLLECTION_NAME = "whatsapp_running_chat"

# Initialize OpenAI client
client = OpenAI()

def parse_whatsapp_message(line: str) -> Dict[str, str]:
    """
    Parse a WhatsApp message line into structured data.

    Format: [date, time] sender: message
    Example: [12/06/25, 5:43:09 PM] Sender Name: Message text
    """
    # Pattern to match WhatsApp message format
    pattern = r'^\[([^\]]+)\]\s+([^:]+):\s+(.*)$'
    match = re.match(pattern, line)

    if match:
        timestamp_str, sender, message = match.groups()
        return {
            'timestamp': timestamp_str.strip(),
            'sender': sender.strip(),
            'message': message.strip()
        }
    return None

def is_system_message(message: str) -> bool:
    """Check if a message is a system notification (not actual chat content)."""
    system_indicators = [
        '‎', # Zero-width character used in system messages
        'added', 'removed', 'left', 'joined',
        'created this group', 'changed the group',
        'Messages and calls are end-to-end encrypted',
        'changed this group\'s icon'
    ]
    return any(indicator in message for indicator in system_indicators)

def read_whatsapp_chat(file_path: str) -> List[Dict[str, str]]:
    """
    Read and parse WhatsApp chat file.

    Returns a list of message dictionaries with timestamp, sender, and message.
    """
    messages = []
    current_message = None

    print(f"Reading chat file: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Try to parse as a new message
            parsed = parse_whatsapp_message(line)

            if parsed:
                # Save previous message if it exists and is not a system message
                if current_message and not is_system_message(current_message['message']):
                    messages.append(current_message)

                current_message = parsed
            else:
                # This is a continuation of the previous message
                if current_message:
                    current_message['message'] += ' ' + line

        # Don't forget the last message
        if current_message and not is_system_message(current_message['message']):
            messages.append(current_message)

    print(f"Parsed {len(messages)} messages")
    return messages

def chunk_messages(messages: List[Dict[str, str]], chunk_size: int = 5) -> List[Dict[str, any]]:
    """
    Chunk messages into groups for better context in vector search.

    Groups consecutive messages into chunks to maintain conversation context.
    """
    chunks = []

    for i in range(0, len(messages), chunk_size):
        chunk_messages = messages[i:i + chunk_size]

        # Combine messages into a single text
        combined_text = "\n\n".join([
            f"[{msg['timestamp']}] {msg['sender']}: {msg['message']}"
            for msg in chunk_messages
        ])

        # Create metadata (ChromaDB only accepts str, int, float, bool)
        metadata = {
            'start_timestamp': chunk_messages[0]['timestamp'],
            'end_timestamp': chunk_messages[-1]['timestamp'],
            'num_messages': len(chunk_messages),
            'senders': ', '.join(list(set([msg['sender'] for msg in chunk_messages])))  # Convert list to string
        }

        chunks.append({
            'text': combined_text,
            'metadata': metadata
        })

    print(f"Created {len(chunks)} message chunks")
    return chunks

def create_vector_database(chunks: List[Dict[str, any]]) -> chromadb.Collection:
    """
    Create a ChromaDB vector database from message chunks using OpenAI embeddings.
    """
    print(f"Initializing ChromaDB in {VECTOR_DB_FOLDER}")

    # Create vector DB folder if it doesn't exist
    os.makedirs(VECTOR_DB_FOLDER, exist_ok=True)

    # Initialize ChromaDB client
    chroma_client = chromadb.PersistentClient(
        path=VECTOR_DB_FOLDER,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )

    # Delete existing collection if it exists
    try:
        chroma_client.delete_collection(name=COLLECTION_NAME)
        print(f"Deleted existing collection: {COLLECTION_NAME}")
    except:
        pass

    # Create new collection
    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "WhatsApp running group chat embeddings"}
    )

    print("Generating embeddings using OpenAI...")

    # Process chunks in batches
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]

        # Get texts for embedding
        texts = [chunk['text'] for chunk in batch]

        # Generate embeddings using OpenAI
        try:
            response = client.embeddings.create(
                input=texts,
                model="text-embedding-3-small"
            )

            embeddings = [item.embedding for item in response.data]

            # Add to ChromaDB
            collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=[chunk['metadata'] for chunk in batch],
                ids=[f"chunk_{i+j}" for j in range(len(batch))]
            )

            print(f"Processed batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")

        except Exception as e:
            print(f"Error processing batch {i//batch_size + 1}: {e}")
            continue

    print(f"✅ Vector database created successfully with {len(chunks)} chunks")
    return collection

def main():
    """Main function to create the vector database from WhatsApp chat."""
    print("="*60)
    print("WhatsApp Chat Vector Database Creator")
    print("="*60)
    print()

    # Check if chat file exists
    chat_file_path = os.path.join(WHATSAPP_CHAT_FOLDER, CHAT_FILE_NAME)
    if not os.path.exists(chat_file_path):
        print(f"❌ Error: Chat file not found at {chat_file_path}")
        print(f"Please ensure the WhatsApp chat export is in the '{WHATSAPP_CHAT_FOLDER}' folder")
        return

    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("  export OPENAI_API_KEY='your-api-key-here'")
        return

    try:
        # Step 1: Read and parse WhatsApp chat
        print("\n[Step 1/3] Reading WhatsApp chat...")
        messages = read_whatsapp_chat(chat_file_path)

        if not messages:
            print("❌ No messages found in chat file")
            return

        # Step 2: Chunk messages
        print("\n[Step 2/3] Chunking messages...")
        chunks = chunk_messages(messages, chunk_size=5)

        # Step 3: Create vector database
        print("\n[Step 3/3] Creating vector database...")
        collection = create_vector_database(chunks)

        # Summary
        print("\n" + "="*60)
        print("✅ SUCCESS!")
        print("="*60)
        print(f"Total messages parsed: {len(messages)}")
        print(f"Total chunks created: {len(chunks)}")
        print(f"Vector database location: {VECTOR_DB_FOLDER}/")
        print(f"Collection name: {COLLECTION_NAME}")
        print()
        print("You can now run the chat application:")
        print("  python3 app.py")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
