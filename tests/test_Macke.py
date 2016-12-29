import unittest

from macke.Macke import Macke


class TestMackeGeneral(unittest.TestCase):

    def test_invalid_file_assertion(self):
        with self.assertRaises(AssertionError):
            Macke("randomFileThatDoesNot.exists")
