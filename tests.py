from nose.tools import ok_, eq_
import youstat

def test_nigahiga():
    ok_('document_tone' in youstat.get_stats('nigahiga'))
