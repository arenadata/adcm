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
	"strconv"
	"strings"
)

type ClusterService struct {
	Cluster int `json:"cluster"`
	Service int `json:"service"`
}

// ServiceMap:
// HostService:	"host.component" -> (cluster, service))
// Component:   cluster -> service  -> ["host.component"]
// Service:     cluster -> [service]
// Host:        cluster -> [host]
// HostCluster: host -> cluster // computed

// HostComponentStorage:
// host -> component -> Status

// HostStorage:
// "all" -> host -> Status

type ServiceMaps struct {
	Host        map[Id][]int              `json:"host"`
	HostCluster map[Id]int                `json:"hostcluster"`
	Service     map[Id][]int              `json:"service"`
	Component   map[Id]map[Id][]string    `json:"component"`
	HostService map[string]ClusterService `json:"hostservice"`
}

type ssReq struct {
	command  string
	cluster  int
	service  int
	hostcomp string
	smap     ServiceMaps
}

type ssResp struct {
	ok    bool
	value int
	cs    ClusterService
	rmap  []int
	amap  []string
	smap  ServiceMaps
}

type ServiceServer struct {
	in   chan ssReq
	out  chan ssResp
	smap ServiceMaps
}

type Id int

func (i *Id) UnmarshalText(text []byte) error {
	val, err := strconv.Atoi(string(text))
	if err != nil {
		return fmt.Errorf("key %v should be integer", text)
	}
	*i = Id(val)
	return nil
}

// Server

func newServiceServer() *ServiceServer {
	return &ServiceServer{
		in:   make(chan ssReq),
		out:  make(chan ssResp),
		smap: ServiceMaps{},
	}
}

func (s *ServiceServer) run() {
	logg.I.l("start service map server")
	for {
		c := <-s.in
		logg.I.l("ServiceServer command: ", c)
		switch c.command {
		case "init":
			s.smap = initServiceMap(c.smap)
			s.out <- ssResp{ok: true}
		case "getmap":
			s.out <- ssResp{smap: s.smap}
		case "gethosts":
			hosts, ok := s.smap.getHosts(c.cluster)
			s.out <- ssResp{rmap: hosts, ok: ok}
		case "gethostcluster":
			clusterId, ok := s.smap.getHostCluster(c.cluster)
			s.out <- ssResp{value: clusterId, ok: ok}
		case "getclusters":
			clusters, ok := s.smap.getClusters()
			s.out <- ssResp{rmap: clusters, ok: ok}
		case "getallhosts":
			hosts, ok := s.smap.getAllHosts()
			s.out <- ssResp{rmap: hosts, ok: ok}
		case "getservices":
			services, ok := s.smap.getServices(c.cluster)
			s.out <- ssResp{rmap: services, ok: ok}
		case "getservicehc":
			hc, ok := s.smap.getServiceHC(c.cluster, c.service)
			s.out <- ssResp{amap: hc, ok: ok}
		case "gethostcomp":
			cs, ok := s.smap.getHostComponent(c.hostcomp)
			s.out <- ssResp{cs: cs, ok: ok}
		case "getcomphosts":
			hosts := s.smap.getComponentHosts(c.cluster)
			s.out <- ssResp{rmap: hosts, ok: true}
		default:
			logg.E.l("ServiceServer unknown ss command: ", c)
		}
	}
}

// Interface

func (s *ServiceServer) init(sm ServiceMaps) {
	s.in <- ssReq{command: "init", smap: sm}
	<-s.out
}

func (s *ServiceServer) getMap() ServiceMaps {
	s.in <- ssReq{command: "getmap"}
	resp := <-s.out
	return resp.smap
}

func (s *ServiceServer) getServiceIDByComponentID(compId int) (resultServiceID int, found bool) {
	resultServiceID = 0
	found = false
	for hostIDCompIDKey, clusterService := range s.smap.HostService {
		compIdKey, _ := strconv.Atoi(strings.Split(hostIDCompIDKey, ".")[1])
		if compIdKey == compId {
			resultServiceID = clusterService.Service
			found = true
			break
		}
	}
	return
}

func (s *ServiceServer) getHosts(clusterId int) ([]int, bool) {
	s.in <- ssReq{command: "gethosts", cluster: clusterId}
	resp := <-s.out
	return resp.rmap, resp.ok
}

func (s *ServiceServer) getHostCluster(hostId int) (int, bool) {
	s.in <- ssReq{command: "gethostcluster", cluster: hostId}
	resp := <-s.out
	return resp.value, resp.ok
}

func (s *ServiceServer) getClusters() []int {
	s.in <- ssReq{command: "getclusters"}
	resp := <-s.out
	return resp.rmap
}

func (s *ServiceServer) getAllHosts() []int {
	s.in <- ssReq{command: "getallhosts"}
	resp := <-s.out
	return resp.rmap
}

func (s *ServiceServer) getServices(clusterId int) ([]int, bool) {
	s.in <- ssReq{command: "getservices", cluster: clusterId}
	resp := <-s.out
	return resp.rmap, resp.ok
}

func (s *ServiceServer) getServiceHC(clusterId int, serviceId int) ([]string, bool) {
	s.in <- ssReq{command: "getservicehc", cluster: clusterId, service: serviceId}
	resp := <-s.out
	return resp.amap, resp.ok
}

func (s *ServiceServer) getHostComponent(hostComponent string) (ClusterService, bool) {
	s.in <- ssReq{command: "gethostcomp", hostcomp: hostComponent}
	resp := <-s.out
	return resp.cs, resp.ok
}

func (s *ServiceServer) getComponentHosts(compId int) ([]int, bool) {
	s.in <- ssReq{command: "getcomphosts", cluster: compId}
	resp := <-s.out
	return resp.rmap, resp.ok
}

// Internal

func initServiceMap(smap ServiceMaps) ServiceMaps {
	smap.HostCluster = map[Id]int{}
	for clusterId, hosts := range smap.Host {
		for _, hostId := range hosts {
			smap.HostCluster[Id(hostId)] = int(clusterId)
		}
	}
	return smap
}

func (s *ServiceMaps) getHostComponent(hostComponent string) (ClusterService, bool) {
	v, ok := s.HostService[hostComponent]
	return v, ok
}

func (s *ServiceMaps) getComponentHosts(componentId int) []int {
	var hosts []int
	for key := range s.HostService {
		s := strings.Split(key, ".")
		hostId, _ := strconv.Atoi(s[0])
		compId, _ := strconv.Atoi(s[1])
		if compId == componentId {
			hosts = append(hosts, hostId)
		}
	}
	return hosts
}

func (s *ServiceMaps) getHosts(clusterId int) ([]int, bool) {
	v, ok := s.Host[Id(clusterId)]
	return v, ok
}

func (s *ServiceMaps) getHostCluster(hostId int) (int, bool) {
	v, ok := s.HostCluster[Id(hostId)]
	return v, ok
}

func (s *ServiceMaps) getClusters() ([]int, bool) {
	clusters := []int{}
	for clusterId := range s.Service {
		clusters = append(clusters, int(clusterId))
	}
	return clusters, true
}

func (s *ServiceMaps) getAllHosts() ([]int, bool) {
	hosts := []int{}
	for hostId := range s.HostCluster {
		hosts = append(hosts, int(hostId))
	}
	return hosts, true
}

func (s *ServiceMaps) getServices(clusterId int) ([]int, bool) {
	v, ok := s.Service[Id(clusterId)]
	return v, ok
}

func (s *ServiceMaps) getServiceHC(cluster int, service int) ([]string, bool) {
	v, ok := s.Component[Id(cluster)][Id(service)]
	return v, ok
}
