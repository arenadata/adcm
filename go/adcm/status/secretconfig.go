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
	"sync"
	"time"

	"adcm/config"
)

type SecretConfig struct {
	AccessTokens config.AccessTokens
	adcmTokens   map[string]time.Time
	tokenTimeOut time.Duration
	mu           sync.RWMutex
}

func NewSecretConfig(accessTokens config.AccessTokens) *SecretConfig {
	return &SecretConfig{
		AccessTokens: accessTokens,
		adcmTokens:   map[string]time.Time{},
		tokenTimeOut: 60 * time.Minute,
	}
}

func (sc *SecretConfig) SetADCMToken(token string) {
	sc.mu.Lock()
	defer sc.mu.Unlock()

	sc.adcmTokens[token] = time.Now().Add(sc.tokenTimeOut)
}

func (sc *SecretConfig) GetADCMToken(token string) (time.Time, bool) {
	sc.mu.RLock()
	defer sc.mu.RUnlock()

	val, ok := sc.adcmTokens[token]
	return val, ok
}
