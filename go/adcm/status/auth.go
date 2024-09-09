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
	"net/http"
	"strings"
	"time"
)

func checkADCMUserToken(hub Hub, token string) bool {
	checkADCMAuth := func(token string) bool {
		if hub.AdcmApi.checkAuth(token) {
			hub.Secrets.adcmTokens[token] = time.Now().Add(hub.Secrets.tokenTimeOut)
			return true
		} else {
			return false
		}
	}

	val, ok := hub.Secrets.adcmTokens[token]
	if !ok {
		return checkADCMAuth(token)
	}

	if time.Now().Before(val) {
		return true
	}

	return checkADCMAuth(token)
}

func djangoAuth(r *http.Request, hub Hub) bool {
	sessionId, err := r.Cookie("sessionid")
	if err != nil {
		logg.D.Println("No sessionid cookie")
		return false
	}
	return hub.AdcmApi.checkSessionAuth(sessionId.Value)
}

func canAuthWithWebSocketHeaderCredentials(r *http.Request, hub Hub) bool {
	header, ok := r.Header["Sec-Websocket-Protocol"]
	if !ok || len(header) < 1 {
		return false
	}

	// we expect that `header[0]` is something like "adcm, sometoken"
	splittedHeader := strings.Split(header[0], ",")
	if len(splittedHeader) < 2 {
		// format is not the one we've expected
		return false
	}

	return checkADCMUserToken(hub, strings.Trim(splittedHeader[1], " "))
}

func getAuthorizationToken(r *http.Request) string {
	h, ok := r.Header["Authorization"]
	if !ok {
		return ""
	}
	a := strings.Split(h[0], " ")
	if len(a) < 2 {
		return ""
	}
	if strings.Title(a[0]) != "Token" {
		return ""
	}
	return a[1]
}

// access control

type authCheckerFunc func(*http.Request, Hub) bool

func isADCM(r *http.Request, hub Hub) bool {
	return getAuthorizationToken(r) == hub.Secrets.ADCMInternalToken
}

func isStatusChecker(r *http.Request, hub Hub) bool {
	return getAuthorizationToken(r) == hub.Secrets.Token
}

func isADCMUser(r *http.Request, hub Hub) bool {
	return djangoAuth(r, hub) || checkADCMUserToken(hub, getAuthorizationToken(r))
}
