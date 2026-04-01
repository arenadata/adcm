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

package main

import (
	"adcm/config"
	"adcm/status"
	"flag"
	"fmt"
	"os"
)

func main() {
	logFile := flag.String("logfile", "", "log file name (with full path)")
	help := flag.Bool("help", false, "Print usage")
	flag.Parse()
	if *help {
		flag.PrintDefaults()
		os.Exit(0)
	}

	accessTokens, err := RetrieveAccessTokensFromBackend()
	if err != nil {
		panic(err)
	}

	status.Start(status.NewSecretConfig(accessTokens), *logFile, GetLogLevel())
}

func GetLogLevel() string {
	priorityLogLevel, ok := os.LookupEnv("STATUS_LOG_LEVEL")
	if ok {
		return priorityLogLevel
	}

	logLevel, ok := os.LookupEnv("LOG_LEVEL")
	if !ok {
		return status.DefaultLogLevel
	}

	return logLevel
}

func RetrieveAccessTokensFromBackend() (config.AccessTokens, error) {
	secretBackend, ok := os.LookupEnv("SECRET_BACKEND")
	if !ok {
		secretBackend = ""
	}

	switch secretBackend {
	case "VaultBackend":
		settings, err := config.ClientSettingsFromEnv()
		if err != nil {
			return config.AccessTokens{}, err
		}

		client, err := config.BuildVaultClient(settings)
		if err != nil {
			return config.AccessTokens{}, err
		}

		backend := config.NewSecretsBackendVault(client, settings.MountPoint)
		return backend.Retrieve()

	case "", "FileSystemBackend":
		path := os.Getenv("SECRETS_FILE_PATH")
		if path == "" {
			path = "/adcm/data/var/secrets_v2.json"
		}

		backend := config.NewSecretsBackendFileSystem(path)
		return backend.Retrieve()

	default:
		return config.AccessTokens{}, fmt.Errorf("unexpected value of SECRET_BACKEND=%q", secretBackend)
	}
}
