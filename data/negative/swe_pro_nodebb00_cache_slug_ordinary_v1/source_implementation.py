from pathlib import Path
p=Path('/app/src/posts/index.js');s=p.read_text();needle='const Posts = module.exports;';assert s.count(needle)==1
s=s.replace(needle,needle+"\n\n// Resolve lazily so configuration is initialized before the LRU cache.\nObject.defineProperty(Posts, 'cache', {\n\tget: () => require('./cache'),\n\tenumerable: false,\n});")
p.write_text(s)
for name in ['src/controllers/admin/cache.js','src/socket.io/admin/cache.js','src/socket.io/admin/plugins.js']:
 p=Path('/app')/name;s=p.read_text();assert "require('../../posts/cache')" in s;s=s.replace("require('../../posts/cache')","require('../../posts').cache");p.write_text(s)
p=Path('/app/src/posts/parse.js');s=p.read_text();assert s.count("const cache = require('./cache');")==2;s=s.replace("const cache = require('./cache');",'const cache = Posts.cache;');p.write_text(s)
p=Path('/app/src/meta/index.js');s=p.read_text();needle='Meta.slugTaken = async function (slug) {\n';assert s.count(needle)==1;s=s.replace(needle,needle+"\tif (Array.isArray(slug)) {\n\t\treturn await Promise.all(slug.map(value => Meta.slugTaken(value)));\n\t}\n\n");p.write_text(s)
print('Canonical Posts.cache is shared across parsing and admin consumers; slugTaken handles arrays per element.')
