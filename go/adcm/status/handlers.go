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
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"net/http"
	"strconv"

	"github.com/bouk/httprouter"
)

const MaxPostSize = 10 * 1024 * 1024

type clusterDetails struct {
	Status   int                   `json:"status"`
	Services map[int]serviceStatus `json:"services"`
	Hosts    map[int]Status        `json:"hosts"`
}

// Handlers

func index(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html")
	fmt.Fprint(w, "<a href=\"api/v1/\">Status Server API</a>\n")
	logg.I.f("%s %s %d\n", r.Method, r.URL.Path, 200)
}

func apiRoot(w http.ResponseWriter, r *http.Request) {
	allow(w, "GET")
	url := "http://" + r.Host + r.URL.Path
	root := map[string]string{
		"event":      url + "event/",
		"log":        url + "log/",
		"cluster":    url + "cluster/",
		"host":       url + "host/",
		"servicemap": url + "servicemap/",
	}
	jsonOut(w, r, root)
}

func showAll(h Hub, w http.ResponseWriter, r *http.Request) {
	allow(w, "GET")
	clusterOut := map[int]clusterDetails{}
	clusters := h.ServiceMap.getClusters()
	for _, clusterId := range clusters {
		servStatus, services := getClusterServiceStatus(h, clusterId)
		hostStatus, hosts := getClusterHostStatus(h, clusterId)
		clusterStatus := cookClusterStatus(servStatus, hostStatus)
		clusterOut[clusterId] = clusterDetails{
			Services: services,
			Hosts:    hosts,
			Status:   clusterStatus,
		}
	}
	hostOut := map[int]Status{}
	hosts := h.ServiceMap.getAllHosts()
	for _, hostId := range hosts {
		val, _ := h.HostStatusStorage.get(ALL, hostId)
		hostOut[hostId] = val
	}
	all := struct {
		Clusters map[int]clusterDetails `json:"clusters"`
		Hosts    map[int]Status         `json:"hosts"`
	}{
		Clusters: clusterOut,
		Hosts:    hostOut,
	}
	jsonOut(w, r, all)
}

func clusterList(h Hub, w http.ResponseWriter, r *http.Request) {
	allow(w, "GET")
	clusterOut := []struct {
		Url string `json:"url"`
	}{}
	url := "http://" + r.Host + r.URL.Path
	clusters := h.ServiceMap.getClusters()
	for _, clusterId := range clusters {
		clusterOut = append(clusterOut, struct {
			Url string `json:"url"`
		}{
			Url: fmt.Sprintf("%s%d/", url, clusterId),
		})
	}
	jsonOut(w, r, clusterOut)
}

func hostList(h Hub, w http.ResponseWriter, r *http.Request) {
	allow(w, "GET")
	hostOut := []struct {
		Url string `json:"url"`
	}{}
	url := "http://" + r.Host + r.URL.Path
	hosts := h.ServiceMap.getAllHosts()
	for _, hostId := range hosts {
		hostOut = append(hostOut, struct {
			Url string `json:"url"`
		}{
			fmt.Sprintf("%s%d/", url, hostId),
		})
	}
	jsonOut(w, r, hostOut)
}

func readConfig(h Hub, w http.ResponseWriter, r *http.Request) {
	ok := h.AdcmApi.loadServiceMap()
	jsonOut(w, r, map[string]bool{"ok": ok})
}

func showLogLevel(h Hub, w http.ResponseWriter, r *http.Request) {
	jsonOut(w, r, struct {
		Level string `json:"level"`
	}{Level: logg.getLogLevel()})
}

func postLogLevel(h Hub, w http.ResponseWriter, r *http.Request) {
	level := struct {
		Level string `json:"level"`
	}{}
	if _, err := decodeBody(w, r, &level); err != nil {
		return
	}
	intLevel, err := logg.decodeLogLevel(level.Level)
	if err != nil {
		ErrOut4(w, r, "LOG_ERROR", err.Error())
		return
	}
	logg.set(intLevel)
}

func showHostComp(h Hub, w http.ResponseWriter, r *http.Request) {
	allow(w, "GET, POST")
	hostId, ok1 := getPathId(w, r, "hostid")
	compId, ok2 := getPathId(w, r, "compid")
	if !ok1 || !ok2 {
		return
	}
	val, _ := h.HostComponentStorage.get(hostId, compId)
	jsonOut(w, r, val)
}

