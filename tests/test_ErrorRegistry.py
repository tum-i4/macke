import unittest

from macke.Error import (
    get_corresponding_ktest, get_reason_for_error, get_vulnerable_instruction)


class TestErrorRegistry(unittest.TestCase):

    def test_get_corresponding_ktest_file(self):
        self.assertEqual(
            "test000001.ktest",
            get_corresponding_ktest("test000001.assert.err"))

    def test_get_corresponding_ktest_directory(self):
        self.assertEqual(
            "/some/dir/test000001.ktest",
            get_corresponding_ktest("/some/dir/test000001.macke.err"))

    def test_get_corresponding_ktest_dirwithdot(self):
        self.assertEqual(
            "/sub.dir/test000001.ktest",
            get_corresponding_ktest("/sub.dir/test000001.ptr.err"))

    def test_get_reason_for_error(self):
        self.assertEqual(
            "ASSERTION FAIL: i != 42",
            get_reason_for_error("examples/simple.assert.err"))

    def test_get_vulnerable_instruction(self):
        self.assertEqual(
            "/some/path/file.c:21",
            get_vulnerable_instruction("examples/simple.assert.err"))
