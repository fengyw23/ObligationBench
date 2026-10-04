from types import SimpleNamespace
import pytest
from PyQt5.QtCore import QUrl
from qutebrowser.mainwindow import tabwidget, tabbedbrowser
from qutebrowser.utils import objreg, usertypes

@pytest.fixture
def windows(qtbot, config_stub, fake_web_tab, win_registry, monkeypatch):
    monkeypatch.setattr(tabwidget.objects, 'backend', usertypes.Backend.QtWebKit)
    config_stub.val.tabs.title.format = 'Normal'
    config_stub.val.tabs.title.format_pinned = 'Pinned'
    old = tabwidget.TabWidget(0)
    new = tabwidget.TabWidget(1)
    qtbot.addWidget(old)
    qtbot.addWidget(new)
    win_registry.add_window(1)
    objreg.register('tabbed-browser', SimpleNamespace(widget=old), scope='window', window=0)
    objreg.register('tabbed-browser', SimpleNamespace(widget=new), scope='window', window=1)
    yield old, new
    objreg.delete('tabbed-browser', scope='window', window=0)
    objreg.delete('tabbed-browser', scope='window', window=1)

def restored_context(old, new, fake_web_tab, config_stub, monkeypatch, pinned):
    config_stub.val.tabs.tabs_are_windows = True
    tab = fake_web_tab(url=QUrl('https://example.test/'))
    tab.win_id = 1
    new.addTab(tab, 'restored')
    history = []
    monkeypatch.setattr(tab.history.private_api, 'deserialize', lambda data: history.append(data))
    entry = tabbedbrowser._UndoEntry(url=QUrl('https://example.test/'), history=b'closed-history', index=0, pinned=pinned)
    source = SimpleNamespace(widget=old, undo_stack=[[entry]], tabopen=lambda **kwargs: tab)
    return source, tab, history

@pytest.mark.parametrize('pinned', [True, False])
def test_tab_owned_pinned_api(windows, fake_web_tab, pinned):
    old, new = windows
    tab = fake_web_tab(url=QUrl('https://example.test/'))
    old.addTab(tab, 'tab')
    tab.set_pinned(pinned)
    assert tab.data.pinned is pinned
    assert old.tabText(0) == ('Pinned' if pinned else 'Normal')
    old.removeTab(0)
    tab.win_id = 1
    new.addTab(tab, 'moved')
    tab.set_pinned(not pinned)
    assert tab.data.pinned is not pinned
    assert new.tabText(0) == ('Normal' if pinned else 'Pinned')
    assert old.indexOf(tab) == -1

@pytest.mark.parametrize('pinned', [True, False])
def test_undo_different_window(windows, fake_web_tab, config_stub, monkeypatch, pinned):
    old, new = windows
    source, tab, history = restored_context(old, new, fake_web_tab, config_stub, monkeypatch, pinned)
    assert old.indexOf(tab) == -1 and new.indexOf(tab) == 0
    tabbedbrowser.TabbedBrowser.undo(source)
    assert source.undo_stack == []
    assert history == [b'closed-history']
    assert tab.data.pinned is pinned
    assert new.tabText(0) == ('Pinned' if pinned else 'Normal')
    print('Native undo restored pinned:', pinned, 'tab window:', tab.win_id, 'UI title:', new.tabText(0), 'old owner index:', old.indexOf(tab))