func showComp(h Hub, w http.ResponseWriter, r *http.Request) {
	allow(w, "GET")
	compId, ok := getPathId(w, r, "compid")
	if !ok {
		return
	}

	status, hosts := getComponentStatus(h, compId)
	if isUIview(r) {
		out := struct {
			Status int            `json:"status"`
			Hosts  map[int]Status `json:"hosts"`
		}{
			Hosts:  hosts,
			Status: status.Status,
		}
		jsonOut(w, r, out)
	} else {
		jsonOut(w, r, status)
	}
}

func showCluster(h Hub, w http.ResponseWriter, r *http.Request) {
	allow(w, "GET")
	clusterId, ok := getPathId(w, r, "clusterid")
	if !ok {
		return
	}
	servStatus, services := getClusterServiceStatus(h, clusterId)
	hostStatus, hosts := getClusterHostStatus(h, clusterId)
	clusterStatus := cookClusterStatus(servStatus, hostStatus)
	if isUIview(r) {
		out := clusterDetails{
			Services: services,
			Hosts:    hosts,
			Status:   clusterStatus,
		}
		jsonOut(w, r, out)
	} else {
		out := struct {
			Status int `json:"status"`
		}{
			Status: clusterStatus,
		}
		jsonOut(w, r, out)
	}
}

func showService(h Hub, w http.ResponseWriter, r *http.Request) {
	allow(w, "GET")
	clusterId, ok1 := getPathId(w, r, "clusterid")
	serviceId, ok2 := getPathId(w, r, "serviceid")
	if !ok1 || !ok2 {
		return
	}
	servStatus, hc := getServiceStatus(h, clusterId, serviceId)
	if isUIview(r) {
		out := struct {
			Components []hostCompStatus `json:"components"`
			Status     int              `json:"status"`
		}{
			hc, servStatus.Status,
		}
		jsonOut(w, r, out)
	} else {
		jsonOut(w, r, servStatus)
	}
}

func checkEvent(e eventMessage, w http.ResponseWriter, r *http.Request) bool {
	if e.Event == "" {
		ErrOut4(w, r, "FIELD_REQUIRED", "field \"event\" is required")
		return false
	}
	if e.Object.Id == 0 {
		ErrOut4(w, r, "FIELD_REQUIRED", "field \"object.id\" is required")
		return false
	}
	return true
}

func postEvent(h Hub, w http.ResponseWriter, r *http.Request) {
	allow(w, "POST")
	event := eventMessage{}
	body, err := decodeBody(w, r, &event)
	if err != nil {
		return
	}
	logg.D.f("postEvent - %+v", event)
	if !checkEvent(event, w, r) {
		logg.W.f("POST body: '%s'", body)
		return
	}
	h.EventWS.send2ws(event)
	jsonOut(w, r, "")
}

func getPostStatus(w http.ResponseWriter, r *http.Request) (int, error) {
	status := Status{}
	_, err := decodeBody(w, r, &status)
	return status.Status, err
}

func setHost(h Hub, w http.ResponseWriter, r *http.Request) {
	allow(w, "GET, POST")
	hostId, ok := getPathId(w, r, "hostid")
	if !ok {
		return
	}
	status, err := getPostStatus(w, r)
	if err != nil {
		return
	}
	clusterId, ok := h.ServiceMap.getHostCluster(hostId)
	if !ok {
		ErrOut4(w, r, "HOST_NOT_FOUND", "unknown host")
		return
	}
	h.StatusEvent.save_host(h, hostId, clusterId)
	clear := func() {
		h.StatusEvent.check_host(h, hostId, clusterId)
	}
	res := h.HostStatusStorage.set(ALL, hostId, status, clear)
	h.StatusEvent.check_host(h, hostId, clusterId)
	jsonOut3(w, r, "", res)
}

func showHost(h Hub, w http.ResponseWriter, r *http.Request) {
	allow(w, "GET, POST")
	hostId, ok := getPathId(w, r, "hostid")
	if !ok {
		return
	}
	_, ok = h.ServiceMap.getHostCluster(hostId)
	if !ok {
		ErrOut4(w, r, "HOST_NOT_FOUND", "unknown host")
		return
	}
	val, _ := h.HostStatusStorage.get(ALL, hostId)
	jsonOut(w, r, val)
}

