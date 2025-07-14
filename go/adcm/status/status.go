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
	Status     int              `json:"status"`
	Components map[int]Status   `json:"components"`
	Details    []hostCompStatus `json:"details"`
}

type eventMessage struct {
	Event  string      `json:"event"`
	Object EventObject `json:"object"`
}

type EventObject struct {
	Id      int                  `json:"id"`
	Changes *statusChangePayload `json:"changes"`
}

type statusChangePrototype struct {
	Id          int    `json:"id,omitempty"`
	Name        string `json:"name,omitempty"`
	DisplayName string `json:"displayName,omitempty"`
	Version     string `json:"version,omitempty"`
}

type statusChangePayload struct {
	Id              int                        `json:"id,omitempty"`
	Reason          *statusChangeReasonPayload `json:"reason,omitempty"`
	IsBlocking      bool                       `json:"isBlocking,omitempty"`
	Owner           *statusChangeOwnerPayload  `json:"owner,omitempty"`
	Type            string                     `json:"type,omitempty"`
	Cause           string                     `json:"cause,omitempty"`
	Status          string                     `json:"status,omitempty"`
	State           string                     `json:"state,omitempty"`
	Prototype       *statusChangePrototype     `json:"prototype,omitempty"`
	MaintenanceMode string                     `json:"maintenanceMode,omitempty"`
	Name            string                     `json:"name,omitempty"`
	DisplayName     string                     `json:"displayName,omitempty"`
	Description     string                     `json:"description,omitempty"`
	NewPassword     string                     `json:"newPassword,omitempty"`
	CurrentPassword string                     `json:"currentPassword,omitempty"`
	Users           []int                      `json:"users,omitempty"`
	Objects         []int                      `json:"objects,omitempty"`
	Groups          []int                      `json:"groups,omitempty"`
	Role            int                        `json:"role,omitempty"`
	Child           int                        `json:"child,omitempty"`
	Children        []int                      `json:"children,omitempty"`
	Password        string                     `json:"password,omitempty"`
	FirstName       string                     `json:"firstName,omitempty"`
	LastName        string                     `json:"lastName,omitempty"`
	Email           string                     `json:"email,omitempty"`
	IsSuperUser     bool                       `json:"isSuperUser,omitempty"`
}

type statusChangeReasonPayload struct {
	Message     string                          `json:"message"`
	Placeholder *statusChangePlaceholderPayload `json:"placeholder"`
}

type statusChangePlaceholderPayload struct {
	Source *statusChangeSourceTargetJobPayload `json:"source,omitempty"`
	Target *statusChangeSourceTargetJobPayload `json:"target,omitempty"`
	Job    *statusChangeSourceTargetJobPayload `json:"job,omitempty"`
	Owner  *statusChangeOwnerPayload           `json:"owner,omitempty"`
}

type statusChangeSourceTargetJobPayload struct {
	Type   string                     `json:"type"`
	Name   string                     `json:"name"`
	Params *statusChangeParamsPayload `json:"params"`
}

type statusChangeOwnerPayload struct {
	Id   int    `json:"id"`
	Type string `json:"type"`
}

type statusChangeParamsPayload struct {
	AdcmId      int `json:"adcmId,omitempty"`
	ClusterId   int `json:"clusterId,omitempty"`
	ServiceId   int `json:"serviceId,omitempty"`
	ComponentId int `json:"componentId,omitempty"`
	ProviderId  int `json:"providerId,omitempty"`
	HostId      int `json:"hostId,omitempty"`
	ActionId    int `json:"actionId,omitempty"`
	JobId       int `json:"jobId,omitempty"`
	TaskId      int `json:"taskId,omitempty"`
	PrototypeId int `json:"prototypeId,omitempty"`
}

func (e eventMessage) encode() ([]byte, error) {
	js, err := json.Marshal(e)
	return js, err
}

func changeStatusMessage(objectType string, objectId int, status int) eventMessage {
	message := eventMessage{Event: "update_" + objectType}
	message.Object.Id = objectId
	message.Object.Changes = buildStatusPayload(status)
	return message
}

func buildStatusPayload(status int) *statusChangePayload {
	if status == 0 {
		return &statusChangePayload{Status: "up"}
	}

	return &statusChangePayload{Status: "down"}
}

func getServiceStatus(h Hub, cluster int, service int) (Status, []hostCompStatus) {
	hc := []hostCompStatus{}
	hostComp, _ := h.ServiceMap.getServiceHC(cluster, service)
	servStatus := Status{Status: 0}
	for _, key := range hostComp {
		spl := strings.Split(key, ".")
		hostId, _ := strconv.Atoi(spl[0])
		compId, _ := strconv.Atoi(spl[1])
		if h.MMObjects.IsHostInMM(hostId) || h.MMObjects.IsComponentInMM(compId) {
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
		if h.MMObjects.IsHostInMM(hostId) {
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
		if h.MMObjects.IsHostInMM(hostId) {
			continue
		}
		status, ok := h.HostStatusStorage.get(ALL, hostId)
		if !ok {
			logg.D.Printf("getClusterHostStatus: no status for host #%v ", hostId)
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
		componentStatusMap := make(map[int]Status)
		for _, hcStatusEntry := range hcStatus {
			entry, exists := componentStatusMap[hcStatusEntry.Component]
			hostOrComponentInMM := h.MMObjects.IsComponentInMM(hcStatusEntry.Component) || h.MMObjects.IsHostInMM(hcStatusEntry.Host)
			if !exists {
				if hostOrComponentInMM {
					componentStatusMap[hcStatusEntry.Component] = Status{Status: 0}
				} else {
					componentStatusMap[hcStatusEntry.Component] = Status{Status: hcStatusEntry.Status}
				}

				continue
			}

			if hostOrComponentInMM || entry.Status != 0 {
				// it's in MM OR already not ok, no need to calculate
				continue
			}

			componentStatusMap[hcStatusEntry.Component] = Status{Status: hcStatusEntry.Status}
		}
		services[serviceId] = serviceStatus{
			Status:     srvStatus.Status,
			Components: componentStatusMap,
			Details:    hcStatus,
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
