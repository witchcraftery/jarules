# jarules_agent/tests/test_local_files.py

import unittest
import os
import shutil # For cleaning up directories
import tempfile # For creating temporary files and directories

# Adjust import path to access the connectors module
import sys
# Assuming the tests are run from the root of the project, or /app
# where 'jarules_agent' is a top-level directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from jarules_agent.connectors import local_files
except ModuleNotFoundError:
    # Fallback if the above path adjustment isn't enough
    # This might happen depending on CWD or how test runner discovers tests
    # For tool environment, running from /app, 'from jarules_agent...' should work.
    # If tests are run directly from /app/jarules_agent/tests, then '../../' is needed to find jarules_agent package.
    # Or if /app is in PYTHONPATH, then 'from jarules_agent...' is fine.
    # The sys.path.insert above should handle the case of running from /app/jarules_agent/tests
    # by adding /app to sys.path
    # Let's try to directly access local_files assuming jarules_agent is in path
    from connectors import local_files # This would work if jarules_agent folder is the CWD


class TestLocalFiles(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory for testing."""
        # Create a temporary directory that will be automatically cleaned up
        self.test_dir = tempfile.mkdtemp()
        # print(f"setUp: Created temp dir {self.test_dir}")


    def tearDown(self):
        """Clean up the temporary directory."""
        # Remove the directory and all its contents
        shutil.rmtree(self.test_dir)
        # print(f"tearDown: Removed temp dir {self.test_dir}")

    def test_list_files(self):
        """Test listing files and directories."""
        # Test empty directory
        self.assertEqual(local_files.list_files(self.test_dir), [])

        # Create some files and a subdirectory
        file1_path = os.path.join(self.test_dir, "file1.txt")
        file2_path = os.path.join(self.test_dir, "file2.txt")
        subdir_path = os.path.join(self.test_dir, "subdir")
        os.makedirs(subdir_path)
        
        with open(file1_path, "w") as f:
            f.write("test1")
        with open(file2_path, "w") as f:
            f.write("test2")

        expected_items = sorted(["file1.txt", "file2.txt", "subdir"])
        self.assertEqual(sorted(local_files.list_files(self.test_dir)), expected_items)

        # Test listing a non-existent directory
        with self.assertRaises(FileNotFoundError):
            local_files.list_files(os.path.join(self.test_dir, "non_existent_dir"))

        # Test listing a file (should raise NotADirectoryError)
        with self.assertRaises(NotADirectoryError):
            local_files.list_files(file1_path)

    def test_read_file(self):
        """Test reading file content."""
        file_path = os.path.join(self.test_dir, "test_read.txt")
        content = "Hello, JaRules!"
        
        with open(file_path, "w") as f:
            f.write(content)
            
        self.assertEqual(local_files.read_file(file_path), content)

        # Test reading a non-existent file
        with self.assertRaises(FileNotFoundError):
            local_files.read_file(os.path.join(self.test_dir, "does_not_exist.txt"))
            
        # Test reading a directory (should raise FileNotFoundError or similar,
        # depending on implementation; our current raises FileNotFoundError because isfile() fails)
        with self.assertRaises(FileNotFoundError): # or IsADirectoryError if explicitly handled
             local_files.read_file(self.test_dir)


    def test_write_file(self):
        """Test writing to a new file and overwriting an existing file."""
        # Test writing to a new file
        new_file_path = os.path.join(self.test_dir, "new_write.txt")
        content1 = "Initial content."
        local_files.write_file(new_file_path, content1)
        
        with open(new_file_path, "r") as f:
            self.assertEqual(f.read(), content1)

        # Test overwriting an existing file
        content2 = "Overwritten content."
        local_files.write_file(new_file_path, content2)
        
        with open(new_file_path, "r") as f:
            self.assertEqual(f.read(), content2)

    def test_write_file_creates_directories(self):
        """Test that write_file creates parent directories if they don't exist."""
        # Path for a file within a new subdirectory structure
        deep_file_path = os.path.join(self.test_dir, "new_parent_dir", "sub_dir", "deep_file.txt")
        content = "Content in a deeply nested file."
        
        local_files.write_file(deep_file_path, content)
        
        self.assertTrue(os.path.exists(deep_file_path))
        with open(deep_file_path, "r") as f:
            self.assertEqual(f.read(), content)
        
        # Check if parent directories were created
        self.assertTrue(os.path.isdir(os.path.join(self.test_dir, "new_parent_dir")))
        self.assertTrue(os.path.isdir(os.path.join(self.test_dir, "new_parent_dir", "sub_dir")))

if __name__ == '__main__':
    unittest.main()
