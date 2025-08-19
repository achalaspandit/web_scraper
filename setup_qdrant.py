from qdrant_client import QdrantClient, models

# Update Qdrant server connection details below.
QDRANT_HOST = "0.0.0.0"
QDRANT_PORT = 6333
QDRANT_COLLECTION_NAME = "new_trial_vector_store"

def create_qdrant_collection():
    """
    Connects to the Qdrant server and creates a new collection
    with specified vector size and distance metric.
    """
    try:
        #Initialize Qdrant client
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        print("Successfully connected to Qdrant client.")
    except Exception as e:
        print(f"Failed to connect to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}: {e}")
        print("Please ensure your EC2 instance is running, Qdrant container is up, and Security Group allows your IP on port 6333.")
        return

    try:
        # Create a new collection with 768-dimensional vectors(GoogleAIEmbeddings size) and cosine distance metric
        client.create_collection(
            collection_name=QDRANT_COLLECTION_NAME,
            vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
        )
        print(f"Collection '{QDRANT_COLLECTION_NAME}' created successfully.")

    except Exception as e:
        print(f"An error occurred during collection creation: {e}", exc_info=True)

if __name__ == "__main__":
    # Run the function to create the Qdrant collection
    create_qdrant_collection()