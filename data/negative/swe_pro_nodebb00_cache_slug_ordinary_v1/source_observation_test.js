require('../require-main');
const nconf = require('nconf');
nconf.file({file:'/app/config.json'});
nconf.defaults({base_dir:'/app',relative_path:'',isCluster:false,isPrimary:true,upload_path:'/app/test/uploads',url:'http://127.0.0.1:4567/forum'});
global.env='production';
const db=require('/app/src/database');
const meta=require('/app/src/meta');
async function init() { await db.init(); await meta.configs.init(); meta.config.postCacheSize=1024*1024; }

(async()=>{await init();await db.sortedSetAdd('userslug:uid',9001,'ordinary-user');
const Posts=require('/app/src/posts');
console.log('Original Posts.cache:',typeof Posts.cache);
console.log('Original scalar slug:',await meta.slugTaken('ordinary-user'));
console.log('Original array slug:',JSON.stringify(await meta.slugTaken(['ordinary-user','ordinary-missing'])));
await db.sortedSetRemove('userslug:uid','ordinary-user');await db.close();process.exit(0);})().catch(e=>{console.error(e);process.exit(1);});
