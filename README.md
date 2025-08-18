# web_scraper

## Architecture

The pipeline consists of two main stages: gathering useful links and preparing the knowledge base. 

In the first stage, find_useful_links.py processes insurance website sitemap links to generate a list of relevant URLs, stored in useful_links.txt. 

In the second stage, web_scraper.py scrapes webpages from this list, converts HTML to markdown, chunks the content, generates embeddings, and stores them in a Qdrant vector database hosted on the same AWS EC2 instance with EBS storage.


<img width="862" height="536" alt="insurance drawio (1)" src="https://github.com/user-attachments/assets/1da89b33-a138-4f98-bea8-d59e238c30f2" />


## Setup
1. S3 bucket: Create new S3 bucket on AWS console and add text file into the bucket.

2. IAM Role: Create a new IAM role on AWS console with below properties
    - Trusted Entity Type: AWS service
    - Use Case: EC2
    - Permission Policy: AmazonS3FullAccess

3. Security Group: Create a new security group for EC2 instance on AWS console with following inbound and outbound rules.
    - Inbound Rules: SSH TCP - Port No 22 - Your IP, Custom TCP - Port No 6333 - Your IP, Custom TCP - Port No 6334 - Your IP
    - Outbound Rules: All traffic - All port ranges - 0.0.0.0/0 (Internet Gateway)

4. EC2 Instance: Create EC2 instance in AWS Console
    - Name: qdrant-ec2
    - AMI: Ubuntu Server 22.04 LTS (64-bit x86)
    - Instance type: t2.medium
    - Key pair: create and download new key pair
    - Network settings: Choose the newly created Security Group from Step 3
    - IAM Role: Choose newly created IAM role

5. EBS Volume: Create new EBS volume in volumes under EC2 in AWS console
    - Type: gp3
    - Size: 10 GB
    - Availability Zone: same as EC2 zone

    After creation, attach the volume to EC2.
    - Actions -> Attach Volume -> Select Instance (device name /dev/sdf)

6. Setup File System

From local system, ssh into EC2 instance
```
ssh -i /path/to/your-key.pem ubuntu@EC2_PUBLIC_IP
```
Within the ubuntu EC2 instance, setup persistent file system. 
```
lsblk
sudo mkfs.ext4 /dev/xvdf

sudo mkdir -p /mnt/qdrant_data
sudo mount /dev/xvdf /mnt/qdrant_data
sudo chown ubuntu:ubuntu /mnt/qdrant_data

#make mount persistent
sudo blkid /dev/xvdf
# copy the UUID from output, then:
echo 'UUID=YOUR-UUID-HERE /mnt/qdrant_data ext4 defaults,nofail 0 2' | sudo tee -a /etc/fstab
sudo mount -a
```

7. Qdrant Server
