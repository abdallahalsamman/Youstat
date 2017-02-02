from nose.tools import ok_, eq_
from backend import youstat

def test_nigahiga():
    ok_('tones' in youstat.get_stats('nigahiga')[0])

def test_non_english_channel():
    ok_('tones' in youstat.get_stats('pablog1100')[0])
    ok_('tones' in youstat.get_stats('InteractiveSpanish')[0])
