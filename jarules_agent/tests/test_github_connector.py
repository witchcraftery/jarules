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

    # --- Tests for get_branch_sha ---
    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_get_branch_sha_success(self, mock_request):
        """Test successfully retrieving a branch's SHA."""
        mock_response_data = {"object": {"sha": "abcdef1234567890"}}
        mock_request.return_value = self.MockResponse(json_data=mock_response_data, status_code=200)
        
        sha = self.client_no_token.get_branch_sha(self.owner, self.repo, "main")
        
        self.assertEqual(sha, "abcdef1234567890")
        mock_request.assert_called_once_with("GET", f"https://api.github.com/repos/{self.owner}/{self.repo}/git/refs/heads/main")

    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_get_branch_sha_not_found(self, mock_request):
        """Test retrieving SHA for a non-existent branch."""
        mock_request.side_effect = requests.exceptions.HTTPError(
            "404 Client Error: Not Found for url", 
            response=self.MockResponse(json_data={"message": "Not Found"}, status_code=404)
        )
        
        sha = self.client_no_token.get_branch_sha(self.owner, self.repo, "nonexistent-branch")
        
        self.assertIsNone(sha)
        mock_request.assert_called_once_with("GET", f"https://api.github.com/repos/{self.owner}/{self.repo}/git/refs/heads/nonexistent-branch")

    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_get_branch_sha_unexpected_response(self, mock_request):
        """Test handling unexpected JSON structure for branch SHA."""
        mock_response_data = {"unexpected_key": "unexpected_value"} # Missing 'object' or 'sha'
        mock_request.return_value = self.MockResponse(json_data=mock_response_data, status_code=200)

        sha = self.client_no_token.get_branch_sha(self.owner, self.repo, "main")
        self.assertIsNone(sha)

    # --- Tests for create_branch ---
    @patch('jarules_agent.connectors.github_connector.GitHubClient.get_branch_sha')
    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_create_branch_success(self, mock_post_request, mock_get_sha):
        """Test creating a new branch successfully."""
        source_branch_name = "main"
        new_branch_name = "feature-branch"
        test_sha = "abcdef1234567890"
        
        mock_get_sha.return_value = test_sha
        
        mock_post_response_data = {
            "ref": f"refs/heads/{new_branch_name}",
            "node_id": "MDM6UmVmcmVmcy9oZWFkcy9mZWF0dXJlLWJyYW5jaA==",
            "url": f"https://api.github.com/repos/{self.owner}/{self.repo}/git/refs/heads/{new_branch_name}",
            "object": {"sha": test_sha, "type": "commit", "url": "..."}
        }
        mock_post_request.return_value = self.MockResponse(json_data=mock_post_response_data, status_code=201) # 201 Created

        success, result = self.client_no_token.create_branch(self.owner, self.repo, new_branch_name, source_branch_name)

        self.assertTrue(success)
        self.assertEqual(result, mock_post_response_data)
        mock_get_sha.assert_called_once_with(self.owner, self.repo, source_branch_name)
        mock_post_request.assert_called_once_with(
            "POST",
            f"https://api.github.com/repos/{self.owner}/{self.repo}/git/refs",
            json={"ref": f"refs/heads/{new_branch_name}", "sha": test_sha}
        )

    @patch('jarules_agent.connectors.github_connector.GitHubClient.get_branch_sha')
    def test_create_branch_source_branch_not_found(self, mock_get_sha):
        """Test creating a branch when the source branch SHA cannot be found."""
        mock_get_sha.return_value = None # Simulate source branch SHA not found

        success, result = self.client_no_token.create_branch(self.owner, self.repo, "new-feature", "nonexistent-main")

        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertIn("source_branch_not_found_or_sha_retrieval_failed", result.get("reason", ""))
        mock_get_sha.assert_called_once_with(self.owner, self.repo, "nonexistent-main")

    @patch('jarules_agent.connectors.github_connector.GitHubClient.get_branch_sha')
    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_create_branch_already_exists(self, mock_post_request, mock_get_sha):
        """Test creating a branch that already exists (API returns 422)."""
        test_sha = "abcdef1234567890"
        mock_get_sha.return_value = test_sha
        
        # Simulate 422 Unprocessable Entity error
        error_response_json = {"message": "Reference already exists", "documentation_url": "..."}
        mock_post_request.side_effect = requests.exceptions.HTTPError(
            "422 Client Error: Unprocessable Entity for url",
            response=self.MockResponse(json_data=error_response_json, status_code=422)
        )

        success, result = self.client_no_token.create_branch(self.owner, self.repo, "existing-branch", "main")

        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertEqual(result.get("message"), "Reference already exists")
        self.assertEqual(result.get("reason"), "branch_already_exists_or_invalid_sha")
        mock_post_request.assert_called_once()

    @patch('jarules_agent.connectors.github_connector.GitHubClient.get_branch_sha')
    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_create_branch_other_api_error_on_post(self, mock_post_request, mock_get_sha):
        """Test handling other API errors during branch creation POST."""
        test_sha = "abcdef1234567890"
        mock_get_sha.return_value = test_sha

        # Simulate 500 Internal Server Error
        mock_post_request.side_effect = requests.exceptions.HTTPError(
            "500 Server Error: Internal Server Error for url",
            response=self.MockResponse(json_data={"message": "Internal Server Error"}, status_code=500)
        )

        success, result = self.client_no_token.create_branch(self.owner, self.repo, "some-branch", "main")

        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertEqual(result.get("reason"), "http_error")
        self.assertNotEqual(result.get("reason"), "branch_already_exists_or_invalid_sha")

    # --- Tests for commit_files ---
    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    @patch('jarules_agent.connectors.github_connector.GitHubClient.get_branch_sha')
    def test_commit_files_success_single_file(self, mock_get_branch_sha, mock_request):
        """Test successfully committing a single file."""
        owner, repo, branch = self.owner, self.repo, "main"
        file_changes = [{"path": "test.txt", "content": "Hello World"}]
        commit_message = "Add test.txt"

        # 1. Mock get_branch_sha
        mock_get_branch_sha.return_value = "latest_commit_sha_123"

        # Mock responses for the sequence of _request calls
        mock_request.side_effect = [
            # 2. Get Base Tree SHA (from commit details)
            self.MockResponse({"tree": {"sha": "base_tree_sha_456"}}, 200),
            # 3. Create Blob
            self.MockResponse({"sha": "blob_sha_789"}, 201),
            # 4. Create New Tree
            self.MockResponse({"sha": "new_tree_sha_abc"}, 201),
            # 5. Create New Commit
            self.MockResponse({"sha": "new_commit_sha_def", "html_url": "commit_url"}, 201),
            # 6. Update Branch Reference
            self.MockResponse({}, 200) 
        ]

        success, result = self.client_no_token.commit_files(owner, repo, branch, file_changes, commit_message)

        self.assertTrue(success)
        self.assertIsNotNone(result)
        self.assertEqual(result["sha"], "new_commit_sha_def")

        mock_get_branch_sha.assert_called_once_with(owner, repo, branch)
        
        expected_calls = [
            unittest.mock.call("GET", f"https://api.github.com/repos/{owner}/{repo}/git/commits/latest_commit_sha_123"),
            unittest.mock.call("POST", f"https://api.github.com/repos/{owner}/{repo}/git/blobs", 
                               json={"content": "Hello World", "encoding": "utf-8"}),
            unittest.mock.call("POST", f"https://api.github.com/repos/{owner}/{repo}/git/trees", 
                               json={"base_tree": "base_tree_sha_456", 
                                     "tree": [{"path": "test.txt", "mode": "100644", "type": "blob", "sha": "blob_sha_789"}]}),
            unittest.mock.call("POST", f"https://api.github.com/repos/{owner}/{repo}/git/commits", 
                               json={"message": commit_message, "tree": "new_tree_sha_abc", "parents": ["latest_commit_sha_123"]}),
            unittest.mock.call("PATCH", f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}", 
                               json={"sha": "new_commit_sha_def"})
        ]
        self.assertEqual(mock_request.call_args_list, expected_calls)


    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    @patch('jarules_agent.connectors.github_connector.GitHubClient.get_branch_sha')
    def test_commit_files_success_multiple_files(self, mock_get_branch_sha, mock_request):
        """Test successfully committing multiple files."""
        owner, repo, branch = self.owner, self.repo, "develop"
        file_changes = [
            {"path": "file1.txt", "content": "Content 1"},
            {"path": "docs/file2.md", "content": "# Markdown"}
        ]
        commit_message = "Add multiple files"

        mock_get_branch_sha.return_value = "latest_commit_sha_xyz"
        
        mock_request.side_effect = [
            self.MockResponse({"tree": {"sha": "base_tree_sha_xyz"}}, 200), # Get base tree
            self.MockResponse({"sha": "blob_sha_file1"}, 201),             # Create blob for file1
            self.MockResponse({"sha": "blob_sha_file2"}, 201),             # Create blob for file2
            self.MockResponse({"sha": "new_tree_sha_pqr"}, 201),            # Create new tree
            self.MockResponse({"sha": "new_commit_sha_stu", "html_url": "url"}, 201), # Create new commit
            self.MockResponse({}, 200)                                      # Update ref
        ]

        success, result = self.client_no_token.commit_files(owner, repo, branch, file_changes, commit_message)

        self.assertTrue(success)
        self.assertEqual(result["sha"], "new_commit_sha_stu")

        expected_tree_elements = [
            {"path": "file1.txt", "mode": "100644", "type": "blob", "sha": "blob_sha_file1"},
            {"path": "docs/file2.md", "mode": "100644", "type": "blob", "sha": "blob_sha_file2"}
        ]
        # Check the tree creation call specifically for the tree elements
        # The fourth call to mock_request is tree creation (index 3)
        actual_tree_call = mock_request.call_args_list[3] # POST for tree
        # Extract the json parameter from the call kwargs
        actual_tree_json = actual_tree_call.kwargs['json'] if 'json' in actual_tree_call.kwargs else actual_tree_call[1]['json']
        self.assertEqual(actual_tree_json['tree'], expected_tree_elements)


    @patch('jarules_agent.connectors.github_connector.GitHubClient.get_branch_sha')
    def test_commit_files_branch_not_found(self, mock_get_branch_sha):
        """Test commit fails if branch SHA cannot be retrieved."""
        mock_get_branch_sha.return_value = None
        
        success, result = self.client_no_token.commit_files(self.owner, self.repo, "ghost-branch", [], "Msg")
        
        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertEqual(result["step"], "get_branch_sha")

    @patch('jarules_agent.connectors.github_connector.GitHubClient.get_branch_sha')
    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_commit_files_error_creating_blob(self, mock_request, mock_get_branch_sha):
        """Test commit fails if blob creation fails."""
        mock_get_branch_sha.return_value = "latest_commit_sha_123"
        mock_request.side_effect = [
            self.MockResponse({"tree": {"sha": "base_tree_sha_456"}}, 200), # Get base tree
            requests.exceptions.HTTPError("Error creating blob", response=self.MockResponse({}, 500)) # Blob creation fails
        ]
        
        file_changes = [{"path": "fail.txt", "content": "..."}]
        success, result = self.client_no_token.commit_files(self.owner, self.repo, "main", file_changes, "Msg")

        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertEqual(result["step"], "create_blob_request")

    @patch('jarules_agent.connectors.github_connector.GitHubClient.get_branch_sha')
    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_commit_files_error_creating_tree(self, mock_request, mock_get_branch_sha):
        """Test commit fails if tree creation fails."""
        mock_get_branch_sha.return_value = "latest_commit_sha_123"
        mock_request.side_effect = [
            self.MockResponse({"tree": {"sha": "base_tree_sha_456"}}, 200),
            self.MockResponse({"sha": "blob_sha_789"}, 201), # Blob creation
            requests.exceptions.HTTPError("Error creating tree", response=self.MockResponse({}, 500)) # Tree creation fails
        ]

        file_changes = [{"path": "ok.txt", "content": "..."}]
        success, result = self.client_no_token.commit_files(self.owner, self.repo, "main", file_changes, "Msg")

        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertEqual(result["step"], "create_tree_request")

    @patch('jarules_agent.connectors.github_connector.GitHubClient.get_branch_sha')
    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_commit_files_error_creating_commit(self, mock_request, mock_get_branch_sha):
        """Test commit fails if commit creation fails."""
        mock_get_branch_sha.return_value = "latest_commit_sha_123"
        mock_request.side_effect = [
            self.MockResponse({"tree": {"sha": "base_tree_sha_456"}}, 200),
            self.MockResponse({"sha": "blob_sha_789"}, 201),
            self.MockResponse({"sha": "new_tree_sha_abc"}, 201), # Tree creation
            requests.exceptions.HTTPError("Error creating commit", response=self.MockResponse({}, 500)) # Commit creation fails
        ]
        file_changes = [{"path": "ok.txt", "content": "..."}]
        success, result = self.client_no_token.commit_files(self.owner, self.repo, "main", file_changes, "Msg")

        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertEqual(result["step"], "create_commit_request")

    @patch('jarules_agent.connectors.github_connector.GitHubClient.get_branch_sha')
    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_commit_files_error_updating_ref(self, mock_request, mock_get_branch_sha):
        """Test commit fails if reference update fails."""
        mock_get_branch_sha.return_value = "latest_commit_sha_123"
        mock_request.side_effect = [
            self.MockResponse({"tree": {"sha": "base_tree_sha_456"}}, 200),
            self.MockResponse({"sha": "blob_sha_789"}, 201),
            self.MockResponse({"sha": "new_tree_sha_abc"}, 201),
            self.MockResponse({"sha": "new_commit_sha_def"}, 201), # Commit creation
            requests.exceptions.HTTPError("Error updating ref", response=self.MockResponse({}, 422)) # Ref update fails (e.g. not fast-forward)
        ]
        file_changes = [{"path": "ok.txt", "content": "..."}]
        success, result = self.client_no_token.commit_files(self.owner, self.repo, "main", file_changes, "Msg")
        
        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertEqual(result["step"], "update_ref_http_error")
        self.assertEqual(result["reason"], "not_a_fast_forward_or_other_issue")

    # --- Tests for create_pull_request ---
    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_create_pull_request_success(self, mock_request):
        """Test creating a pull request successfully."""
        owner, repo = self.owner, self.repo
        head_branch, base_branch = "feature-branch", "main"
        title, body = "New Feature", "This PR adds an amazing new feature."
        
        expected_pr_data = {
            "html_url": f"https://github.com/{owner}/{repo}/pull/1",
            "id": 123,
            "title": title,
            "number": 1
        }
        mock_request.return_value = self.MockResponse(json_data=expected_pr_data, status_code=201)

        success, result = self.client_no_token.create_pull_request(owner, repo, head_branch, base_branch, title, body)

        self.assertTrue(success)
        self.assertEqual(result, expected_pr_data)
        mock_request.assert_called_once_with(
            "POST",
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            json={"title": title, "head": head_branch, "base": base_branch, "body": body}
        )

    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_create_pull_request_branch_not_found(self, mock_request):
        """Test PR creation when a branch is not found (422 error)."""
        error_response_json = {
            "message": "Validation Failed", 
            "errors": [{"resource": "PullRequest", "code": "invalid", "field": "head", "message": "Head branch not_found_branch does not exist"}]
        }
        mock_request.side_effect = requests.exceptions.HTTPError(
            "422 Client Error: Unprocessable Entity",
            response=self.MockResponse(json_data=error_response_json, status_code=422)
        )
        
        success, result = self.client_no_token.create_pull_request(self.owner, self.repo, "not_found_branch", "main", "Title")
        
        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertEqual(result.get("reason"), "branch_not_found")
        self.assertIn("Head branch not_found_branch does not exist", result.get("specific_error", ""))

    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_create_pull_request_no_diff(self, mock_request):
        """Test PR creation when there's no difference between branches (422 error)."""
        error_response_json = {
            "message": "Validation Failed",
            "errors": [{"resource": "PullRequest", "code": "custom", "message": "No commits between main and main"}]
        }
        mock_request.side_effect = requests.exceptions.HTTPError(
            "422 Client Error: Unprocessable Entity",
            response=self.MockResponse(json_data=error_response_json, status_code=422)
        )

        success, result = self.client_no_token.create_pull_request(self.owner, self.repo, "main", "main", "No Diff PR")

        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertEqual(result.get("reason"), "no_diff")
        self.assertIn("No commits between main and main", result.get("specific_error", ""))


    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_create_pull_request_already_exists(self, mock_request):
        """Test PR creation when a PR for the head branch already exists (422 error)."""
        error_response_json = {
            "message": "Validation Failed",
            "errors": [{"resource": "PullRequest", "code": "custom", "message": "A pull request already exists for testowner:feature-branch."}]
        }
        mock_request.side_effect = requests.exceptions.HTTPError(
            "422 Client Error: Unprocessable Entity",
            response=self.MockResponse(json_data=error_response_json, status_code=422)
        )

        success, result = self.client_no_token.create_pull_request(self.owner, self.repo, "feature-branch", "main", "Existing PR")

        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertEqual(result.get("reason"), "pr_already_exists")
        self.assertIn("A pull request already exists", result.get("specific_error", ""))
        
    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_create_pull_request_generic_422_error(self, mock_request):
        """Test PR creation with a generic 422 error (no specific known message)."""
        error_response_json = {
            "message": "Validation Failed",
            "errors": [{"resource": "PullRequest", "code": "custom", "message": "Some other validation problem."}]
        }
        mock_request.side_effect = requests.exceptions.HTTPError(
            "422 Client Error: Unprocessable Entity",
            response=self.MockResponse(json_data=error_response_json, status_code=422)
        )

        success, result = self.client_no_token.create_pull_request(self.owner, self.repo, "head", "base", "Generic 422")

        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertEqual(result.get("reason"), "unprocessable_entity_general")
        self.assertIn("Some other validation problem.", result.get("specific_error", ""))


    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_create_pull_request_other_api_error(self, mock_request):
        """Test PR creation with a non-422 HTTP error (e.g., 500)."""
        mock_request.side_effect = requests.exceptions.HTTPError(
            "500 Server Error: Internal Server Error",
            response=self.MockResponse(json_data={"message": "Server Error"}, status_code=500)
        )
        
        success, result = self.client_no_token.create_pull_request(self.owner, self.repo, "head", "base", "Server Error PR")
        
        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertEqual(result.get("reason"), "http_error_general") # General HTTP error, not specific 422
        self.assertEqual(result.get("message"), "Server Error")

    @patch('jarules_agent.connectors.github_connector.GitHubClient._request')
    def test_create_pull_request_request_exception(self, mock_request):
        """Test PR creation when a requests.exceptions.RequestException occurs."""
        mock_request.side_effect = requests.exceptions.Timeout("Connection timed out")

        success, result = self.client_no_token.create_pull_request(self.owner, self.repo, "head", "base", "Timeout PR")

        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertEqual(result.get("reason"), "request_exception")
        self.assertIn("Connection timed out", result.get("error", ""))


if __name__ == '__main__':
    unittest.main()
