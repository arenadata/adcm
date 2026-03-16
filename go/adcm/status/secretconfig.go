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
	"adcm/config"
	"time"
)

type SecretConfig struct {
	AccessTokens config.AccessTokens
	adcmTokens   map[string]time.Time
	tokenTimeOut time.Duration
}

func NewSecretConfig(accessTokens config.AccessTokens) *SecretConfig {
	return &SecretConfig{
		AccessTokens: accessTokens,
		adcmTokens:   map[string]time.Time{},
		tokenTimeOut: 60 * time.Minute,
	}
}
