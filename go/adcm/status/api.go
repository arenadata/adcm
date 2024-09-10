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
		logg.E.Printf("getToken: http error: %v", err)
		return "", false
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		logg.E.Printf("getToken: http status: %s", resp.Status)
		body, err := ioutil.ReadAll(io.LimitReader(resp.Body, MaxPostSize))
		if err == nil {
			logg.E.Printf("getToken: POST body: %q", body)
		}
		return "", false
	}
	body, err := ioutil.ReadAll(io.LimitReader(resp.Body, MaxPostSize))
	if err != nil {
		logg.E.Printf("getToken: body read error: %v", err)
		return "", false
	}

	var v struct{ Token string }
	if err := json.Unmarshal(body, &v); err != nil {
		logg.E.Printf("getToken: json decode error: %v", err)
		return "", false
	}

	api.token = v.Token
	return v.Token, true
}

func (api *AdcmApi) checkAuth(token string) bool {
	client := api.getClient()
	req, _ := http.NewRequest("GET", api.Url+"/rbac/me/", nil)
	req.Header.Add("Authorization", "Token "+token)
	resp, err := client.Do(req)
	if err != nil {
		logg.E.Printf("checkAuth: http error: %v", err)
		return false
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		logg.W.Printf("check ADCM token %s fail: %v", token, resp.Status)
		return false
	}
	logg.D.Println("checkAuth: check ADCM token ok")
	return true
}

func (api *AdcmApi) checkSessionAuth(sessionId string) bool {
	client := api.getClient()
	req, _ := http.NewRequest("GET", api.Url+"/stack/", nil)
	req.AddCookie(&http.Cookie{Name: "sessionid", Value: sessionId})
	//logg.D.Printf(checkSessionAuth: client %+v, request %+v", client, req)
	resp, err := client.Do(req)
	if err != nil {
		logg.E.Printf("checkSessionAuth: http error: %v", err)
		return false
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		logg.W.Printf("check ADCM sessionId %s fail: %v", sessionId, resp.Status)
		return false
	}
	logg.D.Println("checkSessionAuth: check ADCM sessionId ok")
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
		logg.E.Println("loadServiceMap: http error: ", err)
		return false
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		logg.E.Printf("loadServiceMap: http status: %s", resp.Status)
		body, err := ioutil.ReadAll(io.LimitReader(resp.Body, MaxPostSize))
		if err == nil {
			logg.E.Printf("loadServiceMap: POST body: '%s'", body)
		}
		return false
	}
	_, err = ioutil.ReadAll(io.LimitReader(resp.Body, MaxPostSize))
	if err != nil {
		logg.E.Println("loadServiceMap: body read error: ", err)
		return false
	}
	logg.D.Printf("loadServiceMap: call /stack/load/servicemap/ got %s response", resp.Status)
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
