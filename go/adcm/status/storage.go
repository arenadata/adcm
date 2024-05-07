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
	"sync"
	"time"
)

type Status struct {
	Status  int `json:"status"`
	counter int
}

type storageRequest struct {
	command   string
	key1      int
	key2      int
	val       int
	counter   int
	clearFunc func()
}

type storageResponse struct {
	code   int
	ok     bool
	status Status
	map1   map[int]Status
}

type dbMap2 map[int]map[int]Status

const (
	cmdSet   = "set"
	cmdClear = "clear"
	cmdPure  = "pure"
	cmdGet   = "get"
	cmdGet1  = "get1"

	statusTimeOut = 60 // seconds
)

type dbStorage interface {
	set(key1 int, key2 int, val int) int
	get(key1 int, key2 int) (Status, bool)
	get1(key1 int) (map[int]Status, bool)
	getCounter(key1 int, key2 int) int
	clear(key1 int, key2 int, counter int)
	create() dbStorage
}

type Storage struct {
	in      chan storageRequest
	out     chan storageResponse
	dbMap   dbStorage
	timeout int
	label   string
}

// maintenance mode objects

type MMObjectsData struct {
	Services   []int `json:"services"`
	Components []int `json:"components"`
	Hosts      []int `json:"hosts"`
}

type MMObjects struct {
	data  MMObjectsData
	mutex sync.Mutex
}

func newMMObjects() *MMObjects {
	return &MMObjects{
		data: MMObjectsData{},
	}
}

func (mm *MMObjects) IsHostInMM(hostID int) bool {
	return intSliceContains(mm.data.Hosts, hostID)
}

func (mm *MMObjects) IsServiceInMM(serviceID int) bool {
	return intSliceContains(mm.data.Services, serviceID)
}

func (mm *MMObjects) IsComponentInMM(componentID int) bool {
	return intSliceContains(mm.data.Components, componentID)
}

func intSliceContains(a []int, x int) bool {
	for _, n := range a {
		if x == n {
			return true
		}
	}
	return false
}

// Server

func newStorage(db dbStorage, label string) *Storage {
	return &Storage{
		in:      make(chan storageRequest),
		out:     make(chan storageResponse),
		dbMap:   db,
		timeout: statusTimeOut,
		label:   label,
	}
}

func (s *Storage) setTimeOut(timeout int) {
	s.timeout = timeout
}

func (s *Storage) run() {
	logg.I.f("start storage %s server", s.label)
	for {
		c := <-s.in
		logg.I.f("Storage %s command: %+v", s.label, c)
		switch c.command {
		case cmdSet:
			v := s.dbMap.set(c.key1, c.key2, c.val)
			s.startTimer(s.dbMap, c)
			s.out <- storageResponse{code: v}
		case cmdClear:
			s.dbMap.clear(c.key1, c.key2, c.counter)
			if c.clearFunc != nil {
				go c.clearFunc()
			}
		case cmdPure:
			s.dbMap = s.dbMap.create()
			s.out <- storageResponse{ok: true}
		case cmdGet:
			v, ok := s.dbMap.get(c.key1, c.key2)
			s.out <- storageResponse{status: v, ok: ok}
		case cmdGet1:
			v, ok := s.dbMap.get1(c.key1)
			s.out <- storageResponse{map1: v, ok: ok}
		default:
			logg.E.f("Storage %s unknown command: %+v", s.label, c)
		}
	}
}

// Interface

func (s *Storage) set(key1 int, key2 int, val int, clear func()) int {
	req := storageRequest{command: cmdSet, key1: key1, key2: key2, val: val, clearFunc: clear}
	s.in <- req
	resp := <-s.out
	return resp.code
}

func (s *Storage) get(key1 int, key2 int) (Status, bool) {
	req := storageRequest{command: cmdGet, key1: key1, key2: key2}
	s.in <- req
	resp := <-s.out
	return resp.status, resp.ok
}

func (s *Storage) get1(key1 int) (map[int]Status, bool) { //nolint: unused
	s.in <- storageRequest{command: cmdGet1, key1: key1}
	resp := <-s.out
	return resp.map1, resp.ok
}

func (s *Storage) pure() { //nolint: unused
	s.in <- storageRequest{command: cmdPure}
	<-s.out
}

// Internal DB Interface

func (db dbMap2) get(key1 int, key2 int) (Status, bool) {
	val, ok := db[key1][key2]
	if ok {
		return val, true
	}
	return Status{Status: 16}, false
}

func (db dbMap2) get1(key1 int) (map[int]Status, bool) {
	val, ok := db[key1]
	if ok {
		return val, true
	}
	return val, false
}

func (db dbMap2) set(key1 int, key2 int, val int) int {
	var ok bool
	res := 0
	st := Status{}
	if _, ok := db[key1]; !ok {
		db[key1] = map[int]Status{}
	}
	if st, ok = db[key1][key2]; ok {
		st.counter++
		res = 200
	} else {
		res = 201
	}
	st.Status = val
	db[key1][key2] = st
	return res
}

func (db dbMap2) clear(key1 int, key2 int, counter int) {
	oldC := db.getCounter(key1, key2)
	if counter == oldC {
		delete(db[key1], key2)
	}
}

func (db dbMap2) create() dbStorage {
	return dbMap2{}
}

func (db dbMap2) getCounter(key1 int, key2 int) int {
	val := db[key1][key2]
	return val.counter
}

func (s *Storage) startTimer(db dbStorage, c storageRequest) {
	if s.timeout == 0 {
		return
	}
	counter := db.getCounter(c.key1, c.key2)
	c.counter = counter
	c.command = cmdClear
	go func(c storageRequest) {
		time.Sleep(time.Duration(s.timeout) * time.Second)
		s.in <- c
	}(c)
}
