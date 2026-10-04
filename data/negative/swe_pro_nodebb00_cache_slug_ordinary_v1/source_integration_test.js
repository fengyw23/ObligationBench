require('../require-main');
const nconf = require('nconf');
nconf.file({file:'/app/config.json'});
nconf.defaults({base_dir:'/app',relative_path:'',isCluster:false,isPrimary:true,upload_path:'/app/test/uploads',url:'http://127.0.0.1:4567/forum'});
global.env='production';
const db=require('/app/src/database');
const meta=require('/app/src/meta');
async function init() { await db.init(); await meta.configs.init(); meta.config.postCacheSize=1024*1024; }

const assert=require('assert');
let Posts, socketCache, adminCache;
describe('cache and slug native Redis regression',function(){
 before(async()=>{await init();Posts=require('/app/src/posts');socketCache=require('/app/src/socket.io/admin/cache');adminCache=require('/app/src/controllers/admin/cache');
 await db.sortedSetAdd('userslug:uid',9001,'ordinary-user');await db.setObjectField('groupslug:groupname','ordinary-group','Ordinary Group');await db.sortedSetAdd('categoryhandle:cid',9002,'ordinary-category');});
 after(async()=>{Posts.cache.reset();await db.sortedSetRemove('userslug:uid','ordinary-user');await db.deleteObjectField('groupslug:groupname','ordinary-group');await db.sortedSetRemove('categoryhandle:cid','ordinary-category');await db.close();});
 it('preserves scalar booleans for user/group/category and absent slug',async()=>{for(const slug of ['ordinary-user','ordinary-group','ordinary-category'])assert.strictEqual(await meta.slugTaken(slug),true);assert.strictEqual(await meta.slugTaken('ordinary-absent'),false);});
 it('returns ordered boolean array with normalization, duplicates and absent entries',async()=>{assert.deepStrictEqual(await meta.slugTaken(['Ordinary User','ordinary-absent','ordinary-group','ordinary-category','ordinary-user']),[true,false,true,true,true]);});
 it('handles empty and one-element arrays',async()=>{assert.deepStrictEqual(await meta.slugTaken([]),[]);assert.deepStrictEqual(await meta.slugTaken(['ordinary-absent']),[false]);});
 it('preserves scalar and array entry validation',async()=>{await assert.rejects(meta.slugTaken(''),/invalid-data/);await assert.rejects(meta.slugTaken(['ordinary-user',null]),/invalid-data/);});
 it('backwards compatibility alias supports arrays',async()=>{assert.deepStrictEqual(await meta.userOrGroupExists(['ordinary-user','ordinary-absent']),[true,false]);});
 it('exports same native cache and parser uses contents',async()=>{assert.strictEqual(Posts.cache,require('/app/src/posts/cache'));Posts.cache.enabled=true;Posts.cache.reset();Posts.cache.set('991|default','cached output');assert.strictEqual((await Posts.parsePost({pid:991,content:'other input'})).content,'cached output');});
 it('socket clear invalidates parser cache',async()=>{Posts.cache.set('992|default','stale output');await socketCache.clear(null,{name:'post'});assert.strictEqual(Posts.cache.has('992|default'),false);assert.strictEqual((await Posts.parsePost({pid:992,content:'fresh input'})).content,'fresh input');assert.strictEqual(Posts.cache.get('992|default'),'fresh input');});
 it('socket toggle affects parser cache',async()=>{await socketCache.toggle(null,{name:'post',enabled:false});await Posts.parsePost({pid:993,content:'uncached'});assert.strictEqual(Posts.cache.get('993|default'),undefined);assert.strictEqual(Posts.cache.enabled,false);await socketCache.toggle(null,{name:'post',enabled:true});});
 it('admin statistics and dump observe parser cache',async()=>{Posts.cache.reset();Posts.cache.set('994|default','dumped content');let stats;await adminCache.get({}, {render:(name,data)=>{stats=data;}});assert.strictEqual(stats.caches.post.itemCount,1);let dump,ended=false;await adminCache.dump({query:{name:'post'}},{setHeader:()=>{},write:(data,cb)=>{dump=JSON.parse(data);cb();},end:()=>{ended=true;}},()=>{throw Error('unexpected next');});assert.ok(dump.some(entry=>entry[0]==='994|default'));assert.strictEqual(ended,true);});
 it('clearCachedPost removes every content type',()=>{for(const type of ['default','plaintext','activitypub.note','activitypub.article'])Posts.cache.set('995|'+type,'typed content');Posts.clearCachedPost(995);for(const type of ['default','plaintext','activitypub.note','activitypub.article'])assert.strictEqual(Posts.cache.has('995|'+type),false);});
});
