import unittest

from macke.config import check_config


class TestValidConfig(unittest.TestCase):

    def test_valid_config(self):
        check_config()
