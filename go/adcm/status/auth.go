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
		//logg.D.f("checkADCMUserToken: get token from cache")
		return true
	} else {
		return checkADCMAuth(token)
	}
}

func djangoAuth(r *http.Request, hub Hub) bool {
	sessionId, err := r.Cookie("sessionid")
	if err != nil {
		logg.D.f("no sessionid cookie")
		return false
	}
	return hub.AdcmApi.checkSessionAuth(sessionId.Value)
}

func wsTokenAuth(w http.ResponseWriter, r *http.Request, hub Hub) bool {
	h, ok := r.Header["Sec-Websocket-Protocol"]
	//logg.D.f("wsTokenAuth: headers: %+v", r.Header)
	if !ok {
		ErrOut4(w, r, "AUTH_ERROR", "no \"Sec-WebSocket-Protocol\" header")
		return false
	}
	if len(h) < 1 {
		ErrOut4(w, r, "AUTH_ERROR", "no token")
		return false
	}
	token := ""
	for _, i := range strings.Split(h[0], ",") {
		token = strings.Trim(i, " ")
	}
	if !checkADCMUserToken(hub, token) {
		ErrOut4(w, r, "AUTH_ERROR", "invalid token")
		return false
	}
	return true
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
