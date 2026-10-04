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

def test_original_undo_wrong_container(windows, fake_web_tab, config_stub, monkeypatch):
    old, new = windows
    source, tab, history = restored_context(old, new, fake_web_tab, config_stub, monkeypatch, True)
    assert old.indexOf(tab) == -1 and new.indexOf(tab) == 0
    with pytest.raises(AttributeError) as error:
        tabbedbrowser.TabbedBrowser.undo(source)
    assert history == [b'closed-history']
    print('Observed original cross-window undo error:', str(error.value))
    print('Original owner index:', old.indexOf(tab), 'actual owner index:', new.indexOf(tab), 'restored UI title:', new.tabText(0))
