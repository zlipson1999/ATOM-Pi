import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class KnowledgeIndexTests(unittest.TestCase):
    def test_index_tracks_add_change_delete(self):
        with tempfile.TemporaryDirectory() as drive, tempfile.TemporaryDirectory() as index:
            with patch.dict(os.environ, {"LIBRARY_INDEX_DIR": index}):
                import importlib

                import atom_knowledge

                atom_knowledge = importlib.reload(atom_knowledge)
                root = Path(drive)
                doc = root / "note.txt"
                doc.write_text("alpha fact", encoding="utf-8")
                self.assertIn("1 new", atom_knowledge.index_documents(root))
                self.assertTrue(atom_knowledge.doc_search(root, "alpha"))
                doc.write_text("beta fact changed", encoding="utf-8")
                self.assertIn("updated 1", atom_knowledge.index_documents(root))
                self.assertTrue(atom_knowledge.doc_search(root, "beta"))
                doc.unlink()
                self.assertIn("removed 1", atom_knowledge.index_documents(root))
                self.assertFalse(atom_knowledge.doc_search(root, "beta"))


if __name__ == "__main__":
    unittest.main()

