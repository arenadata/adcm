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

import "time"

type Status struct {
	Status  int `json:"status"`
	counter int
}

type storageReq struct {
	command string
	key1    int
	key2    int
	val     int
	counter int
}

type storageResp struct {
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
	in      chan storageReq
	out     chan storageResp
	dbMap   dbStorage
	timeout int
	label   string
}

// Server

func newStorage(db dbStorage, label string) *Storage {
	return &Storage{
		in:      make(chan storageReq),
		out:     make(chan storageResp),
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
			s.out <- storageResp{code: v}
		case cmdClear:
			s.dbMap.clear(c.key1, c.key2, c.counter)
		case cmdPure:
			s.dbMap = s.dbMap.create()
			s.out <- storageResp{ok: true}
		case cmdGet:
			v, ok := s.dbMap.get(c.key1, c.key2)
			s.out <- storageResp{status: v, ok: ok}
		case cmdGet1:
			v, ok := s.dbMap.get1(c.key1)
			s.out <- storageResp{map1: v, ok: ok}
		default:
			logg.E.f("Storage %s unknown command: %+v", s.label, c)
		}
	}
}

// Interface

func (s *Storage) set(key1 int, key2 int, val int) int {
	req := storageReq{command: cmdSet, key1: key1, key2: key2, val: val}
	s.in <- req
	resp := <-s.out
	return resp.code
}

func (s *Storage) get(key1 int, key2 int) (Status, bool) {
	req := storageReq{command: cmdGet, key1: key1, key2: key2}
	s.in <- req
	resp := <-s.out
	return resp.status, resp.ok
}

func (s *Storage) get1(key1 int) (map[int]Status, bool) { //nolint: unused
	s.in <- storageReq{command: cmdGet1, key1: key1}
	resp := <-s.out
	return resp.map1, resp.ok
}

func (s *Storage) pure() { //nolint: unused
	s.in <- storageReq{command: cmdPure}
	<-s.out
}

// Internal DB Interface

func (db dbMap2) get(key1 int, key2 int) (Status, bool) {
	val, ok := db[key1][key2]
	if ok {
		return val, true
	}
	return val, false
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

func (s *Storage) startTimer(db dbStorage, c storageReq) {
	if s.timeout == 0 {
		return
	}
	counter := db.getCounter(c.key1, c.key2)
	c.counter = counter
	c.command = cmdClear
	go func(c storageReq) {
		time.Sleep(time.Duration(s.timeout) * time.Second)
		s.in <- c
	}(c)
}
