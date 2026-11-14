import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

from fairshield.dashboard import Handler


class DashboardV2Tests(unittest.TestCase):
    def test_v2_api_returns_baselines_and_adaptive_policy(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/api/run?scenario=ddos&windows=2&version=2"
            with urlopen(url, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
            policies = {row["policy"] for row in payload["results"]}
            self.assertEqual(policies, {"no_defense", "static_threshold", "fairshield", "adaptive_fairshield_v2"})
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
