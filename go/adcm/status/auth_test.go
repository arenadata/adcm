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
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"
	"testing"

	"adcm/config"
)

type roundTripFunc func(*http.Request) (*http.Response, error)

func (f roundTripFunc) RoundTrip(r *http.Request) (*http.Response, error) {
	return f(r)
}

func TestCheckADCMUserTokenConcurrent(t *testing.T) {
	InitLog("", "CRITICAL")

	httpClient := &http.Client{
		Transport: roundTripFunc(func(*http.Request) (*http.Response, error) {
			return &http.Response{
				StatusCode: http.StatusOK,
				Body:       io.NopCloser(strings.NewReader("")),
			}, nil
		}),
	}

	secrets := NewSecretConfig(config.AccessTokens{})
	hub := Hub{
		Secrets: secrets,
		AdcmApi: &AdcmApi{
			Url:        "http://adcm.test",
			httpClient: httpClient,
			Secrets:    secrets,
		},
	}

	const workers = 100
	start := make(chan struct{})
	results := make(chan bool, workers)
	var wg sync.WaitGroup

	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			<-start
			results <- checkADCMUserToken(hub, fmt.Sprintf("token-%d", id))
		}(i)
	}

	close(start)
	wg.Wait()
	close(results)

	for authenticated := range results {
		if !authenticated {
			t.Fatal("expected every concurrent token check to succeed")
		}
	}

	for i := 0; i < workers; i++ {
		if _, ok := secrets.GetADCMToken(fmt.Sprintf("token-%d", i)); !ok {
			t.Fatalf("expected token-%d to be cached", i)
		}
	}
}
