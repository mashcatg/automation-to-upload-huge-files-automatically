# automation-to-upload-huge-files-automatically
Google Drive Upload Bot is a Python tool for batch file uploads to Google Drive with API rate limit handling. It supports folder creation or use of existing ones, duplicate detection, file filtering, and detailed logs. Using OAuth 2.0, it’s ideal for bulk uploads, automated organization, and scheduled backups.


# Google Drive Upload Bot

A Python utility for automatically uploading files to Google Drive with batch processing and rate limiting capabilities.

## Description

The Google Drive Upload Bot is a tool designed to help you upload large numbers of files to Google Drive while respecting API rate limits. It includes features such as:

- Batch uploading with configurable breaks to avoid API rate limits
- Support for uploading to existing folders or creating new ones
- File filtering by extension
- Duplicate file detection to avoid re-uploading existing files
- Detailed logging of upload progress and results
- Command-line interface for listing available folders

This tool is particularly useful for scenarios where you need to upload a large number of files to Google Drive and want to ensure the process is reliable and doesn't trigger API rate limits.

## Requirements

```
google-api-python-client
google-auth
google-auth-oauthlib
google-auth-httplib2
```

## Setup

1. Create a Google Cloud project and enable the Google Drive API
2. Create OAuth 2.0 credentials and download the credentials JSON file
3. Rename the credentials file to `credentials.json` and place it in the same directory as the script
4. Install the required Python packages:

```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

## Usage

### Basic Usage

1. Edit the `main.py` file to configure your local folder path and Google Drive folder settings
2. Run the script:

```bash
python main.py
```

### List Available Folders

To see a list of available folders in your Google Drive (useful for finding folder IDs):

```bash
python main.py --list-folders
```

### Configuration Options

In the `main()` function of `main.py`, you can configure:

- `LOCAL_FOLDER`: Path to the local folder containing files to upload
- `DRIVE_FOLDER_NAME`: Name of the folder to create/use in Google Drive
- `DRIVE_FOLDER_ID`: ID of an existing Google Drive folder (optional)
- `file_extensions`: List of file extensions to filter by (e.g., `['.txt', '.pdf']`)

### Advanced Configuration

You can also modify these parameters in the `GoogleDriveUploadBot` class:

- `batch_size`: Number of files to upload before taking a break (default: 10)
- `break_duration`: Duration of break in seconds (default: 180)

## How It Works

1. The bot authenticates with Google Drive using OAuth 2.0
2. It scans the specified local folder for files to upload
3. Files are uploaded in batches with configurable breaks between batches
4. The bot checks for existing files to avoid duplicates
5. A summary of the upload process is provided upon completion

## License

This project is open source and available under the MIT License.
