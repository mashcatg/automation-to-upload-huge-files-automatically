import os
import time
import mimetypes
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('upload_bot.log'),
        logging.StreamHandler()
    ]
)

class GoogleDriveUploadBot:
    def __init__(self, credentials_file='credentials.json', token_file='token.json'):
        self.SCOPES = ['https://www.googleapis.com/auth/drive.file']
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = self._authenticate()
        self.uploaded_count = 0
        self.batch_size = 10
        self.break_duration = 180  # 180 seconds (3 minutes)
        
    def _authenticate(self):
        """Authenticate and return Google Drive service object"""
        creds = None
        
        # Check if token file exists
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        
        # If there are no valid credentials, request authorization
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(f"Credentials file '{self.credentials_file}' not found!")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        return build('drive', 'v3', credentials=creds)
    
    def get_files_to_upload(self, local_folder_path, file_extensions=None):
        """Get list of files to upload from local folder"""
        if not os.path.exists(local_folder_path):
            raise FileNotFoundError(f"Local folder '{local_folder_path}' not found!")
        
        files_to_upload = []
        path = Path(local_folder_path)
        
        # Get all files recursively
        for file_path in path.rglob('*'):
            if file_path.is_file():
                # Filter by extensions if specified
                if file_extensions is None or file_path.suffix.lower() in file_extensions:
                    files_to_upload.append(file_path)
        
        logging.info(f"Found {len(files_to_upload)} files to upload")
        return files_to_upload
    
    def create_drive_folder(self, folder_name, parent_folder_id='root'):
        """Create a folder in Google Drive"""
        try:
            # Check if folder already exists
            query = f"name='{folder_name}' and parents='{parent_folder_id}' and mimeType='application/vnd.google-apps.folder'"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            
            if folders:
                logging.info(f"Folder '{folder_name}' already exists")
                return folders[0]['id']
            
            # Create new folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id]
            }
            
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            logging.info(f"Created folder '{folder_name}' with ID: {folder.get('id')}")
            return folder.get('id')
            
        except Exception as e:
            logging.error(f"Error creating folder: {str(e)}")
            return None
    
    def get_folder_id_by_name(self, folder_name, parent_folder_id='root'):
        """Find a folder ID by name"""
        try:
            query = f"name='{folder_name}' and parents='{parent_folder_id}' and mimeType='application/vnd.google-apps.folder'"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            
            if folders:
                folder_id = folders[0]['id']
                logging.info(f"Found folder '{folder_name}' with ID: {folder_id}")
                return folder_id
            else:
                logging.info(f"Folder '{folder_name}' not found")
                return None
                
        except Exception as e:
            logging.error(f"Error finding folder: {str(e)}")
            return None
            
    def list_folders(self, parent_folder_id='root'):
        """List all folders in the parent folder"""
        try:
            query = f"parents='{parent_folder_id}' and mimeType='application/vnd.google-apps.folder'"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            
            if not folders:
                print("No folders found.")
                return
                
            print("\nAvailable folders:")
            print("-" * 50)
            for folder in folders:
                print(f"Name: {folder['name']}\tID: {folder['id']}")
            print("-" * 50)
            
            return folders
            
        except Exception as e:
            logging.error(f"Error listing folders: {str(e)}")
            return None
    
    def upload_file(self, file_path, drive_folder_id='root'):
        """Upload a single file to Google Drive"""
        try:
            file_name = os.path.basename(file_path)
            
            # Check if file already exists in Drive
            query = f"name='{file_name}' and parents='{drive_folder_id}'"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            existing_files = results.get('files', [])
            
            if existing_files:
                logging.info(f"File '{file_name}' already exists in Drive, skipping...")
                return True
            
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = 'application/octet-stream'
            
            # File metadata
            file_metadata = {
                'name': file_name,
                'parents': [drive_folder_id]
            }
            
            # Upload file
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            
            file_obj = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            logging.info(f"Successfully uploaded: {file_name} (ID: {file_obj.get('id')})")
            return True
            
        except Exception as e:
            logging.error(f"Error uploading {file_path}: {str(e)}")
            return False
    
    def upload_with_breaks(self, local_folder_path, drive_folder_name=None, drive_folder_id=None, file_extensions=None):
        """Upload files with breaks after every batch"""
        try:
            # Get files to upload
            files_to_upload = self.get_files_to_upload(local_folder_path, file_extensions)
            
            if not files_to_upload:
                logging.info("No files to upload")
                return
            
            # Use existing folder ID if provided, otherwise create/get folder by name
            target_folder_id = 'root'
            if drive_folder_id:
                target_folder_id = drive_folder_id
                logging.info(f"Using existing folder with ID: {drive_folder_id}")
            elif drive_folder_name:
                target_folder_id = self.create_drive_folder(drive_folder_name)
                if not target_folder_id:
                    logging.error("Failed to create destination folder")
                    return
            
            total_files = len(files_to_upload)
            successful_uploads = 0
            failed_uploads = 0
            start_time = time.time()
            
            logging.info(f"Starting upload of {total_files} files...")
            
            for i, file_path in enumerate(files_to_upload):
                # Upload file
                if self.upload_file(str(file_path), target_folder_id):
                    successful_uploads += 1
                    self.uploaded_count += 1
                else:
                    failed_uploads += 1
                
                # Take break after every batch
                if self.uploaded_count % self.batch_size == 0 and i < total_files - 1:
                    logging.info(f"Uploaded {self.batch_size} files. Taking a {self.break_duration} second break...")
                    time.sleep(self.break_duration)
                    logging.info("Resuming uploads...")
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            hours, remainder = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            
            # Final summary
            logging.info("=" * 50)
            logging.info("UPLOAD SUMMARY")
            logging.info("=" * 50)
            logging.info(f"Total files processed: {total_files}")
            logging.info(f"Successful uploads: {successful_uploads}")
            logging.info(f"Failed uploads: {failed_uploads}")
            logging.info(f"Total upload time: {time_str}")
            
        except KeyboardInterrupt:
            logging.info("Upload interrupted by user")
        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")


