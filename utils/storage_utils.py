"""
Utility functions for Azure Storage operations.
"""
import os
import logging
from azure.storage.blob import BlobServiceClient, ContentSettings

logger = logging.getLogger(__name__)

def upload_to_blob_storage(file_path, container_name, blob_name=None):
    """
    Upload a file to Azure Blob Storage.
    
    Args:
        file_path: Path to the local file
        container_name: Azure Storage container name
        blob_name: Name for the blob (if None, uses the file basename)
    
    Returns:
        URL of the uploaded blob, or None if upload failed
    """
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None
    
    # Get connection string from environment
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
