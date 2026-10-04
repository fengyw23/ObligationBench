import pytest
from qutebrowser.utils import utils
from qutebrowser.misc import utilcmds
from qutebrowser.api import cmdutils


@pytest.mark.parametrize('duration, expected', [
    ('123', 123), ('0', 0), (' 60 ', 60), ('0.5s', 500),
    ('1.001s', 1001), ('.5s', 500), ('1h 1s', 3601000),
    ('1h 2m 3.5s', 3723500), (' 1s\t1h ', 3601000),
    ('1.5h', 5400000), ('1m .25s', 60250), ('0.0005s', 0),
])
def test_valid_duration_components(duration, expected):
    assert utils.parse_duration(duration) == expected


@pytest.mark.parametrize('duration', [
    '-1s', '-1', '', ' ', '34ss', '1.2', '1h x', '1h 2',
    '1s1s', '1h1h', '1.s', '1 h', '+1s', '1d', '1ms',
    'NaNs', 'infs', 's', 'h m', '1h-1s',
])
def test_invalid_duration_raises(duration):
    with pytest.raises(ValueError):
        utils.parse_duration(duration)


@pytest.mark.parametrize('duration', ['-1s', 'not-a-duration', '1s1s'])
def test_later_preserves_command_error_interface(duration):
    with pytest.raises(cmdutils.CommandError, match='Wrong format'):
        utilcmds.later(duration, 'nop', 1)
