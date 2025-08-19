# Web Scraper Project

## Overview

This project provides a scalable pipeline for collecting, processing, and storing insurance related web content for downstream applications. The pipeline leverages AWS infrastructure, Qdrant vector database, and Python tools for web scraping and embedding generation.


## Architecture

The pipeline consists of two main stages: gathering useful links and preparing the knowledge base. 

<img width="862" height="536" alt="insurance drawio (1)" src="https://github.com/user-attachments/assets/1da89b33-a138-4f98-bea8-d59e238c30f2" />


### 1. Link Collection
- **Script:** `find_useful_links.py`
- **Purpose:** Parses insurance website sitemaps to extract relevant URLs.
- **Output:** Stores filtered URLs in `useful_links.txt`.

### 2. Knowledge Base Preparation

- **Script:** `web_scraper.py`
- **Purpose:** 
    - Scrapes webpages listed in `useful_links.txt`.
    - Converts HTML content to Markdown for easier processing.
    - Chunks the content for efficient embedding.
    - Generates vector embeddings (using GoogleAIEmbeddings).
    - Stores embeddings in a Qdrant vector database hosted on AWS EC2 with EBS-backed storage.


## AWS Setup Instructions
Follow these steps to deploy the pipeline on AWS:

### 1. Create an S3 bucket
- Go to AWS Console → S3 → Create bucket.
- Upload useful_links.txt files in the bucket.


### 2. Configure IAM Role
- Go to AWS Console → IAM → Roles → Create role.
    - **Trusted Entity Type:** AWS service
    - **Use Case:** EC2
    - **Permissions:** Attach `AmazonS3FullAccess` policy

### 3. Set up Security Group
- Go to AWS Console → EC2 → Security Groups → Create security group.
    - **Inbound Rules:**
        - SSH (TCP, Port 22) — Your IP
        - Custom TCP (Port 6333) — Your IP (Qdrant API)
        - Custom TCP (Port 6334) — Your IP (Qdrant gRPC)
    - **Outbound Rules:**
        - All traffic (All ports, 0.0.0.0/0)

### 4. Create and Launch EC2 Instance
- Go to AWS Console → EC2 → Launch instance.
    - **Name:** `qdrant-ec2`
    - **AMI:** Ubuntu Server 22.04 LTS (64-bit x86)
    - **Instance Type:** `t2.medium` 
    - **Key Pair:** Create a new key pair for SSH access
    - **Network Settings:** Attach the security group from Step 3
    - **IAM Role:** Attach the IAM role from Step 2

### 5. Attach EBS Volume
- Go to AWS Console → EC2 → Volumes → Create volume.
    - **Type:** `gp3`
    - **Size:** 10 GB (can adjusr later)
    - **Availability Zone:** Same as EC2 instance
- Attach the volume to your EC2 instance:
    - Actions → Attach Volume → Select instance (`/dev/sdf`)


### 6. Setup File System on EC2

SSH into EC2 instance.
```sh
ssh -i /path/to/your-key.pem ubuntu@<EC2_PUBLIC_IP>
```

Format and mount EBS volume. 
```
lsblk                      # List block devices to find your volume
sudo mkfs.ext4 /dev/xvdf   # Format the volume (replace xvdf if needed)

sudo mkdir -p /mnt/qdrant_data
sudo mount /dev/xvdf /mnt/qdrant_data
sudo chown ubuntu:ubuntu /mnt/qdrant_data
```

Make mount persistent across reboots.
```sh
sudo blkid /dev/xvdf       # Get the UUID of the volume
# Add the following line to /etc/fstab (replace YOUR-UUID-HERE):
echo 'UUID=YOUR-UUID-HERE /mnt/qdrant_data ext4 defaults,nofail 0 2' | sudo tee -a /etc/fstab
sudo mount -a              # Remount all filesystems
```

### 7. Deploy Qdrant Server with Docker

Install Docker
```sh
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
```

Run Qdrant container
```sh
docker run -d \
  --name qdrant_container \
  -p 6333:6333 \
  -p 6334:6334 \
  -v /mnt/qdrant_data:/qdrant/data \
  --restart unless-stopped \
  qdrant/qdrant:latest

```

### 8. Qdrant Database Collection Management
To manage Qdrant collections, use the below helper scripts. Before running the script update QDRANT_HOST and QDRANT_COLLECTION_NAME variable names in `setup_qdrant.py` and `check_qdrant.py` files to match your deployment settings.
- `setup_qdrant.py`: Execute this script to create a new collection in your Qdrant database. This is typically done once during initial setup or when you need to add a new collection.
- `check_qdrant.py`: Use this script to verify the status and configuration of an existing Qdrant collection. This helps confirm that your collection is available and correctly configured.


## Execution

Follow these steps to run the full pipeline 

1. Generate `useful_links.txt`
NOTE: You can also skip this and use the `useful_links.txt` in this repository directly to avoid rework.
Run `find_useful_links.py` locally to create the list of relevant URLs. You can modify `sitemap_links` variable in the script to add, remove or update sitemap links of insurance websites as needed. 

3. Upload S3 bucket
Upload the generated `useful_links.txt` into designated AWS S3 bucket.

4. Connect to EC2 instance
SSH into EC2 instance using the key pair
```sh
ssh -i /path/to/your-key.pem ubuntu@<EC2_PUBLIC_IP>
```

4. Copy `web_scraper.py` into EC2 instance
```sh
scp -i /path/to/your-key.pem web_scraper.py ubuntu@<EC2-PUBLIC-IP>:/home/ubuntu/
```
5. Install dependencies
```sh
sudo apt update && sudo apt install python3-pip -y
pip3 install requests boto3 langchain-core langchain-google-genai langchain qdrant-client

export GEMINI_API_KEY="your_api_key_here"
```
5. Configure script variables 
In `web_scraper.py` update the following variables to match the setup 
- QDRANT_COLLECTION_NAME: Name of Qdrant Collection for storing embeddings
- S3_BUCKET_NAME: Name of S3 bucket
- S3_FILE_KEY: Filename of textfile to read URLs from

6. Run the scraper
Execute `web_scraper.py` on your EC2 instance to process the links, generate embeddings, and store them in Qdrant.


7. Verify Data in Qdrant
Use `check_qdrant.py` to confirm that points have been successfully added to your Qdrant collection and to inspect its status.
