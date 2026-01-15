"""
WhatsApp Chat Vector Database Creator - Pinecone Version

This script reads WhatsApp chat data from the "WhatsApp Chat" folder,
parses the messages, and creates a vector database using Pinecone and OpenAI embeddings.

Usage:
    python3 whatsappvector_pinecone.py

The vectors will be stored in Pinecone cloud database.
"""

import os
import re
from datetime import datetime
from typing import List, Dict
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
import json
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

# Configuration
WHATSAPP_CHAT_FOLDER = "WhatsApp Chat"
CHAT_FILE_NAME = "_chat.txt"
PINECONE_INDEX_NAME = "whatsapp-chat"

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

        # Create metadata
        metadata = {
            'start_timestamp': chunk_messages[0]['timestamp'],
            'end_timestamp': chunk_messages[-1]['timestamp'],
            'num_messages': str(len(chunk_messages)),  # Convert to string for Pinecone
            'senders': ', '.join(list(set([msg['sender'] for msg in chunk_messages])))
        }

        chunks.append({
            'text': combined_text,
            'metadata': metadata
        })

    print(f"Created {len(chunks)} message chunks")
    return chunks

def create_pinecone_database(chunks: List[Dict[str, any]]) -> None:
    """
    Create a Pinecone vector database from message chunks using OpenAI embeddings.
    """
    print(f"Initializing Pinecone...")

    # Get API key
    pinecone_api_key = os.getenv('PINECONE_API_KEY')
    if not pinecone_api_key:
        raise Exception("PINECONE_API_KEY not found in environment variables")

    # Initialize Pinecone
    pc = Pinecone(api_key=pinecone_api_key)

    # Check if index exists
    print(f"Setting up Pinecone index '{PINECONE_INDEX_NAME}'...")
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
        # Delete all existing vectors to start fresh
        index = pc.Index(PINECONE_INDEX_NAME)
        print("Clearing existing vectors...")
        index.delete(delete_all=True)
        time.sleep(2)

    # Connect to index
    index = pc.Index(PINECONE_INDEX_NAME)
    print(f"✅ Connected to Pinecone index")

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

            # Prepare vectors for Pinecone
            vectors_to_upsert = []
            for j, (embedding, chunk) in enumerate(zip(embeddings, batch)):
                metadata = chunk['metadata'].copy()
                metadata['text'] = chunk['text']  # Add text to metadata for retrieval

                vectors_to_upsert.append({
                    'id': f"chunk_{i+j}",
                    'values': embedding,
                    'metadata': metadata
                })

            # Upsert to Pinecone
            index.upsert(vectors=vectors_to_upsert)

            print(f"Processed batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")

        except Exception as e:
            print(f"Error processing batch {i//batch_size + 1}: {e}")
            continue

    # Verify
    stats = index.describe_index_stats()
    print(f"✅ Vector database created successfully with {stats['total_vector_count']} chunks")

def main():
    """Main function to create the vector database from WhatsApp chat."""
    print("="*60)
    print("WhatsApp Chat Vector Database Creator - Pinecone")
    print("="*60)
    print()

    # Check if chat file exists
    chat_file_path = os.path.join(WHATSAPP_CHAT_FOLDER, CHAT_FILE_NAME)
    if not os.path.exists(chat_file_path):
        print(f"❌ Error: Chat file not found at {chat_file_path}")
        print(f"Please ensure the WhatsApp chat export is in the '{WHATSAPP_CHAT_FOLDER}' folder")
        return

    # Check for API keys
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key in .env file")
        return

    if not os.getenv('PINECONE_API_KEY'):
        print("❌ Error: PINECONE_API_KEY environment variable not set")
        print("Please set your Pinecone API key in .env file")
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

        # Step 3: Create Pinecone database
        print("\n[Step 3/3] Creating Pinecone vector database...")
        create_pinecone_database(chunks)

        # Summary
        print("\n" + "="*60)
        print("✅ SUCCESS!")
        print("="*60)
        print(f"Total messages parsed: {len(messages)}")
        print(f"Total chunks created: {len(chunks)}")
        print(f"Pinecone index: {PINECONE_INDEX_NAME}")
        print()
        print("You can now run the chat application:")
        print("  python3 app_prod.py")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
