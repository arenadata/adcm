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
	"strconv"
	"strings"
)

const ALL = 100001

type hostCompStatus struct {
	Host      int `json:"host"`
	Component int `json:"component"`
	Status    int `json:"status"`
}

type serviceStatus struct {
	Status  int              `json:"status"`
	Details []hostCompStatus `json:"details"`
}

type eventMsg struct {
	Event  string `json:"event"`
	Object struct {
		Type    string      `json:"type"`
		Id      int         `json:"id"`
		Details interface{} `json:"details"`
	} `json:"object"`
}

type eventDetail struct {
	Id          string      `json:"id,omitempty"`
	HostId      string      `json:"host_id,omitempty"`
	ComponentId string      `json:"component_id,omitempty"`
	Type        string      `json:"type"`
	Value       interface{} `json:"value"`
}

func (e eventMsg) encode() ([]byte, error) {
	js, err := json.Marshal(e)
	return js, err
}

func newEventMsg4(status int, objType string, objId int, id2 int) eventMsg {
	em := eventMsg{Event: "change_status"}
	em.Object.Type = objType
	em.Object.Id = objId
	em.Object.Details = eventDetail{
		Type:        "status",
		Value:       strconv.Itoa(status),
		Id:          strconv.Itoa(id2),
		HostId:      strconv.Itoa(objId),
		ComponentId: strconv.Itoa(id2),
	}
	return em
}

func newEventMsg(status int, objType string, objId int) eventMsg {
	em := eventMsg{Event: "change_status"}
	em.Object.Type = objType
	em.Object.Id = objId
	em.Object.Details = eventDetail{
		Type:  "status",
		Value: strconv.Itoa(status),
	}
	return em
}

func getServiceStatus(h Hub, cluster int, service int) (Status, []hostCompStatus) {
	hc := []hostCompStatus{}
	hostComp, _ := h.ServiceMap.getServiceHC(cluster, service)
	servStatus := Status{Status: 0}
	for _, key := range hostComp {
		spl := strings.Split(key, ".")
		hostId, _ := strconv.Atoi(spl[0])
		compId, _ := strconv.Atoi(spl[1])
		if h.MMObjects.IsComponentInMM(compId) {
			continue
		}
		host, ok := h.HostStorage.retrieve(hostId)
		if ok && host.MaintenanceMode {
			continue
		}
		status, ok := h.HostComponentStorage.get(hostId, compId)
		if !ok {
			status.Status = 16
		}
		hc = append(hc, hostCompStatus{Host: hostId, Component: compId, Status: status.Status})
		if status.Status != 0 {
			servStatus = status
		}
	}
	return servStatus, hc
}

func getComponentStatus(h Hub, compId int) (Status, map[int]Status) {
	hosts := map[int]Status{}
	hostList, _ := h.ServiceMap.getComponentHosts(compId)
	if len(hostList) == 0 {
		return Status{Status: 32}, hosts
	}

	status := 0
	if h.MMObjects.IsComponentInMM(compId) {
		return Status{Status: status}, hosts
	}

	for _, hostId := range hostList {
		host, ok := h.HostStorage.retrieve(hostId)
		if h.MMObjects.IsHostInMM(hostId) || ok && host.MaintenanceMode {
			continue
		}
		hostStatus, ok := h.HostComponentStorage.get(hostId, compId)
		if !ok {
			hostStatus = Status{Status: 16}
		}
		if hostStatus.Status != 0 {
			status = hostStatus.Status
		}
		hosts[hostId] = hostStatus
	}
	return Status{Status: status}, hosts
}

func getClusterHostStatus(h Hub, clusterId int) (int, map[int]Status) {
	hosts := map[int]Status{}
	hostList, _ := h.ServiceMap.getHosts(clusterId)
	if len(hostList) < 1 {
		return 32, make(map[int]Status)
	}
	result := 0
	for _, hostId := range hostList {
		host, ok := h.HostStorage.retrieve(hostId)
		if ok && host.MaintenanceMode {
			continue
		}
		status, ok := h.HostStatusStorage.get(ALL, hostId)
		if !ok {
			logg.D.f("getClusterHostStatus: no status for host #%v ", hostId)
			status = Status{Status: 16}
		}
		if status.Status != 0 {
			result = status.Status
		}
		hosts[hostId] = status
	}
	return result, hosts
}

func getClusterServiceStatus(h Hub, clusterId int) (int, map[int]serviceStatus) {
	services := map[int]serviceStatus{}
	servList, _ := h.ServiceMap.getServices(clusterId)
	if len(servList) < 1 {
		return 32, make(map[int]serviceStatus)
	}
	result := 0
	for _, serviceId := range servList {
		srvStatus, hcStatus := getServiceStatus(h, clusterId, serviceId)
		services[serviceId] = serviceStatus{
			Status:  srvStatus.Status,
			Details: hcStatus,
		}
		if srvStatus.Status != 0 {
			result = srvStatus.Status
		}
	}
	return result, services
}

func cookClusterStatus(serviceStatus int, hostStatus int) int {
	if serviceStatus != 0 {
		return serviceStatus
	}
	if hostStatus != 0 {
		return hostStatus
	}
	return 0
}

func getClusterStatus(h Hub, clusterId int) Status {
	serviceStatus, _ := getClusterServiceStatus(h, clusterId)
	hostStatus, _ := getClusterHostStatus(h, clusterId)
	return Status{Status: cookClusterStatus(serviceStatus, hostStatus)}
}
