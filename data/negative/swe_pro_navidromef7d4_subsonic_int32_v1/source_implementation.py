from pathlib import Path
import re
p=Path('/app/server/subsonic/responses/responses.go');s=p.read_text()
s,n=re.subn(r'(?m)^(\s*\w+\s+)(\[\])?int(\s+`)',lambda m:m[1]+(m[2] or '')+'int32'+m[3],s)
assert n==30,n
p.write_text(s)
changes = {'server/subsonic/album_lists.go': [(158, 'int(time.Since(np.Start).Minutes())'), (159, 'i + 1')], 'server/subsonic/api.go': [(265, 'code')], 'server/subsonic/browsing.go': [(357, 'artist.AlbumCount'), (358, 'artist.Rating'), (395, 'album.Rating'), (396, 'album.SongCount'), (418, 'album.SongCount'), (419, 'int(album.Duration)'), (424, 'album.MaxYear'), (426, 'album.Rating')], 'server/subsonic/helpers.go': [(88, 'a.AlbumCount'), (89, 'a.Rating'), (103, 'a.AlbumCount'), (106, 'a.Rating'), (119, 'g.SongCount'), (120, 'g.AlbumCount'), (145, 'mf.Year'), (148, 'mf.TrackNumber'), (149, 'int(mf.Duration)'), (152, 'mf.BitRate'), (161, 'mf.DiscNumber'), (173, 'mf.Rating'), (212, 'al.MaxYear'), (218, 'int(al.Duration)'), (219, 'al.SongCount'), (227, 'al.Rating')], 'server/subsonic/playlists.go': [(168, 'p.SongCount'), (170, 'int(p.Duration)')], 'server/subsonic/searching.go': [(107, 'artist.AlbumCount'), (108, 'artist.Rating')], 'server/subsonic/sharing.go': [(39, 'share.VisitCount')]}
for filename, edits in changes.items():
    p=Path('/app')/filename; lines=p.read_text().splitlines(keepends=True)
    for linenum, old in edits:
        line=lines[linenum-1]; assert line.count(old)==1,(filename,linenum,line,old)
        new='int32('+old[4:] if old.startswith('int(') else 'int32('+old+')'
        lines[linenum-1]=line.replace(old,new,1)
    p.write_text(''.join(lines))
p=Path('/app/server/subsonic/responses/responses_test.go');s=p.read_text();assert s.count('[]int{')==2
p.write_text(s.replace('[]int{','[]int32{'))
print('Subsonic response integer types and typed native conversion sites updated.')
