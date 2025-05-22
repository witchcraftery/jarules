# jarules_agent/tests/test_github_connector.py

import unittest
from unittest.mock import patch, MagicMock
import base64
import requests # For requests.exceptions.RequestException

# Adjust import path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from jarules_agent.connectors.github_connector import GitHubClient
except ModuleNotFoundError:
    # This path adjustment might be necessary if the above doesn't work in all execution contexts
    # e.g. if CWD is 'jarules_agent'
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from connectors.github_connector import GitHubClient


class TestGitHubClient(unittest.TestCase):

    def setUp(self):
        """Set up GitHubClient instances for testing."""
        self.client_no_token = GitHubClient()
        self.client_with_token = GitHubClient(token="test_token_123")
        self.owner = "testowner"
        self.repo = "testrepo"

    # Mocked response class to simulate requests.Response
    class MockResponse:
        def __init__(self, json_data, status_code, text_data="", content_data=None):
            self.json_data = json_data
            self.status_code = status_code
            self.text = text_data
            self.content = content_data if content_data is not None else text_data.encode('utf-8')

        def json(self):
            return self.json_data

        def raise_for_status(self):
            if self.status_code >= 400:
                http_error_msg = f"{self.status_code} Client Error: Error for url"
                raise requests.exceptions.HTTPError(http_error_msg, response=self)

    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_list_repo_files_success(self, mock_request):
        """Test listing repository files successfully."""
        mock_api_response = [
            {'name': 'file1.py', 'type': 'file'},
            {'name': 'mydir', 'type': 'dir'},
            {'name': '.env', 'type': 'file'}
        ]
        mock_request.return_value = self.MockResponse(json_data=mock_api_response, status_code=200)
        
        expected_files = ['file1.py', 'mydir', '.env']
        files = self.client_no_token.list_repo_files(self.owner, self.repo, "some/path")
        
        self.assertEqual(files, expected_files)
        mock_request.assert_called_once_with("GET", f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/some/path")

    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_list_repo_files_api_error(self, mock_request):
        """Test listing repository files when API returns an error."""
        # Simulate an HTTP error by having _request raise it (as it would if response.raise_for_status() was called)
        mock_request.side_effect = requests.exceptions.HTTPError("404 Client Error: Not Found for url", response=self.MockResponse(json_data={}, status_code=404))
        
        files = self.client_no_token.list_repo_files(self.owner, self.repo, "nonexistent/path")
        self.assertEqual(files, []) # Expect empty list on error as per current implementation
        mock_request.assert_called_once_with("GET", f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/nonexistent/path")

    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_list_repo_files_path_is_file(self, mock_request):
        """Test listing repository files when the path points to a file, not a directory."""
        # GitHub API returns a single JSON object if the path is a file
        mock_api_response = {'name': 'file1.py', 'type': 'file', 'content': 'cHJpbnQoImhpIik='}
        mock_request.return_value = self.MockResponse(json_data=mock_api_response, status_code=200)
        
        files = self.client_no_token.list_repo_files(self.owner, self.repo, "some/file1.py")
        self.assertEqual(files, []) # Expect empty list as it's not a directory listing
        mock_request.assert_called_once_with("GET", f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/some/file1.py")

    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_read_repo_file_success(self, mock_request):
        """Test reading a file's content successfully."""
        file_content = "print('Hello, JaRules!')"
        encoded_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')
        mock_api_response = {
            'name': 'script.py',
            'type': 'file',
            'content': encoded_content,
            'encoding': 'base64',
            'download_url': 'http://example.com/download/script.py'
        }
        mock_request.return_value = self.MockResponse(json_data=mock_api_response, status_code=200)
        
        content = self.client_no_token.read_repo_file(self.owner, self.repo, "path/to/script.py")
        self.assertEqual(content, file_content)
        mock_request.assert_called_once_with("GET", f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/path/to/script.py")

    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_read_repo_file_uses_download_url(self, mock_request):
        """Test reading file content using download_url if 'content' is missing or problematic."""
        # First call to /contents endpoint, simulating a response without 'content' or with problematic content
        # For simplicity, let's assume 'content' is missing and 'download_url' is present.
        # The actual implementation might try to decode first, then fallback.
        # Our mock for this test simulates the case where download_url is used.
        
        file_content_from_download = "Raw content from download URL"
        
        # Response for the initial /contents/{file_path} call
        contents_api_response = {
            'name': 'large_file.txt',
            'type': 'file',
            # 'content': '...', # Assume content is too large or not directly provided
            'download_url': f'https://api.github.com/repos/{self.owner}/{self.repo}/raw/path/to/large_file.txt'
        }
        
        # Response for the download_url call
        download_url_response = self.MockResponse(json_data=None, status_code=200, text_data=file_content_from_download)

        # Configure mock_request to return different responses based on the URL
        def side_effect_func(method, url, **kwargs):
            if "contents/path/to/large_file.txt" in url:
                return self.MockResponse(json_data=contents_api_response, status_code=200)
            elif "raw/path/to/large_file.txt" in url:
                return download_url_response
            raise ValueError(f"Unexpected URL: {url}")

        mock_request.side_effect = side_effect_func
        
        content = self.client_no_token.read_repo_file(self.owner, self.repo, "path/to/large_file.txt")
        self.assertEqual(content, file_content_from_download)
        
        self.assertEqual(mock_request.call_count, 2)
        # Check first call
        mock_request.assert_any_call("GET", f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/path/to/large_file.txt")
        # Check second call (to download_url)
        mock_request.assert_any_call("GET", contents_api_response['download_url'])


    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_read_repo_file_not_found(self, mock_request):
        """Test reading a non-existent file."""
        mock_request.side_effect = requests.exceptions.HTTPError("404 Client Error", response=self.MockResponse(json_data={}, status_code=404))
        
        content = self.client_no_token.read_repo_file(self.owner, self.repo, "nonexistent/file.txt")
        self.assertIsNone(content)
        mock_request.assert_called_once_with("GET", f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/nonexistent/file.txt")

    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_read_repo_file_path_is_directory(self, mock_request):
        """Test reading a path that is a directory, not a file."""
        # GitHub API returns a list if the path is a directory
        mock_api_response = [{'name': 'item1'}, {'name': 'item2'}]
        mock_request.return_value = self.MockResponse(json_data=mock_api_response, status_code=200)

        content = self.client_no_token.read_repo_file(self.owner, self.repo, "path/to/directory")
        self.assertIsNone(content)
        mock_request.assert_called_once_with("GET", f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/path/to/directory")


    @patch('requests.request') # Patching the actual requests.request call used by _request
    def test_authentication_header(self, mock_actual_request_call):
        """Test that the Authorization header is correctly set when a token is provided."""
        mock_actual_request_call.return_value = self.MockResponse(json_data=[{'name': 'file.txt'}], status_code=200)
        
        # Use the client initialized with a token
        self.client_with_token.list_repo_files(self.owner, self.repo, "some/path")
        
        # Check the headers passed to requests.request
        # The first argument to requests.request is method, second is url, then kwargs
        # We need to inspect the 'headers' kwarg.
        called_args, called_kwargs = mock_actual_request_call.call_args
        self.assertIn('headers', called_kwargs)
        self.assertEqual(called_kwargs['headers']['Authorization'], "token test_token_123")
        self.assertEqual(called_kwargs['headers']['Accept'], "application/vnd.github.v3+json")

    @patch('requests.request')
    def test_no_authentication_header_if_no_token(self, mock_actual_request_call):
        """Test that Authorization header is not set if no token is provided."""
        mock_actual_request_call.return_value = self.MockResponse(json_data=[{'name': 'file.txt'}], status_code=200)

        self.client_no_token.list_repo_files(self.owner, self.repo, "some/path")
        
        called_args, called_kwargs = mock_actual_request_call.call_args
        self.assertIn('headers', called_kwargs)
        self.assertNotIn('Authorization', called_kwargs['headers'])
        self.assertEqual(called_kwargs['headers']['Accept'], "application/vnd.github.v3+json")


if __name__ == '__main__':
    unittest.main()
