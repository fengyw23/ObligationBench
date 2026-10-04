from copy import deepcopy
import pytest
from openlibrary.catalog.add_book import normalize_import_record


@pytest.mark.parametrize('fields', [
    {'publishers': ['????']},
    {'authors': [{'name': '????'}]},
    {'publish_date': '????'},
    {'publishers': ['????'], 'authors': [{'name': '????'}], 'publish_date': '????'},
])
def test_exact_placeholders_are_removed(fields):
    record = {'title': 'Import example', 'source_records': ['test:placeholder'], **deepcopy(fields)}
    assert normalize_import_record(record) is None
    for field in fields:
        assert field not in record
    assert record['title'] == 'Import example'
    assert record['source_records'] == ['test:placeholder']


@pytest.mark.parametrize('fields', [
    {'publishers': ['Actual publisher'], 'authors': [{'name': 'Actual author'}], 'publish_date': '2001'},
    {'publishers': ['????', 'Actual publisher'], 'authors': [{'name': '????'}, {'name': 'Actual author'}], 'publish_date': '???? edition'},
    {'publishers': ['???? extra'], 'authors': [{'name': '????', 'key': '/authors/OL1A'}], 'publish_date': ' ???? '},
    {'publishers': [], 'authors': [], 'publish_date': ''},
])
def test_non_exact_fields_are_retained(fields):
    record = {'title': 'Import example', 'source_records': ['test:real'], **deepcopy(fields)}
    normalize_import_record(record)
    for field, value in fields.items():
        assert record[field] == value


def test_missing_fields_preserve_existing_normalization():
    record = {'title': 'Import example', 'source_records': 'test:missing'}
    normalize_import_record(record)
    assert record['source_records'] == ['test:missing']
    assert 'publishers' not in record
    assert 'publish_date' not in record
    assert record['authors'] == []
