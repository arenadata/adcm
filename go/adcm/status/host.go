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

type Host struct {
	Id              int  `json:"id"`
	MaintenanceMode bool `json:"maintenance_mode"`
}

type dbHost map[int]Host

type hostRequest struct {
	command          string
	id               int
	maintenance_mode bool
	hosts            []Host
}

type hostResponse struct {
	ok    bool
	host  Host
	hosts []Host
}

type HostStorage struct {
	in    chan hostRequest
	out   chan hostResponse
	db    dbHost
	label string
}

func newHostStorage(db dbHost, label string) *HostStorage {
	return &HostStorage{
		in:    make(chan hostRequest),
		out:   make(chan hostResponse),
		db:    db,
		label: label,
	}
}

func (hs *HostStorage) run() {
	logg.I.f("start storage %s server", hs.label)
	for {
		request := <-hs.in
		logg.I.f("Storage %s command: %+v", hs.label, request.command)
		switch request.command {
		case "retrieve":
			host, ok := hs.db.retrieve(request.id)
			hs.out <- hostResponse{host: host, ok: ok}
		case "update":
			ok := hs.db.update(request.id, request.maintenance_mode)
			hs.out <- hostResponse{ok: ok}
		case "list":
			hosts := hs.db.list()
			hs.out <- hostResponse{hosts: hosts}
		case "create":
			ok := hs.db.create(request.hosts)
			hs.out <- hostResponse{ok: ok}
		default:
			logg.E.f("Storage %s unknown command: %+v", hs.label, request)

		}
	}
}

func (hs *HostStorage) list() []Host {
	request := hostRequest{command: "list"}
	hs.in <- request
	response := <-hs.out
	return response.hosts
}

func (hs *HostStorage) create(hosts []Host) bool {
	request := hostRequest{command: "create", hosts: hosts}
	hs.in <- request
	response := <-hs.out
	return response.ok
}

func (hs *HostStorage) retrieve(id int) (Host, bool) {
	request := hostRequest{command: "retrieve", id: id}
	hs.in <- request
	response := <-hs.out
	return response.host, response.ok
}

func (hs *HostStorage) update(id int, maintenance_mode bool) bool {
	request := hostRequest{command: "update", id: id, maintenance_mode: maintenance_mode}
	hs.in <- request
	response := <-hs.out
	return response.ok
}

// list - return list Host entities
func (db dbHost) list() []Host {
	result := make([]Host, 0)
	for _, host := range db {
		result = append(result, host)
	}
	return result
}

// retrieve - return Host entity, if this exists in db, else return default entity
func (db dbHost) retrieve(id int) (Host, bool) {
	value, ok := db[id]
	if ok {
		return value, true
	}
	return Host{}, false
}

// update - update Host entity
func (db dbHost) update(id int, maintenance_mode bool) bool {
	host, ok := db[id]
	if !ok {
		return ok
	}
	host.MaintenanceMode = maintenance_mode
	db[id] = host
	return ok
}

// create - clear db and created Host entities
func (db dbHost) create(hosts []Host) bool {
	db.clear()
	for _, host := range hosts {
		db[host.Id] = host
	}
	return true
}

// clear - clear db with Hosts
func (db dbHost) clear() {
	for key := range db {
		delete(db, key)
	}
}
