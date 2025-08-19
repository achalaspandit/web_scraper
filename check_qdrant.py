from qdrant_client import QdrantClient

# UPDATE: Qdrant server connection details
QDRANT_HOST = "0.0.0.0"
QDRANT_PORT = 6333
QDRANT_COLLECTION_NAME = "new_trial_vector_store"

def check_existing_collection():
    """
    Connects to the Qdrant server and checks status collection.
    """
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        print("Successfully connected to Qdrant client.")
        
        # Check if collection exists
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if QDRANT_COLLECTION_NAME in collection_names:
            print(f"Collection '{QDRANT_COLLECTION_NAME}' found!")
            
            # Get collection info
            collection_info = client.get_collection(QDRANT_COLLECTION_NAME)
            print(f"Collection status: {collection_info.status}")
            print(f"Vector count: {collection_info.vectors_count}")
            print(f"Points count: {collection_info.points_count}")
        else:
            print(f"Collection '{QDRANT_COLLECTION_NAME}' not found.")
            print(f"Available collections: {collection_names}")
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    # Run the function to check existing Qdrant collection
    check_existing_collection()