
import builtins
import importlib
import os
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")

from config import Config


class SessionPersistenceTestCase(unittest.TestCase):
    def test_session_is_configured_for_persistent_login(self):
        self.assertTrue(Config.SESSION_PERMANENT)
        self.assertGreater(Config.PERMANENT_SESSION_LIFETIME.total_seconds(), 0)


class CloudinaryImportTestCase(unittest.TestCase):
    def test_cloudinary_utils_imports_without_cloudinary_package(self):
        sys.modules.pop("utils.cloudinary_utils", None)
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "cloudinary" or name.startswith("cloudinary."):
                raise ImportError("simulated missing cloudinary")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            module = importlib.import_module("utils.cloudinary_utils")

        self.assertIsNotNone(module)
        self.assertTrue(hasattr(module, "upload_image"))
        self.assertTrue(callable(module.upload_image))


if __name__ == "__main__":
    unittest.main()
