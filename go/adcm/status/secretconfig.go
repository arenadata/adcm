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

package status

import (
	"encoding/json"
	"log"
	"os"
	"time"
)

type SecretConfig struct {
	ADCMUser struct {
		User     string `json:"user"`
		Password string `json:"password"`
	} `json:"adcmuser"`
	Token             string `json:"token"`
	ADCMInternalToken string `json:"adcm_internal_token"`
	adcmTokens        map[string]time.Time
	tokenTimeOut      time.Duration
}

func ReadSecret(filename *string) *SecretConfig {
	var config SecretConfig

	file, err := os.Open(*filename)
	if err != nil {
		panic(err)
	}
	defer file.Close()

	jsonParser := json.NewDecoder(file)
	if err := jsonParser.Decode(&config); err != nil {
		log.Fatalf("Can't decode json file %s: %v", *filename, err)
	}
	config.adcmTokens = map[string]time.Time{}
	config.tokenTimeOut = 60 * time.Minute
	return &config
}
