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
	"sync"
)

type StatusHolder struct {
	cluster   Status
	service   Status
	component Status
	host      Status
	hostComp  Status
}

type StatusEvent struct {
	db    map[string]StatusHolder
	mutex sync.Mutex
}

func newStatusEvent() *StatusEvent {
	return &StatusEvent{
		db: map[string]StatusHolder{},
	}
}

func (se *StatusEvent) save_hc(h Hub, hostId int, compId int, hc ClusterService) {
	sh := fill_hc_status(h, hostId, compId, hc)
	se.write(fmt.Sprintf("hc.%d.%d", hostId, compId), sh)
	se.write(fmt.Sprintf("cluster.%d", hc.Cluster), sh)
}

func (se *StatusEvent) save_host(h Hub, hostId int, clusterId int) {
	sh := fill_host_status(h, hostId, clusterId)
	se.write(fmt.Sprintf("host.%d", hostId), sh)
	se.write(fmt.Sprintf("cluster.%d", clusterId), sh)
}

func (se *StatusEvent) check_hc(h Hub, hostId int, compId int, hc ClusterService) {
	key := fmt.Sprintf("hc.%d.%d", hostId, compId)
	cluster_key := fmt.Sprintf("cluster.%d", hc.Cluster)
	old := se.read(key)
	new := fill_hc_status(h, hostId, compId, hc)
	if old.component.Status != new.component.Status {
		h.EventWS.send2ws(changeStatusMessage("component", compId, new.component.Status))
	}
	if old.service.Status != new.service.Status {
		h.EventWS.send2ws(changeStatusMessage("service", hc.Service, new.service.Status))
	}
	old = se.read(cluster_key)
	if old.cluster.Status != new.cluster.Status {
		h.EventWS.send2ws(changeStatusMessage("cluster", hc.Cluster, new.cluster.Status))
	}
	se.write(key, new)
	se.write(cluster_key, new)
}

func (se *StatusEvent) check_host(h Hub, hostId int, clusterId int) {
	key := fmt.Sprintf("host.%d", hostId)
	cluster_key := fmt.Sprintf("cluster.%d", clusterId)
	old := se.read(key)
	new := fill_host_status(h, hostId, clusterId)
	if old.host.Status != new.host.Status {
		h.EventWS.send2ws(changeStatusMessage("host", hostId, new.host.Status))
	}
	old = se.read(cluster_key)
	if old.cluster.Status != new.cluster.Status {
		h.EventWS.send2ws(changeStatusMessage("cluster", clusterId, new.cluster.Status))
	}
	se.write(key, new)
	se.write(cluster_key, new)
}

func (se *StatusEvent) write(key string, sh StatusHolder) {
	se.mutex.Lock()
	defer se.mutex.Unlock()
	se.db[key] = sh
}

func (se *StatusEvent) read(key string) StatusHolder {
	se.mutex.Lock()
	defer se.mutex.Unlock()
	return se.db[key]
}

func fill_hc_status(h Hub, hostId int, compId int, hc ClusterService) StatusHolder {
	sh := StatusHolder{}
	sh.component, _ = getComponentStatus(h, compId)
	sh.service, _ = getServiceStatus(h, hc.Cluster, hc.Service)
	sh.cluster = getClusterStatus(h, hc.Cluster)
	sh.hostComp, _ = h.HostComponentStorage.get(hostId, compId)
	return sh
}

func fill_host_status(h Hub, hostId int, clusterId int) StatusHolder {
	ClusterStatus := getClusterStatus(h, clusterId)
	HostStatus, _ := h.HostStatusStorage.get(ALL, hostId)
	return StatusHolder{
		cluster: ClusterStatus,
		host:    HostStatus,
	}
}
