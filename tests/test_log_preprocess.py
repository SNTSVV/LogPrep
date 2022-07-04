import unittest
import tempfile
from src.log_preprocess import *


class TestLogPreprocess(unittest.TestCase):
    def test_split_log(self):
        system = 'test_system'
        log_dir = os.path.join('tests', 'resources', 'single_log')
        with tempfile.TemporaryDirectory() as output_dir:
            split_log(
                system=system,
                log_dir=log_dir,
                log_split_keyword='restart',
                output_dir=output_dir
            )

            with open(os.path.join(output_dir, f'{system}_1.log'), 'r') as f:
                self.assertEqual(['restart\n', 'event1 port\n', 'event2 port\n'], f.readlines())
            with open(os.path.join(output_dir, f'{system}_2.log'), 'r') as f:
                self.assertEqual(['restart\n', 'event3 port\n', 'event4 port\n', 'event5 port'], f.readlines())

    # TODO: add more tests
