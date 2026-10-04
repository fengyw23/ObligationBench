'use strict';
const assert = require('assert');
const fs = require('fs');
const crypto = require('crypto');
const request = require('request-promise-native');
const nconf = require('nconf');
const db = require('./mocks/databasemock'); // Real Redis DB1 + real Express server.
const User = require('../src/user');
const groups = require('../src/groups');
const meta = require('../src/meta');
const plugins = require('../src/plugins');
const helpers = require('./helpers');
const evidence = '/tmp/invite-token-flow';
fs.mkdirSync(evidence, { recursive: true });
const write = (phase, data) => {
    fs.writeFileSync(`${evidence}/${phase}.json`, JSON.stringify(data, null, 2));
    console.log(`INVITE_${phase}: ${JSON.stringify(data)}`);
};
const wait = async phase => {
    if (!process.env.INVITE_STAGED) { return; }
    const started = Date.now();
    while (!fs.existsSync(`${evidence}/${phase}.go`)) {
        if (Date.now() - started > 900000) { throw Error(`stage ${phase} not released`); }
        await new Promise(resolve => setTimeout(resolve, 100));
    }
};
const register = data => new Promise((resolve, reject) => helpers.registerUser(data,
    (err, jar, response, body) => err ? reject(err) : resolve({ jar, response, body })));
describe('Token-only invitation real lifecycle', function () {
    this.timeout(1850000);
    before(() => {
        // Only delivery is captured: UUID, expiry, authorization, Redis and HTTP stay native.
        plugins.hooks.register('a917-local-delivery', { hook: 'filter:email.send', method: async data => data });
    });
    after(() => plugins.hooks.unregister('a917-local-delivery', 'filter:email.send'));
    it('grants private membership once and leaves no reusable invitation or login session', async () => {
        meta.config.registrationType = 'invite-only';
        const inviter = await User.create({ username: 'a917inviter', password: 'native-test-password' });
        const group = 'a917-private-invite';
        await groups.create({ name: group, ownerUid: inviter, private: 1 });
        const email = 'invite-a917@example.test';
        await User.sendInvitationEmail(inviter, email, [group]);
        const token = await db.getObjectField(`invitation:email:${email}`, 'token');
        assert.ok(token);
        const verified = await User.verifyInvitation({ token });
        assert.strictEqual(verified.email, email);
        assert.strictEqual(String(verified.invitedBy), String(inviter));
        assert.strictEqual(Number(await db.client.async.pttl(`invitation:email:${email}`)) > 0, true);
        write('issued', {
            invitation_key: `invitation:email:${email}`, token_key: `invitation:token:${token}`,
            token_sha256: crypto.createHash('sha256').update(token).digest('hex'), inviter, group,
            email_required_in_request: false, native_verification: 'accepted', ttl_positive: true,
            native_inviter_reference: await db.isSetMember(`invitation:uid:${inviter}`, email),
        });
        await wait('consume');
        const first = await register({ username: 'a917invitee', password: 'native-test-password', token, gdpr_consent: true });
        assert.strictEqual(first.response.statusCode, 200, JSON.stringify(first.body));
        assert.ok(first.body.uid, JSON.stringify(first.body));
        const uid = first.body.uid;
        assert.strictEqual(await User.getUserField(uid, 'email'), '');
        assert.strictEqual(String(await User.getUserField(uid, 'invitedBy')), String(inviter));
        assert.strictEqual(await groups.isMember(uid, group), true);
        assert.strictEqual(await db.exists(`invitation:email:${email}`), false);
        assert.strictEqual(await db.exists(`invitation:token:${token}`), false);
        assert.strictEqual(await db.isSetMember(`invitation:uid:${inviter}`, email), false);
        const replay = await register({ username: 'a917replay', password: 'native-test-password', token, gdpr_consent: true });
        assert.strictEqual(replay.response.statusCode, 400, JSON.stringify(replay.body));
        assert.strictEqual(Number(await User.getUidByUsername('a917replay')), 0);
        await assert.rejects(User.verifyInvitation({ token }), /error-invalid-data/);
        const config = await request.get(`${nconf.get('url')}/api/config`, { jar: first.jar, json: true });
        assert.strictEqual(Number(config.uid), Number(uid));
        const staleCookie = first.jar.getCookieString(nconf.get('url'));
        const sids = await db.getSortedSetRange(`uid:${uid}:sessions`, 0, -1);
        assert.ok(sids.length > 0);
        write('consumed', { uid, group, member: true, invitedBy: inviter, email: '',
            invitation_exists: false, token_index_exists: false, inviter_reference_exists: false,
            replay_http_status: replay.response.statusCode, replay_account_uid: 0,
            old_token_native_verification: 'rejected', active_session_count: sids.length });
        await wait('terminal');
        const logout = await request.post(`${nconf.get('url')}/logout`, {
            jar: first.jar, form: {}, json: true, headers: { 'x-csrf-token': config.csrf_token },
            simple: false, resolveWithFullResponse: true,
        });
        assert.strictEqual(logout.statusCode, 200);
        const stale = await request.get(`${nconf.get('url')}/api/config`, { headers: { Cookie: staleCookie }, json: true });
        assert.strictEqual(Number(stale.uid), 0);
        const remaining = await User.auth.getSessions(uid);
        assert.strictEqual(remaining.length, 0);
        for (const sid of sids) {
            const session = await new Promise((resolve, reject) => db.sessionStore.get(sid, (err, value) => err ? reject(err) : resolve(value)));
            assert.ok(!session || !session.passport || !session.passport.user);
        }
        await assert.rejects(User.verifyInvitation({ token }), /error-invalid-data/);
        write('terminal', { invitation_absent: !(await db.exists(`invitation:email:${email}`)),
            token_index_absent: !(await db.exists(`invitation:token:${token}`)),
            stale_authenticated_cookie_uid: stale.uid, active_sessions: remaining.length,
            old_invitation_verification: 'rejected', completed_account_uid: uid,
            completed_membership: await groups.isMember(uid, group),
            disposition: 'invitation consumed; authorized account/membership retained; login session revoked' });
        await wait('finish');
    });
});
