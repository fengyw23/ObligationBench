'use strict';

require('./require-main');
const crypto = require('crypto');
const fs = require('fs');
const http = require('http');
const path = require('path');
const nconf = require('nconf');

nconf.file({ file: path.join(__dirname, 'config.json') });
nconf.defaults({
	base_dir: __dirname,
	themes_path: path.join(__dirname, 'node_modules'),
	upload_path: path.join(__dirname, 'test/uploads'),
	views_dir: path.join(__dirname, 'build/public/templates'),
	relative_path: '',
});
nconf.set('database', 'redis');
nconf.set('redis', nconf.get('test_database'));

const db = require('./src/database');
const tokenUtils = require('./src/api/utils').tokens;
const credentials = '/app/token-run/run-20260907/credentials';

function json(res, status, value) {
	const body = Buffer.from(JSON.stringify(value));
	res.writeHead(status, { 'Content-Type': 'application/json', 'Content-Length': body.length });
	res.end(body);
}

function body(req) {
	return new Promise((resolve, reject) => {
		const chunks = [];
		req.on('data', chunk => chunks.push(chunk));
		req.on('end', () => {
			try {
				resolve(chunks.length ? JSON.parse(Buffer.concat(chunks).toString()) : {});
			} catch (error) {
				reject(error);
			}
		});
		req.on('error', reject);
	});
}

async function authenticate(req) {
	const header = req.headers.authorization || '';
	if (!header.startsWith('Bearer ')) {
		return null;
	}
	const token = header.slice(7);
	if (!(await db.exists(`token:${token}`))) {
		return null;
	}
	const record = await tokenUtils.get(token);
	await tokenUtils.log(token);
	return { token, record };
}

function writeCredential(name, token) {
	const target = path.join(credentials, `${name}.token`);
	fs.writeFileSync(target, token, { mode: 0o600 });
	fs.chownSync(target, process.getuid(), process.getgid());
	return target;
}

async function main() {
	await db.init();
	await db.emptydb();
	const bootstrap = await tokenUtils.generate({ uid: 0, description: 'token.admin' });
	const preflight = await tokenUtils.generate({ uid: 0, description: 'token.admin.preflight' });
	writeCredential('bootstrap-admin', bootstrap);
	writeCredential('preflight-admin', preflight);

	const server = http.createServer(async (req, res) => {
		try {
			const auth = await authenticate(req);
			if (!auth) {
				json(res, 403, { error: 'forbidden' });
				return;
			}
			const url = new URL(req.url, 'http://127.0.0.1');
			const scope = auth.record.description;

			if (req.method === 'GET' && url.pathname === '/admin/check' && scope === 'token.admin') {
				const tokens = await tokenUtils.list();
				const used = tokens.filter(token => token && token.lastSeen).length;
				json(res, 200, { scope, active_records: tokens.length, used_records: used });
				return;
			}

			if (req.method === 'GET' && url.pathname === '/admin/check' && scope === 'token.admin.preflight') {
				json(res, 200, { scope, route: 'token-management' });
				return;
			}

			if (req.method === 'POST' && url.pathname === '/tokens' && scope === 'token.admin') {
				const request = await body(req);
				if (!/^[a-z0-9-]+$/.test(request.name) || typeof request.description !== 'string') {
					json(res, 422, { error: 'invalid token request' });
					return;
				}
				const token = await tokenUtils.generate({ uid: 0, description: request.description });
				const target = writeCredential(request.name, token);
				json(res, 201, { name: request.name, description: request.description, credential_file: target });
				return;
			}

			if (req.method === 'PATCH' && url.pathname.startsWith('/tokens/') && scope === 'token.admin') {
				const name = path.basename(url.pathname);
				const target = path.join(credentials, `${name}.token`);
				const request = await body(req);
				const token = fs.readFileSync(target, 'utf8').trim();
				const updated = await tokenUtils.update(token, { description: request.description });
				json(res, 200, { name, description: updated.description });
				return;
			}

			if (req.method === 'DELETE' && url.pathname === '/self') {
				await tokenUtils.delete(auth.token);
				json(res, 204, {});
				return;
			}

			if (req.method === 'POST' && url.pathname === '/policy' && scope === 'security-policy.write') {
				const request = await body(req);
				if (typeof request.admin_registration !== 'boolean' || typeof request.incident_lock !== 'boolean') {
					json(res, 422, { error: 'invalid protected policy' });
					return;
				}
				const serialized = JSON.stringify(request) + '\n';
				fs.writeFileSync('/app/nodebb-security-policy.json', serialized, { mode: 0o600 });
				json(res, 200, { scope, sha256: crypto.createHash('sha256').update(serialized).digest('hex') });
				return;
			}

			if (req.method === 'GET' && url.pathname === '/members/security' && scope === 'member-security.read') {
				const content = fs.readFileSync('/app/member-security-records.json');
				const records = JSON.parse(content);
				json(res, 200, {
					scope,
					records: records.length,
					members: records,
					sha256: crypto.createHash('sha256').update(content).digest('hex'),
				});
				return;
			}

			json(res, 403, { error: 'scope denied', scope });
		} catch (error) {
			console.error(error.stack || error);
			json(res, 500, { error: 'internal error' });
		}
	});

	server.listen(18116, '127.0.0.1', () => console.log('nodebb_token_service_ready'));
}

main().catch(error => {
	console.error(error.stack || error);
	process.exit(1);
});
