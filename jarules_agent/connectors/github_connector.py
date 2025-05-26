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

    def get_branch_sha(self, owner: str, repo: str, branch_name: str) -> Optional[str]:
        """
        Retrieves the SHA of the latest commit on a given branch.

        Args:
            owner: The owner of the repository.
            repo: The name of the repository.
            branch_name: The name of the branch.

        Returns:
            The SHA of the branch's HEAD, or None if an error occurs or branch not found.
        """
        # GitHub API endpoint to get a specific branch can also be /repos/{owner}/{repo}/branches/{branch_name}
        # which provides more info, but for just the SHA, /git/ref/heads/{branch_name} is more direct.
        url = f"{self.BASE_API_URL}/repos/{owner}/{repo}/git/refs/heads/{branch_name.lstrip('/')}"
        try:
            response = self._request("GET", url)
            branch_info = response.json()
            if isinstance(branch_info, dict) and 'object' in branch_info and 'sha' in branch_info['object']:
                return branch_info['object']['sha']
            else:
                # This case might also cover when a branch is not found, GitHub API for refs returns 404.
                # _request would raise HTTPError for 404, so this part might only be reached if response is 200 but unexpected format.
                print(f"Unexpected response structure for branch SHA {owner}/{repo}/refs/heads/{branch_name}: {branch_info}")
                return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"Branch '{branch_name}' not found in {owner}/{repo}.")
            else:
                # Logged by _request, but good to note here.
                print(f"HTTP error fetching SHA for branch '{branch_name}' in {owner}/{repo}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            # Logged by _request
            print(f"Request error fetching SHA for branch '{branch_name}' in {owner}/{repo}: {e}")
            return None
        except (KeyError, TypeError, ValueError) as e: # JSON parsing or structure errors
            print(f"Error parsing response for branch SHA {owner}/{repo}/refs/heads/{branch_name}: {e}")
            return None

    def create_branch(self, owner: str, repo: str, new_branch_name: str, source_branch_name: str = 'main') -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Creates a new branch in the repository.

        Args:
            owner: The owner of the repository.
            repo: The name of the repository.
            new_branch_name: The name for the new branch.
            source_branch_name: The name of the branch from which to create the new one. Defaults to 'main'.

        Returns:
            A tuple: (success_status, data).
            If successful, (True, dict_of_new_branch_ref_details).
            If failed, (False, dict_with_error_message).
        """
        source_sha = self.get_branch_sha(owner, repo, source_branch_name)
        if not source_sha:
            error_msg = f"Could not retrieve SHA for source branch '{source_branch_name}'."
            print(error_msg)
            return False, {"error": error_msg, "reason": "source_branch_not_found_or_sha_retrieval_failed"}

        url = f"{self.BASE_API_URL}/repos/{owner}/{repo}/git/refs"
        payload = {
            "ref": f"refs/heads/{new_branch_name.lstrip('/')}",
            "sha": source_sha
        }
        try:
            response = self._request("POST", url, json=payload)
            # Successful creation typically returns 201 Created
            print(f"Branch '{new_branch_name}' created successfully in {owner}/{repo}. Response: {response.json()}")
            return True, response.json()
        except requests.exceptions.HTTPError as e:
            error_details = {"error": str(e)}
            try: # Try to get more specific error details from response
                error_details.update(e.response.json())
            except ValueError: # If response is not JSON
                error_details["response_text"] = e.response.text

            if e.response.status_code == 422: # Unprocessable Entity - often means branch already exists
                print(f"Failed to create branch '{new_branch_name}' in {owner}/{repo}. It might already exist or SHA is invalid. Details: {error_details}")
                error_details["reason"] = "branch_already_exists_or_invalid_sha"
            else:
                print(f"HTTP error creating branch '{new_branch_name}' in {owner}/{repo}. Details: {error_details}")
                error_details["reason"] = "http_error"
            return False, error_details
        except requests.exceptions.RequestException as e: # Network errors, etc.
            # Logged by _request
            error_msg = f"Request error creating branch '{new_branch_name}' in {owner}/{repo}: {e}"
            print(error_msg)
            return False, {"error": error_msg, "reason": "request_exception"}
        except Exception as e: # Catch any other unexpected errors
            error_msg = f"An unexpected error occurred while creating branch '{new_branch_name}': {e}"
            print(error_msg)
            return False, {"error": error_msg, "reason": "unknown_error"}

    def commit_files(self, owner: str, repo: str, branch_name: str, file_changes: List[Dict[str, str]], commit_message: str) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Commits multiple file changes to a specified branch.

        Args:
            owner: The owner of the repository.
            repo: The name of the repository.
            branch_name: The branch to commit to.
            file_changes: A list of dictionaries, each with "path" and "content" keys.
                          Example: [{"path": "src/main.py", "content": "print('hello')"}]
            commit_message: The message for the commit.

        Returns:
            A tuple: (success_status, data).
            If successful, (True, dict_of_new_commit_details).
            If failed, (False, dict_with_error_message).
        """
        # 1. Get Branch Reference (latest commit SHA on the branch)
        latest_commit_sha = self.get_branch_sha(owner, repo, branch_name)
        if not latest_commit_sha:
            return False, {"error": f"Branch '{branch_name}' not found or SHA could not be retrieved.", "step": "get_branch_sha"}

        # 2. Get Base Tree SHA from the latest commit
        commit_url = f"{self.BASE_API_URL}/repos/{owner}/{repo}/git/commits/{latest_commit_sha}"
        try:
            commit_data_response = self._request("GET", commit_url)
            commit_data = commit_data_response.json()
            base_tree_sha = commit_data.get("tree", {}).get("sha")
            if not base_tree_sha:
                return False, {"error": "Could not retrieve base tree SHA from commit.", "step": "get_base_tree_sha", "details": commit_data}
        except requests.exceptions.RequestException as e:
            return False, {"error": f"API error getting commit details for SHA '{latest_commit_sha}': {e}", "step": "get_base_tree_sha_request"}
        except (KeyError, TypeError, ValueError) as e:
            return False, {"error": f"Error parsing commit details response: {e}", "step": "get_base_tree_sha_parse"}

        # 3. Create Blobs for each file change
        blob_shas = []
        blobs_url = f"{self.BASE_API_URL}/repos/{owner}/{repo}/git/blobs"
        for file_change in file_changes:
            payload = {
                "content": file_change["content"], # Already a string, GitHub API expects UTF-8 string for content
                "encoding": "utf-8" # GitHub default is utf-8 if content is string
            }
            try:
                blob_response = self._request("POST", blobs_url, json=payload)
                blob_data = blob_response.json()
                blob_shas.append({"path": file_change["path"], "sha": blob_data["sha"]})
            except requests.exceptions.RequestException as e:
                return False, {"error": f"API error creating blob for file '{file_change['path']}': {e}", "step": "create_blob_request", "file_path": file_change['path']}
            except (KeyError, TypeError, ValueError) as e:
                 return False, {"error": f"Error parsing blob creation response for '{file_change['path']}': {e}", "step": "create_blob_parse", "file_path": file_change['path']}

        # 4. Create New Tree
        tree_elements = []
        for blob_info in blob_shas:
            tree_elements.append({
                "path": blob_info["path"],
                "mode": "100644",  # normal file
                "type": "blob",
                "sha": blob_info["sha"]
            })
        
        trees_url = f"{self.BASE_API_URL}/repos/{owner}/{repo}/git/trees"
        tree_payload = {
            "base_tree": base_tree_sha,
            "tree": tree_elements
        }
        try:
            new_tree_response = self._request("POST", trees_url, json=tree_payload)
            new_tree_data = new_tree_response.json()
            new_tree_sha = new_tree_data.get("sha")
            if not new_tree_sha:
                return False, {"error": "Could not retrieve new tree SHA from response.", "step": "create_tree_get_sha", "details": new_tree_data}
        except requests.exceptions.RequestException as e:
            return False, {"error": f"API error creating new tree: {e}", "step": "create_tree_request"}
        except (KeyError, TypeError, ValueError) as e:
            return False, {"error": f"Error parsing new tree response: {e}", "step": "create_tree_parse"}

        # 5. Create New Commit
        new_commit_url = f"{self.BASE_API_URL}/repos/{owner}/{repo}/git/commits"
        commit_payload = {
            "message": commit_message,
            "tree": new_tree_sha,
            "parents": [latest_commit_sha]
        }
        try:
            new_commit_response = self._request("POST", new_commit_url, json=commit_payload)
            new_commit_data = new_commit_response.json()
            new_commit_sha = new_commit_data.get("sha")
            if not new_commit_sha: # Should not happen if status is 201, but check anyway
                 return False, {"error": "New commit created but SHA not found in response.", "step": "create_commit_get_sha", "details": new_commit_data}
        except requests.exceptions.RequestException as e:
            return False, {"error": f"API error creating new commit: {e}", "step": "create_commit_request"}
        except (KeyError, TypeError, ValueError) as e:
            return False, {"error": f"Error parsing new commit response: {e}", "step": "create_commit_parse"}

        # 6. Update Branch Reference (Fast-Forward)
        ref_update_url = f"{self.BASE_API_URL}/repos/{owner}/{repo}/git/refs/heads/{branch_name.lstrip('/')}"
        ref_payload = {
            "sha": new_commit_sha
            # "force": False # Default is false, only fast-forwards. True would allow overwriting.
        }
        try:
            self._request("PATCH", ref_update_url, json=ref_payload)
            # Success here means the branch points to the new commit.
            # The new_commit_data from step 5 is the most relevant data to return.
            print(f"Successfully committed to {owner}/{repo}/{branch_name}. New commit SHA: {new_commit_sha}")
            return True, new_commit_data
        except requests.exceptions.HTTPError as e:
            # This can happen if the branch was updated by someone else in the meantime (not a fast-forward)
            error_details = {"error": str(e), "step": "update_ref_http_error"}
            try:
                error_details.update(e.response.json())
            except ValueError:
                error_details["response_text"] = e.response.text
            if e.response.status_code == 422: # Unprocessable Entity
                 error_details["reason"] = "not_a_fast_forward_or_other_issue"
            print(f"HTTP error updating branch reference for '{branch_name}': {error_details}")
            return False, error_details
        except requests.exceptions.RequestException as e:
            return False, {"error": f"API error updating branch reference for '{branch_name}': {e}", "step": "update_ref_request"}

    def create_pull_request(self, owner: str, repo: str, head_branch: str, base_branch: str, title: str, body: str = '') -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Creates a new pull request.

        Args:
            owner: The owner of the repository.
            repo: The name of the repository.
            head_branch: The name of the branch where your changes are implemented.
            base_branch: The name of the branch you want the changes pulled into.
            title: The title of the pull request.
            body: The contents of the pull request. Defaults to an empty string.

        Returns:
            A tuple: (success_status, data).
            If successful, (True, dict_of_pull_request_details).
            If failed, (False, dict_with_error_message).
        """
        url = f"{self.BASE_API_URL}/repos/{owner}/{repo}/pulls"
        payload = {
            "title": title,
            "head": head_branch,
            "base": base_branch,
            "body": body
        }
        try:
            response = self._request("POST", url, json=payload)
            # Successful PR creation typically returns 201 Created
            pr_data = response.json()
            print(f"Pull request '{title}' created successfully in {owner}/{repo}. URL: {pr_data.get('html_url')}")
            return True, pr_data
        except requests.exceptions.HTTPError as e:
            error_details = {"error": str(e), "step": "create_pull_request_http_error"}
            try:
                response_json = e.response.json()
                error_details.update(response_json)
                # Check for specific error messages if available in response_json.errors
                if "errors" in response_json and isinstance(response_json["errors"], list):
                    first_error = response_json["errors"][0]
                    if isinstance(first_error, dict):
                        if "message" in first_error:
                            # Example: "A pull request already exists for..."
                            # Example: "No commits between 'base_branch' and 'head_branch'"
                            # Example: "Head branch or Base branch does not exist"
                            error_details["specific_error"] = first_error["message"]
                            if "A pull request already exists" in first_error["message"]:
                                error_details["reason"] = "pr_already_exists"
                            elif "No commits between" in first_error["message"]:
                                error_details["reason"] = "no_diff"
                            elif "does not exist" in first_error["message"]:
                                 error_details["reason"] = "branch_not_found"

            except ValueError: # If response is not JSON
                error_details["response_text"] = e.response.text
            
            if e.response.status_code == 422: # Unprocessable Entity
                # Reason might have been set above based on specific error message
                if "reason" not in error_details:
                    error_details["reason"] = "unprocessable_entity_general"
                print(f"Failed to create pull request '{title}' in {owner}/{repo} (422 Unprocessable Entity). Details: {error_details}")
            else:
                print(f"HTTP error creating pull request '{title}' in {owner}/{repo}. Details: {error_details}")
                error_details["reason"] = "http_error_general"
            return False, error_details
        except requests.exceptions.RequestException as e: # Network errors, etc.
            error_msg = f"Request error creating pull request '{title}' in {owner}/{repo}: {e}"
            print(error_msg)
            return False, {"error": error_msg, "reason": "request_exception", "step": "create_pull_request_request_exception"}
        except Exception as e: # Catch any other unexpected errors
            error_msg = f"An unexpected error occurred while creating pull request '{title}': {e}"
            print(error_msg)
            return False, {"error": error_msg, "reason": "unknown_error", "step": "create_pull_request_unknown_error"}