func setHostComp(h Hub, w http.ResponseWriter, r *http.Request) {
	allow(w, "GET, POST")
	hostId, ok1 := getPathId(w, r, "hostid")
	compId, ok2 := getPathId(w, r, "compid")
	if !ok1 || !ok2 {
		return
	}
	status, err := getPostStatus(w, r)
	if err != nil {
		return
	}
	key := fmt.Sprintf("%d.%d", hostId, compId)
	hc, ok := h.ServiceMap.getHostComponent(key)
	if !ok {
		msg := fmt.Sprintf("Component #%d is not present on host #%d", compId, hostId)
		ErrOut4(w, r, "HC_NOT_FOUND", msg)
		return
	}
	h.StatusEvent.save_hc(h, hostId, compId, hc)
	clear := func() {
		h.StatusEvent.check_hc(h, hostId, compId, hc)
	}
	res := h.HostComponentStorage.set(hostId, compId, status, clear)
	h.StatusEvent.check_hc(h, hostId, compId, hc)
	jsonOut3(w, r, "", res)
}

func showServiceMap(h Hub, w http.ResponseWriter, r *http.Request) {
	allow(w, "GET, POST")
	jsonOut(w, r, h.ServiceMap.getMap())
}

func postServiceMap(h Hub, w http.ResponseWriter, r *http.Request) {
	allow(w, "GET, POST")
	var m ServiceMaps
	_, err := decodeBody(w, r, &m)
	if err != nil {
		ErrOut4(w, r, "JSON_ERROR", err.Error())
		return
	}
	logg.D.f("postServiceMap: %+v", m)
	if len(m.HostService) < 1 {
		logg.W.f("%s %s", "INPUT_WARNING", "no HostService in servicemap post")
	}
	if len(m.Component) < 1 {
		logg.W.f("%s %s", "INPUT_WARNING", "no Component in servicemap post")
	}
	h.ServiceMap.init(m)
	// h.ServiceStorage.pure()
}

func postMMObjects(h Hub, w http.ResponseWriter, r *http.Request) {
	allow(w, "POST")
	h.MMObjects.mutex.Lock()
	defer h.MMObjects.mutex.Unlock()

	var mmData MMObjectsData
	if _, err := decodeBody(w, r, &mmData); err != nil {
		ErrOut4(w, r, "JSON_ERROR", err.Error())
		return
	}
	h.MMObjects.data = mmData
}

func getMMObjects(h Hub, w http.ResponseWriter, r *http.Request) {
	allow(w, "GET")
	jsonOut(w, r, h.MMObjects.data)
}

// Helpers

func getGet(r *http.Request, key string) (string, bool) {
	keys, ok := r.URL.Query()[key]
	if !ok || len(keys) < 1 {
		return "", false
	}
	return keys[0], true
}

func isUIview(r *http.Request) bool {
	view, ok := getGet(r, "view")
	if ok && view == "interface" {
		return true
	}
	return false
}

func getPathId(w http.ResponseWriter, r *http.Request, name string) (int, bool) {
	val := httprouter.GetParam(r, name)
	intVal, err := strconv.Atoi(val)
	if err != nil {
		msg := fmt.Sprintf("'%s' path parameter should be integer, not '%s'", name, val)
		ErrOut4(w, r, "WRONG_INPUT_TYPE", msg)
		return 0, false
	}
	return intVal, true
}

func decodeBody(w http.ResponseWriter, r *http.Request, v interface{}) ([]byte, error) {
	body, err := ioutil.ReadAll(io.LimitReader(r.Body, MaxPostSize))
	r.Body.Close()
	if err != nil {
		ErrOut4(w, r, "INPUT_ERROR", err.Error())
		return body, err
	}
	decoder := json.NewDecoder(bytes.NewReader(body))
	decoder.DisallowUnknownFields()
	err = decoder.Decode(v)
	if err != nil {
		ErrOut4(w, r, "JSON_ERROR", err.Error())
		logg.W.f("POST body: '%s'", body)
		return body, err
	}
	return body, nil
}

func allow(w http.ResponseWriter, methods string) {
	w.Header().Set("Allow", methods)
}

func jsonOut(w http.ResponseWriter, r *http.Request, out interface{}) {
	jsonOut3(w, r, out, http.StatusOK)
}

func jsonOut3(w http.ResponseWriter, r *http.Request, out interface{}, status_code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status_code)
	if out != "" {
		if err := json.NewEncoder(w).Encode(out); err != nil {
			logg.E.f("JSON out error: %v, (%v)", err, out)
		}
	}
	logg.I.f("%s %s %d", r.Method, r.URL.Path, status_code)
}
