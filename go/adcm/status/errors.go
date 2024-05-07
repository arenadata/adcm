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
	"net/http"
)

type ApiErr struct {
	Msg      string `json:"desc"`
	httpCode int
	Level    string `json:"level"`
	Code     string `json:"code"`
}

const (
	WARNING  = "warning"
	ERROR    = "error"
	CRITICAL = "critical"
)

var apiErrors = map[string]ApiErr{
	"AUTH_ERROR":        {"authorization error", 401, ERROR, ""},
	"JSON_ERROR":        {"json decoding error", 400, ERROR, ""},
	"FIELD_REQUIRED":    {"field is required", 400, ERROR, ""},
	"INPUT_ERROR":       {"input error", 400, ERROR, ""},
	"INPUT_WARNING":     {"input warning", 400, WARNING, ""},
	"WRONG_INPUT_TYPE":  {"wrong input type", 400, ERROR, ""},
	"SERVICE_NOT_FOUND": {"service doesn't exist", 404, ERROR, ""},
	"HOST_NOT_FOUND":    {"host doesn't exist", 404, ERROR, ""},
	"HC_NOT_FOUND":      {"host component doesn't exist", 404, ERROR, ""},
	"STATUS_UNDEFINED":  {"status is undefined", 409, WARNING, ""},
	"LOG_ERROR":         {"log error", 409, ERROR, ""},
	"PAGE_NOT_FOUND":    {"page not found", 404, WARNING, ""},
	"UNKNOWN_ERROR":     {"unknown error", 501, CRITICAL, ""},
}

func GetErr(code string) ApiErr {
	err, ok := apiErrors[code]
	if ok {
		err.Code = code
		return err
	} else {
		unCode := "UNKNOWN_ERROR"
		unErr := apiErrors[unCode]
		unErr.Code = unCode
		return unErr
	}
}

func GetErr2(code string, desc string) ApiErr {
	err := GetErr(code)
	err.Msg = desc
	return err
}

func ErrOut(w http.ResponseWriter, r *http.Request, errCode string) {
	apiErr := GetErr(errCode)
	errOut(w, r, apiErr)
}

func ErrOut4(w http.ResponseWriter, r *http.Request, errCode string, desc string) {
	apiErr := GetErr(errCode)
	apiErr.Msg = desc
	errOut(w, r, apiErr)
}

func errOut(w http.ResponseWriter, r *http.Request, apiErr ApiErr) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(apiErr.httpCode)
	json.NewEncoder(w).Encode(apiErr) //nolint: errcheck
	logg.W.f("%s %s", apiErr.Code, apiErr.Msg)
	logg.I.f("%s %s %d", r.Method, r.URL.Path, apiErr.httpCode)
}
