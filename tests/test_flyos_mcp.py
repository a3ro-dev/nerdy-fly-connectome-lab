import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from flyos.mcp_server import Server
from flyos.mcp_client import MCPStdioClient


ROOT = Path(__file__).parents[1]


class MCPServerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.root = root
        (root / "web/data").mkdir(parents=True)
        shutil.copy2(ROOT / "web/data/male_common_graph.json", root / "web/data/male_common_graph.json")
        self.server = Server(root, "identity", 3)

    def tearDown(self):
        self.temp.cleanup()

    def test_lifecycle_and_tools(self):
        initialized = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}})
        self.assertIn("tools", initialized["result"]["capabilities"])
        listed = self.server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        names = {tool["name"] for tool in listed["result"]["tools"]}
        self.assertIn("fly_create_task", names)
        self.assertIn("fly_get_trace", names)

    def test_tool_calls_are_structured_and_traced(self):
        created = self.server.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "fly_create_task", "arguments": {"task": "verify a file", "run_id": "mcp-test"}}})
        self.assertFalse(created["result"]["isError"])
        routed = self.server.handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "fly_route", "arguments": {"requested": "verification"}}})
        self.assertEqual(routed["result"]["structuredContent"]["requested"], "verification")
        self.assertTrue(self.server.runtime.trace)

    def test_unittest_verification_is_fixed_and_objective(self):
        self.server.call("fly_create_task", {"task": "verify tests", "run_id": "verify-test"})
        result = self.server.call("fly_act", {"result": {"state_changed": True, "verification_type": "unittest"}})
        self.assertIn("reward", result)
        event = self.server.runtime.trace[-1]
        self.assertIn("verification_returncode", event["result"])

    def test_stdio_client_consumes_configured_mcp_server(self):
        with MCPStdioClient([sys.executable, "-m", "flyos.mcp_server", "--root", str(self.root), "--condition", "identity"], ROOT) as client:
            names = {tool["name"] for tool in client.list_tools()}
            self.assertIn("fly_route", names)
            result = client.call_tool("fly_create_task", {"task": "client smoke test", "run_id": "client-test"})
            self.assertFalse(result["isError"])


if __name__ == "__main__":
    unittest.main()
