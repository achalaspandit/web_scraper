import requests
import os
import uuid
import random
import time
import json
import boto3
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient, models


def get_urls_from_s3(bucket_name, file_key):
    """
    Downloads file from S3 bucket and extracts URLs from it.
    Returns a list of non-empty URLs.
    """
    s3 = boto3.client('s3')
    try:
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        urls_file_content = response['Body'].read().decode('utf-8')
        urls = urls_file_content.strip().split('\n')
        return [url for url in urls if url.strip()]
    except Exception as e:
        print(f"Error reading S3 file: {e}")
        return []
    
def get_clients():
    """Initialization of objects
    - Text splitter for chunking markdown
    - Qdrant vector DB client
    - Gemini embedding model
    - Gemini LLM for HTML parsing
    - HTML parsing prompt template
    Returns the initialized clients."""

    if not hasattr(get_clients, '_initialized'):
        get_clients.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
        )

        get_clients.qdrant_client = QdrantClient(host=QDRANT_HOST, port=int(QDRANT_PORT))
        
        get_clients.embedding_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GEMINI_API_KEY)
        
        get_clients.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GEMINI_API_KEY)

        # Prompt for extracting meaningful content from HTML using LLM
        get_clients.html_parser = """
            You are an expert HTML parser and data extractor. Your task is to analyze raw HTML content and extract only the meaningful, substantive information while completely ignoring all markup, styling, navigation, and decorative elements.

            Instructions:
            EXTRACT ONLY:
            Primary content text (articles, descriptions, product details, etc.)
            Data values (prices, dates, quantities, specifications)
            Contact information when present
            Lists of items or features that represent actual content
            All links to PDFs, documents, and downloadable files
            Image URLs and their associated alt text or captions
            Document links with their descriptive text
            Fineprint disclaimers

            COMPLETELY IGNORE:
            HTML tags, attributes, and markup syntax
            CSS classes, IDs, and styling information
            JavaScript code and script tags
            Navigation menus, headers, footers
            Advertisement content and promotional banners
            Social media widgets and sharing buttons
            Cookie notices, popup overlays, and modals
            Form elements unless they contain meaningful data
            Comments and debugging information
            Error messages and system notifications

            Output Format:
            Present the extracted information in clean, readable strictly MARKDOWN format using # for headers, formatting text (bold, italics, etc.), creating lists, and adding links and images
            Use natural language structure
            Preserve the logical hierarchy of information
            Maintain original wording exactly as found
            Separate distinct sections clearly
            Use bullet points or numbering only when the original content was clearly structured as a list
            For links to files/documents/images, format as: "Link Text" (URL)
            Group related links together and clearly label their purpose

            Quality Standards:
            Extract information exactly as written in the source
            Do not summarize, paraphrase, or interpret
            Do not add your own commentary or explanations
            If uncertain whether content is meaningful vs. decorative, err on the side of inclusion
            Preserve important contextual relationships between data points

            Input Format:
            Provide the raw HTML content below, and I will return only the extracted meaningful information.
            {html_content}"""
        get_clients._initialized = True
    
    return get_clients.text_splitter, get_clients.qdrant_client, get_clients.embedding_model, get_clients.llm, get_clients.html_parser


def scrape_html(url, max_retries=3, timeout=10, sleep_range=(1.5, 4.0)):
    """
    Scrapes HTML content from a URL using randomized user agents and retry logic.
    Returns HTML text on success, or None if all retries fail.
    """
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/117.0 Safari/537.36",
    ]
    BASE_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    for attempt in range(1, max_retries + 1):
        try:
            headers = BASE_HEADERS.copy()
            headers["User-Agent"] = random.choice(USER_AGENTS)
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text

        except requests.exceptions.RequestException as e:
            print(f"Error on attempt {attempt}: {e}")
            if attempt < max_retries:
                sleep_time = random.uniform(*sleep_range)
                print(f"Retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)
            else:
                print("Max retries reached. Skipping.")
                return None


def process_urls(urls):
    """
    Main pipeline for processing URLs:
    - Scrapes HTML from each URL
    - Uses LLM to extract meaningful content in Markdown
    - Splits Markdown into chunks
    - Embeds each chunk
    - Uploads chunks and embeddings to Qdrant vector DB
    - Returns a list of results for each URL
    """
    text_splitter, qdrant_client, embedding_model, llm, html_parser = get_clients()
    results = []
    for url in urls:
        # Scrape RAW HTML from link
        html_content = scrape_html(url)

        if html_content: # Check if scraping was successful
            # Extract markdown from RAW HTML
            html_parser_prompt = ChatPromptTemplate.from_template(html_parser)
            formatted_prompt = html_parser_prompt.format_messages(html_content=html_content)
            try:
                mrdwn = llm.invoke(formatted_prompt).content
            except Exception as e:
                print(f"Error invoking Gemini for URL {url}: {e}")
                results.append({"url": url, "status": "failed", "reason": f"gemini_api_error: {str(e)}"})
                continue

            #Chunk markdown use RecursiveCharacterTextSplitter
            chunks = text_splitter.create_documents([mrdwn])

            try:
                texts = [chunk.page_content for chunk in chunks]
                embeddings = embedding_model.embed_documents(texts)
            except Exception as e:
                print(f"Error getting embeddings for URL {url}: {e}")
                results.append({"url": url, "status": "failed", "reason": f"error: {str(e)}"})
                continue
              
            points = []
            for idx in range(len(embeddings)):
                points.append(
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embeddings[idx],
                        payload={"text": texts[idx], "url": url}
                    )
                )
                    
            try:
                # Upload chunks and embeddings to Qdrant
                qdrant_client.upsert(
                    collection_name=QDRANT_COLLECTION_NAME,
                    points=points
                )
                results.append({"url": url, "status": "success", "chunks": len(chunks)})
            except Exception as upload_error:
                results.append({"url": url, "status": "failed", "chunks":len(chunks), "reason": str(upload_error)})
            

        else:
            results.append({"url": url, "status": "failed", "reason": "scraping_failed"})
        
    return results

if __name__ == "__main__":
    # Load environment variables
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    QDRANT_HOST = "localhost"
    QDRANT_PORT = 6333
    QDRANT_COLLECTION_NAME = "new_trial_vector_store"

    # Define your S3 bucket and file
    S3_BUCKET_NAME = "achala-insurance-project"
    S3_FILE_KEY = "useful_links_short.txt"

    # Fetch the URLs from S3
    print(f"Fetching URLs from s3://{S3_BUCKET_NAME}/{S3_FILE_KEY}")
    urls_to_process = get_urls_from_s3(S3_BUCKET_NAME, S3_FILE_KEY)

    if not urls_to_process:
        print("No URLs to process. Exiting.")
    else:
        print(f"Found {len(urls_to_process)} URLs. Starting processing...")
        results = process_urls(urls_to_process)
        print("Processing complete. Results:")
        print(json.dumps(results, indent=2))