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
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"

	vault "github.com/hashicorp/vault/api"
)

// TYPES

// AccessTokens contains service access tokens loaded from secrets storage.
type AccessTokens struct {
	StatusCheckerIn string
	ADCMIn          string
	ADCMOut         string
}

type secretsFile struct {
	ADCM struct {
		StatusChecker struct {
			StatusServiceToken string `json:"status_service_token"`
		} `json:"status_checker"`
		Backend struct {
			StatusServiceToken string `json:"status_service_token"`
		} `json:"backend"`
		StatusService struct {
			ADCMToken string `json:"adcm_token"`
		} `json:"status_service"`
	} `json:"adcm"`
}

// ClientSettings describes Vault connection settings.
type ClientSettings struct {
	URL            string
	TokenFile      string
	MountPoint     string
	ClientCertFile string
	ClientKeyFile  string
	CAFile         string
	Namespace      string
}

// SecretsBackend retrieves access tokens from a secrets source.
type SecretsBackend interface {
	Retrieve() (AccessTokens, error)
}

// SecretsBackendFileSystem reads access tokens from a JSON file.
type SecretsBackendFileSystem struct {
	path string
}

// SecretsBackendVault reads access tokens from Vault KV v2.
type SecretsBackendVault struct {
	client     *vault.Client
	mountPoint string
}

// CONSTRUCTORS

// NewSecretsBackendFileSystem creates a filesystem-based secrets backend.
func NewSecretsBackendFileSystem(path string) *SecretsBackendFileSystem {
	return &SecretsBackendFileSystem{path: path}
}

// NewSecretsBackendVault creates a vault-based secrets backend
func NewSecretsBackendVault(client *vault.Client, mountPoint string) *SecretsBackendVault {
	return &SecretsBackendVault{client: client, mountPoint: mountPoint}
}

// Read settings for vault backend from environment
func ClientSettingsFromEnv() (ClientSettings, error) {
	settings := ClientSettings{
		URL:            os.Getenv("VAULT_URL"),
		TokenFile:      os.Getenv("VAULT_TOKEN_FILE"),
		MountPoint:     os.Getenv("VAULT_MOUNT_POINT"),
		ClientCertFile: os.Getenv("VAULT_CLIENT_CERT_FILE"),
		ClientKeyFile:  os.Getenv("VAULT_CLIENT_KEY_FILE"),
		CAFile:         os.Getenv("VAULT_CA_FILE"),
		Namespace:      os.Getenv("VAULT_NAMESPACE"),
	}

	if settings.URL == "" {
		return ClientSettings{}, fmt.Errorf("missing required environment variable: VAULT_URL")
	}
	if settings.TokenFile == "" {
		return ClientSettings{}, fmt.Errorf("missing required environment variable: VAULT_TOKEN_FILE")
	}
	if settings.MountPoint == "" {
		return ClientSettings{}, fmt.Errorf("missing required environment variable: VAULT_MOUNT_POINT")
	}

	return settings, nil
}

// Builds client to access the vault
func BuildVaultClient(settings ClientSettings) (*vault.Client, error) {
	certIsSet := settings.ClientCertFile != ""
	keyIsSet := settings.ClientKeyFile != ""
	if certIsSet != keyIsSet {
		return nil, fmt.Errorf("vault client initialization error: both client cert and key files must be specified")
	}

	config := vault.DefaultConfig()
	config.Address = settings.URL

	if certIsSet || settings.CAFile != "" {
		tlsConfig := &vault.TLSConfig{
			ClientCert: settings.ClientCertFile,
			ClientKey:  settings.ClientKeyFile,
			CACert:     settings.CAFile,
		}
		if settings.CAFile == "" && certIsSet {
			tlsConfig.Insecure = true
		}

		if err := config.ConfigureTLS(tlsConfig); err != nil {
			return nil, fmt.Errorf("configure vault tls: %w", err)
		}
	}

	token, err := os.ReadFile(settings.TokenFile)
	if err != nil {
		return nil, fmt.Errorf("failed to retrieve token from %s: %w", settings.TokenFile, err)
	}
	if len(token) == 0 {
		return nil, fmt.Errorf("failed to retrieve token from %s: token is empty", settings.TokenFile)
	}

	client, err := vault.NewClient(config)
	if err != nil {
		return nil, fmt.Errorf("unable to initialize vault client: %w", err)
	}
	client.SetToken(string(token))

	if settings.Namespace != "" {
		client.SetNamespace(settings.Namespace)
	}

	return client, nil
}

// INTERFACE IMPLEMENTATIONS

func (s *SecretsBackendFileSystem) Retrieve() (AccessTokens, error) {
	data, err := os.ReadFile(s.path)
	if err != nil {
		return AccessTokens{}, fmt.Errorf("read secrets file %q: %w", s.path, err)
	}

	var payload secretsFile

	if err := json.Unmarshal(data, &payload); err != nil {
		return AccessTokens{}, fmt.Errorf("parse secrets json from %q: %w", s.path, err)
	}

	tokens := AccessTokens{
		StatusCheckerIn: payload.ADCM.StatusChecker.StatusServiceToken,
		ADCMIn:          payload.ADCM.Backend.StatusServiceToken,
		ADCMOut:         payload.ADCM.StatusService.ADCMToken,
	}

	if strings.TrimSpace(tokens.StatusCheckerIn) == "" {
		return AccessTokens{}, fmt.Errorf("missing required secret: adcm.status_checker.status_service_token")
	}
	if strings.TrimSpace(tokens.ADCMIn) == "" {
		return AccessTokens{}, fmt.Errorf("missing required secret: adcm.backend.status_service_token")
	}
	if strings.TrimSpace(tokens.ADCMOut) == "" {
		return AccessTokens{}, fmt.Errorf("missing required secret: adcm.status_service.adcm_token")
	}

	return tokens, nil
}

func (s *SecretsBackendVault) Retrieve() (AccessTokens, error) {
	statusCheckerIn, err := s.retrieveField("adcm/status_checker", "status_service_token")
	if err != nil {
		return AccessTokens{}, err
	}
	adcmIn, err := s.retrieveField("adcm/backend", "status_service_token")
	if err != nil {
		return AccessTokens{}, err
	}
	adcmOut, err := s.retrieveField("adcm/status_service", "adcm_token")
	if err != nil {
		return AccessTokens{}, err
	}

	return AccessTokens{
		StatusCheckerIn: statusCheckerIn,
		ADCMIn:          adcmIn,
		ADCMOut:         adcmOut,
	}, nil
}

func (s *SecretsBackendVault) retrieveField(path string, field string) (string, error) {
	secret, err := s.client.KVv2(s.mountPoint).Get(context.Background(), path)
	if err != nil {
		return "", fmt.Errorf("failed to retrieve secret %q from mount point %q: %w", path, s.mountPoint, err)
	}
	if secret == nil || secret.Data == nil {
		return "", fmt.Errorf("storage format was unexpected for %q from mount point %q: missing data", path, s.mountPoint)
	}

	raw, ok := secret.Data[field]
	if !ok {
		return "", fmt.Errorf(
			"storage format was unexpected for %q from mount point %q: failed to get %s",
			path,
			s.mountPoint,
			field,
		)
	}

	value, ok := raw.(string)
	if !ok {
		return "", fmt.Errorf("secret value is not a string for %q field %q: %T", path, field, raw)
	}
	if strings.TrimSpace(value) == "" {
		return "", fmt.Errorf("missing required secret: %s.%s", strings.ReplaceAll(path, "/", "."), field)
	}

	return value, nil
}
