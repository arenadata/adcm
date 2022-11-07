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
	"io"
	"io/ioutil"
	"net/http"
	"net/url"
	"time"
)

const LoadServiceMapTimeOut = 60 // seconds

type AdcmApi struct {
	Url        string
	token      string
	httpClient *http.Client
	Secrets    *SecretConfig
}

func newAdcmApi(secrets *SecretConfig) *AdcmApi {
	return &AdcmApi{
		Url:     "http://127.0.0.1:8000/api/v1",
		Secrets: secrets,
	}
}

func (api *AdcmApi) getClient() *http.Client {
	if api.httpClient == nil {
		api.httpClient = &http.Client{Timeout: 800 * time.Millisecond}
	}
	return api.httpClient
}

func (api *AdcmApi) getToken() (string, bool) {
	if api.token != "" {
		return api.token, true
	}
	resp, err := http.PostForm(api.Url+"/token/",
		url.Values{
			"username": {api.Secrets.ADCMUser.User},
			"password": {api.Secrets.ADCMUser.Password},
		})
	if err != nil {
		logg.E.l("getToken: http error: ", err)
		return "", false
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		logg.E.f("getToken: http status: %s", resp.Status)
		body, err := ioutil.ReadAll(io.LimitReader(resp.Body, MaxPostSize))
		if err == nil {
			logg.E.f("getToken: POST body: '%s'", body)
		}
		return "", false
	}
	body, err := ioutil.ReadAll(io.LimitReader(resp.Body, MaxPostSize))
	if err != nil {
		logg.E.l("getToken: body read error: ", err)
		return "", false
	}
	//logg.D.f("getToken body: %s", body)

	var v struct{ Token string }
	if err := json.Unmarshal(body, &v); err != nil {
		logg.E.l("getToken: json decode error: ", err)
		return "", false
	}
	logg.D.l("getToken: token: ", v.Token)
	api.token = v.Token
	return v.Token, true
}

func (api *AdcmApi) checkAuth(token string) bool {
	client := api.getClient()
	req, _ := http.NewRequest("GET", api.Url+"/rbac/me/", nil)
	req.Header.Add("Authorization", "Token "+token)
	//logg.D.f("checkAuth: client %+v, request %+v", client, req)
	resp, err := client.Do(req)
	if err != nil {
		logg.E.f("checkAuth: http error: %v", err)
		return false
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		logg.W.f("check ADCM token %s fail: %v", token, resp.Status)
		return false
	}
	logg.D.l("checkAuth: check ADCM token ok")
	return true
}

func (api *AdcmApi) checkSessionAuth(sessionId string) bool {
	client := api.getClient()
	req, _ := http.NewRequest("GET", api.Url+"/stack/", nil)
	req.AddCookie(&http.Cookie{Name: "sessionid", Value: sessionId})
	//logg.D.f("checkSessionAuth: client %+v, request %+v", client, req)
	resp, err := client.Do(req)
	if err != nil {
		logg.E.f("checkSessionAuth: http error: %v", err)
		return false
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		logg.W.f("check ADCM sessionId %s fail: %v", sessionId, resp.Status)
		return false
	}
	logg.D.l("checkSessionAuth: check ADCM sessionId ok")
	return true
}

func (api *AdcmApi) loadServiceMap() bool {
	token, ok := api.getToken()
	if !ok {
		return false
	}
	client := api.getClient()
	req, _ := http.NewRequest("PUT", api.Url+"/stack/load/servicemap/", nil)
	req.Header.Add("Authorization", "Token "+token)
	resp, err := client.Do(req)
	if err != nil {
		logg.E.l("loadServiceMap: http error: ", err)
		return false
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		logg.E.f("loadServiceMap: http status: %s", resp.Status)
		body, err := ioutil.ReadAll(io.LimitReader(resp.Body, MaxPostSize))
		if err == nil {
			logg.E.f("loadServiceMap: POST body: '%s'", body)
		}
		return false
	}
	_, err = ioutil.ReadAll(io.LimitReader(resp.Body, MaxPostSize))
	if err != nil {
		logg.E.l("loadServiceMap: body read error: ", err)
		return false
	}
	logg.D.f("loadServiceMap: call /stack/load/servicemap/ got %s response", resp.Status)
	return true
}

func (api *AdcmApi) getServiceMap() {
	if !api.loadServiceMap() {
		go func() {
			time.Sleep(LoadServiceMapTimeOut * time.Second)
			api.getServiceMap()
		}()
	}
}