def main():
    # Configuration
    LOCAL_FOLDER = "./files_to_upload"  # Change this to your local folder path
    
    # Option 1: Create or use folder by name
    DRIVE_FOLDER_NAME = "uploads"  # Will create this folder in Google Drive if it doesn't exist
    
    # Option 2: Use existing folder by ID (leave as None to use folder name instead)
    DRIVE_FOLDER_ID = None  # Set this to your folder ID to use an existing folder
    
    # Optional: filter by file extensions (None = upload all files)
    file_extensions = None  # Change to ['.txt', '.pdf', '.jpg'] if you want specific types
    
    # Create bot instance
    try:
        bot = GoogleDriveUploadBot()
        
        # Check if we're in list mode
        if len(sys.argv) > 1 and sys.argv[1] == "--list-folders":
            print("Listing available folders in Google Drive...")
            bot.list_folders()
            return
        
        print("=" * 60)
        print("GOOGLE DRIVE AUTO UPLOAD BOT")
        print("=" * 60)
        print(f"Local folder: {LOCAL_FOLDER}")
        if DRIVE_FOLDER_ID:
            print(f"Drive folder ID: {DRIVE_FOLDER_ID}")
        else:
            print(f"Drive folder name: {DRIVE_FOLDER_NAME}")
        print(f"File filter: {'All files' if file_extensions is None else ', '.join(file_extensions)}")
        print("=" * 60)
        print("\nTIP: Run 'python main.py --list-folders' to see available folders and their IDs")
        print("=" * 60)
        
        # Start uploading
        print("\nInitializing bot and authenticating with Google Drive...")
        print("Starting upload process...")
        bot.upload_with_breaks(
            local_folder_path=LOCAL_FOLDER,
            drive_folder_name=DRIVE_FOLDER_NAME if not DRIVE_FOLDER_ID else None,
            drive_folder_id=DRIVE_FOLDER_ID,
            file_extensions=file_extensions
        )
        
    except Exception as e:
        logging.error(f"Bot failed to start: {str(e)}")
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
