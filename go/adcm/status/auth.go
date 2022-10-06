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

func checkADCMToken(hub Hub, token string) bool {
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
		//logg.D.f("checkADCMToken: get token from cache")
		return true
	} else {
		return checkADCMAuth(token)
	}
}

func checkToken(hub Hub, token string, allow_adcm_session bool) bool {
	if token != hub.Secrets.Token {
	    if allow_adcm_session && checkADCMToken(hub, token) {
	        return true
	    }
		return false
	}
	return true
}

func djangoAuth(r *http.Request, hub Hub) bool {
	sessionId, err := r.Cookie("sessionid")
	if err != nil {
		logg.D.f("no sessionid cookie")
		return false
	}
	return hub.AdcmApi.checkSessionAuth(sessionId.Value)
}

func tokenAuth(w http.ResponseWriter, r *http.Request, hub Hub, allow_adcm_session bool) bool {
    if allow_adcm_session {
        if djangoAuth(r, hub) {
            return true
        }
    }
    h, ok := r.Header["Authorization"]
    if !ok {
        ErrOut4(w, r, "AUTH_ERROR", "no \"Authorization\" header")
        return false
    }
    a := strings.Split(h[0], " ")
    if len(a) < 2 {
        ErrOut4(w, r, "AUTH_ERROR", "no token")
        return false
    }
    if strings.Title(a[0]) != "Token" {
        ErrOut4(w, r, "AUTH_ERROR", "no token")
        return false
    }
    if !checkToken(hub, a[1], allow_adcm_session) {
        ErrOut4(w, r, "AUTH_ERROR", "invalid token")
        return false
    }
    return true
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
	if !checkToken(hub, token, true) {
		ErrOut4(w, r, "AUTH_ERROR", "invalid token")
		return false
	}
	return true
}
