# jarules_agent/connectors/github_connector.py

import requests
import base64
from typing import Optional, List, Dict, Any

class GitHubClient:
    """
    A client for interacting with the GitHub API.
    """
    BASE_API_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        """
        Initializes the GitHubClient.

        Args:
            token: Optional. A GitHub personal access token (PAT) for authentication.
        """
        self.token = token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Makes an HTTP request to the GitHub API.

        Args:
            method: HTTP method (e.g., "GET", "POST").
            url: The full URL for the API endpoint.
            **kwargs: Additional keyword arguments to pass to requests.request.

        Returns:
            A requests.Response object.

        Raises:
            requests.exceptions.RequestException: For network or HTTP errors.
        """
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
            return response
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error occurred: {e} - {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"Error during request to {url}: {e}")
            raise

    def list_repo_files(self, owner: str, repo: str, path: str = '') -> List[str]:
        """
        Lists files and directories in a GitHub repository path.

        Args:
            owner: The owner of the repository.
            repo: The name of the repository.
            path: The path to the directory in the repository. Defaults to root.

        Returns:
            A list of names of files and directories in the specified path.
            Returns an empty list if an error occurs or the path is invalid.
        """
        url = f"{self.BASE_API_URL}/repos/{owner}/{repo}/contents/{path.lstrip('/')}"
        try:
            response = self._request("GET", url)
            contents = response.json()
            if isinstance(contents, list): # Ensure contents is a list (directory listing)
                return [item['name'] for item in contents]
            else: # Could be a single file if path pointed to a file, or an error object
                print(f"Path '{path}' in '{owner}/{repo}' is not a directory or not found.")
                return []
        except requests.exceptions.RequestException as e:
            print(f"Error listing repository files for {owner}/{repo}/{path}: {e}")
            return []
        except (KeyError, TypeError, ValueError) as e: # JSON parsing or structure errors
            print(f"Error parsing response for {owner}/{repo}/{path}: {e}")
            return []


    def read_repo_file(self, owner: str, repo: str, file_path: str) -> Optional[str]:
        """
        Reads the content of a file from a GitHub repository.

        Args:
            owner: The owner of the repository.
            repo: The name of the repository.
            file_path: The path to the file in the repository.

        Returns:
            The content of the file as a string, or None if an error occurs.
        """
        url = f"{self.BASE_API_URL}/repos/{owner}/{repo}/contents/{file_path.lstrip('/')}"
        try:
            response = self._request("GET", url)
            file_data = response.json()

            if not isinstance(file_data, dict):
                if isinstance(file_data, list): # Path was a directory
                    print(f"Error: Path '{file_path}' in '{owner}/{repo}' is a directory, not a file.")
                else: # Unexpected response structure
                    print(f"Unexpected response structure for {owner}/{repo}/{file_path} (not a dict): {file_data}")
                return None

            if file_data.get('type') != 'file':
                print(f"Path '{file_path}' in '{owner}/{repo}' is not a file (type is '{file_data.get('type')}').")
                return None

            # Attempt to decode 'content' if present
            if 'content' in file_data:
                content_base64 = file_data['content']
                # Ensure padding for base64 decoding
                missing_padding = len(content_base64) % 4
                if missing_padding:
                    content_base64 += '=' * (4 - missing_padding)
                try:
                    decoded_content = base64.b64decode(content_base64).decode('utf-8')
                    return decoded_content # Successfully decoded
                except (base64.binascii.Error, UnicodeDecodeError) as decode_error:
                    print(f"Error decoding base64 content for {owner}/{repo}/{file_path}: {decode_error}. Will try download_url if available.")
                    # Fallthrough to download_url logic if decoding fails
            
            # Try download_url if content was not present or decoding failed
            if 'download_url' in file_data and file_data['download_url']:
                print(f"Content not decoded or not present, attempting to download from {file_data['download_url']}")
                try:
                    download_response = self._request("GET", file_data['download_url'])
                    return download_response.text # download_url provides raw content
                except requests.exceptions.RequestException as download_e:
                    print(f"Error downloading file from download_url for {owner}/{repo}/{file_path}: {download_e}")
                    return None # Download failed
            
            # If 'content' was not present and 'download_url' was not present or failed
            print(f"No content found and no usable download_url (or download failed) for {owner}/{repo}/{file_path}.")
            return None

        except requests.exceptions.RequestException as e: # For the primary GET request
            print(f"Error reading repository file {owner}/{repo}/{file_path}: {e}")
            return None
        except (KeyError, TypeError, ValueError) as e: # JSON parsing or structure errors
            print(f"Error parsing response for {owner}/{repo}/{file_path}: {e}")
            return None
