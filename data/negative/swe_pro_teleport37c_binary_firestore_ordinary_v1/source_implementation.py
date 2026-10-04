from pathlib import Path
p=Path('/app/lib/backend/firestore/firestorebk.go')
s=p.read_text()
s=s.replace('Value     string `firestore:', 'Value     []byte `firestore:',1)
s=s.replace('Value: []byte(r.Value),','Value: r.Value,',1)
s=s.replace('string(item.Value)','item.Value').replace('string(replaceWith.Value)','replaceWith.Value')
s=s.replace('existingRecord.Value != string(expected.Value)','!bytes.Equal(existingRecord.Value, expected.Value)',1)
s=s.replace('docSnap.DataTo(&r)','decodeRecord(docSnap, &r)').replace('expectedDocSnap.DataTo(&existingRecord)','decodeRecord(expectedDocSnap, &existingRecord)').replace('change.Doc.DataTo(&r)','decodeRecord(change.Doc, &r)')
s+='\n// decodeRecord accepts current byte values and legacy string values.\nfunc decodeRecord(doc *firestore.DocumentSnapshot, r *record) error {\n    if err := doc.DataTo(r); err == nil { return nil }\n    var legacy struct {\n        Key string `firestore:"key,omitempty"`\n        Timestamp int64 `firestore:"timestamp,omitempty"`\n        Expires int64 `firestore:"expires,omitempty"`\n        ID int64 `firestore:"id,omitempty"`\n        Value string `firestore:"value,omitempty"`\n    }\n    if err := doc.DataTo(&legacy); err != nil { return err }\n    *r = record{Key: legacy.Key, Timestamp: legacy.Timestamp, Expires: legacy.Expires, ID: legacy.ID, Value: []byte(legacy.Value)}\n    return nil\n}\n'
p.write_text(s)
print('Binary records now use []byte; legacy string snapshots are decoded compatibly')
