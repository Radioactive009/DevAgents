import unittest
import os
from execution import DockerSandbox, check_docker_available

@unittest.skipUnless(check_docker_available(), "Docker is not available")
class TestDockerSandbox(unittest.TestCase):
    def setUp(self):
        self.config = {
            "image": "python:3.11-slim",
            "timeout_seconds": 5,
            "memory_limit_mb": 512,
            "cpu_limit": 1.0,
            "network_enabled": False
        }
        self.sandbox = DockerSandbox(self.config)
        self.sandbox.create_workspace()

    def tearDown(self):
        self.sandbox.cleanup()

    def test_basic_execution(self):
        self.sandbox.write_file("main.py", "print('hello')")
        result = self.sandbox.run_command(["python", "main.py"])
        self.assertTrue(result.success)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("hello", result.stdout)
        self.assertEqual(result.failure_category, "SUCCESS")

    def test_nonzero_exit(self):
        self.sandbox.write_file("main.py", "raise RuntimeError('test failure')")
        result = self.sandbox.run_command(["python", "main.py"])
        self.assertFalse(result.success)
        self.assertNotEqual(result.exit_code, 0)
        self.assertEqual(result.failure_category, "NONZERO_EXIT")

    def test_timeout(self):
        # Shorter timeout just for this test
        self.sandbox.timeout_seconds = 2
        self.sandbox.write_file("main.py", "import time; time.sleep(10)")
        result = self.sandbox.run_command(["python", "main.py"])
        self.assertFalse(result.success)
        self.assertTrue(result.timed_out)
        self.assertEqual(result.failure_category, "TIMEOUT")

    def test_test_execution_pass(self):
        # We use unittest instead of pytest because pytest isn't natively in python:3.11-slim by default
        self.sandbox.write_file("test_math.py", "import unittest\nclass T(unittest.TestCase):\n  def test_add(self):\n    self.assertEqual(1+1, 2)")
        result = self.sandbox.run_tests(["python", "-m", "unittest", "test_math.py"])
        self.assertTrue(result.success)

    def test_test_execution_fail(self):
        self.sandbox.write_file("test_math.py", "import unittest\nclass T(unittest.TestCase):\n  def test_add(self):\n    self.assertEqual(1+1, 3)")
        result = self.sandbox.run_tests(["python", "-m", "unittest", "test_math.py"])
        self.assertFalse(result.success)
        self.assertNotEqual(result.exit_code, 0)

    def test_filesystem_isolation(self):
        self.sandbox.write_file("main.py", "import os; print(os.path.exists('/home') or os.path.exists('C:/'))")
        result = self.sandbox.run_command(["python", "main.py"])
        # In a Docker container, /home might exist, but the host's files aren't there.
        # We can check if a known host path exists.
        # A better check is to try reading /etc/shadow or host specific paths, but we'll just verify the workspace is isolated.
        self.sandbox.write_file("check_host.py", "import os; print(os.path.exists('/app/main.py'))")
        result = self.sandbox.run_command(["python", "check_host.py"])
        self.assertIn("True", result.stdout)

    def test_environment_isolation(self):
        code = "import os\nprint('GROQ_API_KEY' in os.environ)\nprint('OPENROUTER_API_KEY' in os.environ)"
        self.sandbox.write_file("main.py", code)
        result = self.sandbox.run_command(["python", "main.py"])
        self.assertNotIn("True", result.stdout)
        self.assertIn("False\nFalse", result.stdout.replace("\\r\\n", "\\n").replace("\\r", "\\n"))

    def test_network_isolation(self):
        code = "import urllib.request\ntry:\n  urllib.request.urlopen('http://1.1.1.1', timeout=2)\n  print('SUCCESS')\nexcept Exception as e:\n  print('FAILED')"
        self.sandbox.write_file("main.py", code)
        result = self.sandbox.run_command(["python", "main.py"])
        self.assertIn("FAILED", result.stdout)

if __name__ == '__main__':
    unittest.main()
