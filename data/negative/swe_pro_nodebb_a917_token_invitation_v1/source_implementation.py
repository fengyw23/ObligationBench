from pathlib import Path

root = Path('/app')
p = root / 'src/user/invite.js'
s = p.read_text()
s = s.replace('if (!query.token || !query.email)', 'if (!query.token)')
s = s.replace("\t\tconst token = await db.getObjectField(`invitation:email:${query.email}`, 'token');", "\t\tconst tokenData = await db.getObject(`invitation:token:${query.token}`);\n\t\tconst email = query.email || (tokenData && tokenData.email);\n\t\tconst invitation = email && await db.getObject(`invitation:email:${email}`);\n\t\tconst token = invitation && invitation.token;")
s = s.replace("\t\tif (!token || token !== query.token) {", "\t\tif (!token || token !== query.token || (tokenData && Number(tokenData.claims) > 0)) {")
old = "\t\t\tthrow new Error('[[register:invite.error-invalid-data]]');\n\t\t}\n\t};"
new = """\t\t\tthrow new Error('[[register:invite.error-invalid-data]]');
\t\t}
\t\treturn { ...invitation, email, invitedBy: invitation.invitedBy || (tokenData && tokenData.invitedBy) };
\t};

\t// Reserve at actual account creation, including resumed interstitials.
\tUser.claimInvitation = async function (query) {
\t\tconst invitation = await User.verifyInvitation(query);
\t\tconst claims = await db.incrObjectField(`invitation:token:${query.token}`, 'claims', 1);
\t\tif (claims !== 1) {
\t\t\tthrow new Error('[[register:invite.error-invalid-data]]');
\t\t}
\t\t// A deletion or expiry between lookup and reservation must fail closed.
\t\tconst token = await db.getObjectField(`invitation:email:${invitation.email}`, 'token');
\t\tif (token !== query.token) {
\t\t\tawait db.delete(`invitation:token:${query.token}`);
\t\t\tthrow new Error('[[register:invite.error-invalid-data]]');
\t\t}
\t\treturn invitation;
\t};"""
assert old in s
s = s.replace(old, new, 1)
s = s.replace("\t\tawait Promise.all([\n\t\t\tdeleteFromReferenceList(invitedByUid, email),\n\t\t\tdb.delete(`invitation:email:${email}`),\n\t\t]);", "\t\tawait User.deleteInvitationKey(email);")
s = s.replace("\t\tawait db.delete(`invitation:email:${email}`);", "\t\tconst token = await db.getObjectField(`invitation:email:${email}`, 'token');\n\t\tawait db.delete(`invitation:email:${email}`);\n\t\tif (token) {\n\t\t\tawait db.delete(`invitation:token:${token}`);\n\t\t}")
s = s.replace("\t\t\tgroupsToJoin: JSON.stringify(groupsToJoin),", "\t\t\tgroupsToJoin: JSON.stringify(groupsToJoin),\n\t\t\tinvitedBy: uid,")
s = s.replace("\t\tawait db.pexpireAt(`invitation:email:${email}`, Date.now() + expireIn);", "\t\tawait db.setObject(`invitation:token:${token}`, { email, invitedBy: uid, claims: 0 });\n\t\tconst expires = Date.now() + expireIn;\n\t\tawait db.pexpireAt(`invitation:email:${email}`, expires);\n\t\tawait db.pexpireAt(`invitation:token:${token}`, expires);")
p.write_text(s)
p = root / 'src/controllers/authentication.js'
s = p.read_text()
s = s.replace('if (!userData.email) {', 'if (!userData.email && !userData.token) {', 1)
start = s.index('\tconst uid = await user.create(userData);')
end = s.index('\tconst next = req.session.returnTo', start)
s = s[:start] + """\tconst invitation = userData.token ? await user.claimInvitation(userData) : null;
\tlet uid;
\ttry {
\t\tuid = await user.create(userData);
\t} catch (err) {
\t\tif (invitation) {
\t\t\tawait db.setObjectField(`invitation:token:${userData.token}`, 'claims', 0);
\t\t}
\t\tthrow err;
\t}
\tif (invitation) {
\t\tawait user.joinGroupsFromInvitation(uid, invitation.email);
\t\tawait user.setUserField(uid, 'invitedBy', invitation.invitedBy);
\t\tawait user.deleteInvitationKey(invitation.email);
\t}
\tif (res.locals.processLogin) {
\t\tawait authenticationController.doLogin(req, uid);
\t}

""" + s[end:]
p.write_text(s)
print('implemented token-only lookup, actual-creation claim, metadata association and consumption')
