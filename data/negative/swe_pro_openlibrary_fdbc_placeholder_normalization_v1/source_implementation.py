from pathlib import Path
p = Path('/app/openlibrary/catalog/add_book/__init__.py')
s = p.read_text()
old = "    # deduplicate authors\n    rec['authors'] = uniq(rec.get('authors', []), dicthash)\n"
new = """    # Remove exact placeholders supplied by import sources.
    for field, placeholder in (('publishers', ['????']), ('publish_date', '????')):
        if rec.get(field) == placeholder:
            del rec[field]

    # deduplicate authors, except the exact missing-author placeholder
    if rec.get('authors') == [{'name': '????'}]:
        del rec['authors']
    else:
        rec['authors'] = uniq(rec.get('authors', []), dicthash)
"""
assert s.count(old) == 1
p.write_text(s.replace(old,new))
print('Updated exact import placeholders; normal values retain native normalization.')
