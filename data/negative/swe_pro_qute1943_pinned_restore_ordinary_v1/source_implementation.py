from pathlib import Path
p=Path('/app/qutebrowser/browser/browsertab.py');s=p.read_text();needle='    def navigation_blocked(self) -> bool:';assert s.count(needle)==1
method='''    def set_pinned(self, pinned: bool) -> None:
        # Resolve the current tab owner, which can differ after undo.
        tabbed_browser = objreg.get('tabbed-browser', scope='window',
                                    window=self.win_id)
        tabbed_browser.widget.set_tab_pinned(self, pinned)

'''
p.write_text(s.replace(needle,method+needle))
p=Path('/app/qutebrowser/mainwindow/tabbedbrowser.py');s=p.read_text();old='self.widget.set_tab_pinned(newtab, entry.pinned)';assert s.count(old)==1;p.write_text(s.replace(old,'newtab.set_pinned(entry.pinned)'))
p=Path('/app/qutebrowser/browser/commands.py');s=p.read_text();assert 'self._tabbed_browser.widget.set_tab_pinned(tab, to_pin)' in s;assert 'new_tabbed_browser.widget.set_tab_pinned(newtab, curtab.data.pinned)' in s;s=s.replace('self._tabbed_browser.widget.set_tab_pinned(tab, to_pin)','tab.set_pinned(to_pin)').replace('new_tabbed_browser.widget.set_tab_pinned(newtab, curtab.data.pinned)','newtab.set_pinned(curtab.data.pinned)');p.write_text(s)
p=Path('/app/qutebrowser/misc/sessions.py');s=p.read_text();old='tabbed_browser.widget.set_tab_pinned(new_tab,\n                                                     new_tab.data.pinned)';assert old in s;p.write_text(s.replace(old,'new_tab.set_pinned(new_tab.data.pinned)'))
print('Pinned updates resolve the restored tab current window through AbstractTab.set_pinned.')
