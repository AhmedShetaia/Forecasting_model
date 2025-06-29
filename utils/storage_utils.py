"""
Utility functions for Azure Storage operations.
"""
import os
import logging
import shutil
from pathlib import Path
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.storage.fileshare import ShareServiceClient, ShareDirectoryClient

logger = logging.getLogger(__name__)

def upload_to_blob_storage(file_path, container_name, blob_name=None, connection_string=None):
    """
    Upload a file to Azure Blob Storage.
    
    Args:
        file_path: Path to the local file
        container_name: Azure Storage container name
        blob_name: Name for the blob (if None, uses the file basename)
        connection_string: Azure Storage connection string (if None, uses environment variable)
    
    Returns:
        URL of the uploaded blob, or None if upload failed
    """
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None
    
    # Get connection string from parameter or environment
    if not connection_string:
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        logger.error("Missing AZURE_STORAGE_CONNECTION_STRING environment variable")
        return None
    
    try:
        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Get or create container
        try:
            container_client = blob_service_client.get_container_client(container_name)
            # Create container if it doesn't exist
            if not container_client.exists():
                logger.info(f"Creating container: {container_name}")
                container_client.create_container(public_access='blob')
        except Exception as e:
            logger.error(f"Error accessing/creating container {container_name}: {str(e)}")
            return None
        
        # Determine blob name
        if blob_name is None:
            blob_name = os.path.basename(file_path)
        
        # Create blob client
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        # Set content type based on file extension
        content_type = "application/json" if file_path.endswith(".json") else "application/octet-stream"
        content_settings = ContentSettings(content_type=content_type)
        
        # Upload file
        with open(file_path, "rb") as data:
            logger.info(f"Uploading {file_path} to {container_name}/{blob_name}")
            blob_client.upload_blob(data, overwrite=True, content_settings=content_settings)
        
        # Get blob URL
        account_name = blob_service_client.account_name
        blob_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}"
        logger.info(f"File uploaded successfully to {blob_url}")
        
        return blob_url
        
    except Exception as e:
        logger.error(f"Error uploading file to blob storage: {str(e)}")
        return None

def create_file_share(share_name):
    """
    Create an Azure File Share if it doesn't exist.
    
    Args:
        share_name: Name of the Azure File Share to create
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Get connection string from environment
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        logger.error("Missing AZURE_STORAGE_CONNECTION_STRING environment variable")
        return False
    
    try:
        # Create file share service client
        share_service_client = ShareServiceClient.from_connection_string(connection_string)
        
        # Create share if it doesn't exist
        try:
            share_client = share_service_client.get_share_client(share_name)
            if not share_client.exists():
                logger.info(f"Creating file share: {share_name}")
                share_client.create_share()
            else:
                logger.info(f"File share {share_name} already exists")
            return True
        except Exception as e:
            logger.error(f"Error creating file share {share_name}: {str(e)}")
            return False
    
    except Exception as e:
        logger.error(f"Error accessing Azure Storage: {str(e)}")
        return False


def create_directory_in_share(share_name, directory_path):
    """
    Create a directory hierarchy in an Azure File Share.
    
    Args:
        share_name: Name of the Azure File Share
        directory_path: Path of the directory to create (e.g. 'scraping/scraped_data')
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Get connection string from environment
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        logger.error("Missing AZURE_STORAGE_CONNECTION_STRING environment variable")
        return False
    
    try:
        # Create file share service client
        share_service_client = ShareServiceClient.from_connection_string(connection_string)
        share_client = share_service_client.get_share_client(share_name)
        
        if not share_client.exists():
            logger.error(f"File share {share_name} does not exist")
            return False
        
        # Split path into components
        path_parts = directory_path.strip('/').split('/')
        current_path = ""
        
        # Create each directory level
        for part in path_parts:
            if not part:  # Skip empty parts
                continue
                
            if current_path:
                current_path = f"{current_path}/{part}"
            else:
                current_path = part
                
            # Create directory
            directory_client = share_client.get_directory_client(current_path)
            if not directory_client.exists():
                logger.info(f"Creating directory: {current_path}")
                directory_client.create_directory()
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating directory in file share: {str(e)}")
        return False


def upload_to_file_share(local_path, share_name, target_path=None):
    """
    Upload a file or directory to Azure File Share.
    
    Args:
        local_path: Path to local file or directory
        share_name: Name of the Azure File Share
        target_path: Path within share (defaults to same as local_path basename)
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Get connection string from environment
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        logger.error("Missing AZURE_STORAGE_CONNECTION_STRING environment variable")
        return False
    
    # Check if path exists
    if not os.path.exists(local_path):
        logger.error(f"Local path not found: {local_path}")
        return False
    
    try:
        # Create file share service client
        share_service_client = ShareServiceClient.from_connection_string(connection_string)
        share_client = share_service_client.get_share_client(share_name)
        
        if not share_client.exists():
            logger.error(f"File share {share_name} does not exist")
            return False
        
        # If directory, recursively upload contents
        if os.path.isdir(local_path):
            return upload_directory_to_share(local_path, share_name, target_path)
        
        # If target path not specified, use the file basename
        if target_path is None:
            target_path = os.path.basename(local_path)
        
        # Handle parent directory creation
        parent_dir = os.path.dirname(target_path)
        if parent_dir:
            create_directory_in_share(share_name, parent_dir)
        
        # Create file client
        file_client = share_client.get_file_client(target_path)
        
        # Upload file
        with open(local_path, "rb") as source_file:
            logger.info(f"Uploading {local_path} to {share_name}/{target_path}")
            file_client.upload_file(source_file)
        
        return True
        
    except Exception as e:
        logger.error(f"Error uploading to file share: {str(e)}")
        return False


def upload_directory_to_share(local_dir_path, share_name, target_dir_path=None):
    """
    Upload a directory and its contents to Azure File Share.
    
    Args:
        local_dir_path: Path to local directory
        share_name: Name of the Azure File Share
        target_dir_path: Path within share (defaults to directory basename)
    
    Returns:
        bool: True if successful, False otherwise
    """
    # If target path not specified, use the directory basename
    if target_dir_path is None:
        target_dir_path = os.path.basename(os.path.normpath(local_dir_path))
    
    # Create the directory in the share
    if not create_directory_in_share(share_name, target_dir_path):
        return False
    
    success = True
    
    # Walk through directory contents
    for root, dirs, files in os.walk(local_dir_path):
        # Get relative path from local_dir_path
        rel_path = os.path.relpath(root, local_dir_path)
        if rel_path == '.':
            rel_path = ""
            
        # Create directories
        for dir_name in dirs:
            if rel_path:
                share_dir_path = f"{target_dir_path}/{rel_path}/{dir_name}"
            else:
                share_dir_path = f"{target_dir_path}/{dir_name}"
                
            if not create_directory_in_share(share_name, share_dir_path):
                success = False
        
        # Upload files
        for file_name in files:
            local_file_path = os.path.join(root, file_name)
            if rel_path:
                share_file_path = f"{target_dir_path}/{rel_path}/{file_name}"
            else:
                share_file_path = f"{target_dir_path}/{file_name}"
                
            # Upload individual file
            if not upload_to_file_share(local_file_path, share_name, share_file_path):
                success = False
    
    return success
