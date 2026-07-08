import os
import unittest

os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")

from config import Config


class SessionPersistenceTestCase(unittest.TestCase):
    def test_session_is_configured_for_persistent_login(self):
        self.assertTrue(Config.SESSION_PERMANENT)
        self.assertGreater(Config.PERMANENT_SESSION_LIFETIME.total_seconds(), 0)


if __name__ == "__main__":
    unittest.main()
