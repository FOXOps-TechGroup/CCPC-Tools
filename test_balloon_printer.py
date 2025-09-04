from unittest import TestCase

from balloon_printer import print_task


class Test(TestCase):
    def test_print_task(self):
        test_task= {
            'problem_id':1,
            'problem_letter':'A',
            'room':'A',
            'team_id':'team1001',
            'ac_time':'01.11',
            'pst':2,
        }
        print_task(test_task)
