from nose.tools import ok_, eq_
from backend import youstat

def test_nigahiga():
    ok_('tones' in youstat.get_stats('nigahiga')[0])