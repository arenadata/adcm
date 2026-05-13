// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package config

import (
	"path/filepath"
	"strings"
	"testing"
)

func TestSecretsBackendFileSystemRetrieve(t *testing.T) {
	tests := []struct {
		name      string
		file      string
		expected  AccessTokens
		errSubstr string
	}{
		{
			name: "correct secrets file",
			file: "secrets_valid.json",
			expected: AccessTokens{
				StatusCheckerIn: "status-checker-in",
				ADCMIn:          "adcm-in",
				ADCMOut:         "adcm-out",
			},
		},
		{
			name:      "missing one secret",
			file:      "secrets_missing_status_checker_in.json",
			errSubstr: "missing required secret: adcm.status_checker.status_service_token",
		},
		{
			name:      "incorrect type for one secret",
			file:      "secrets_bad_type_status_checker_in.json",
			errSubstr: "parse secrets json",
		},
		{
			name:      "file with array content",
			file:      "secrets_array_content.json",
			errSubstr: "parse secrets json",
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			path := filepath.Join("testdata", tc.file)

			backend := NewSecretsBackendFileSystem(path)
			actual, err := backend.Retrieve()

			if tc.errSubstr != "" {
				if err == nil {
					t.Fatalf("expected error containing %q, got nil", tc.errSubstr)
				}
				if !strings.Contains(err.Error(), tc.errSubstr) {
					t.Fatalf("expected error containing %q, got %q", tc.errSubstr, err.Error())
				}
				return
			}

			if err != nil {
				t.Fatalf("expected no error, got %v", err)
			}
			if actual != tc.expected {
				t.Fatalf("expected %+v, got %+v", tc.expected, actual)
			}
		})
	}
}
