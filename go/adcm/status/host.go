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
}

type hostResponse struct {
	code int
	ok   bool
	host Host
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
			value, ok := hs.db.retrieve(request.id)
			hs.out <- hostResponse{host: value, ok: ok}
		case "update":
			value := hs.db.update(request.id, request.maintenance_mode)
			hs.out <- hostResponse{code: value}
		default:
			logg.E.f("Storage %s unknown command: %+v", hs.label, request)

		}
	}
}

func (hs *HostStorage) retrieve(id int) (Host, bool) {
	request := hostRequest{command: "retrieve", id: id}
	hs.in <- request
	response := <-hs.out
	return response.host, response.ok
}

func (hs *HostStorage) update(id int, maintenance_mode bool) int {
	request := hostRequest{command: "update", id: id, maintenance_mode: maintenance_mode}
	hs.in <- request
	response := <-hs.out
	return response.code
}

// list - return list Host entities
func (db dbHost) list() ([]Host, bool) {
	result := make([]Host, 0)
	for _, host := range db {
		result = append(result, host)
	}
	return result, true
}

// retrieve - return Host entity, if this exists in db, else return default entity
func (db dbHost) retrieve(id int) (Host, bool) {
	value, ok := db[id]
	if ok {
		return value, true
	}
	return Host{Id: id, MaintenanceMode: false}, false
}

// update - updated or created Host entity, implements the PUT method
func (db dbHost) update(id int, maintenance_mode bool) int {
	code := 200
	host, ok := db[id]
	if !ok {
		db[id] = Host{Id: id, MaintenanceMode: maintenance_mode}
		code = 201
	}
	host.Id = id
	host.MaintenanceMode = maintenance_mode
	db[id] = host
	return code
}

// create - clear db and created Host entities
func (db dbHost) create(hosts []Host) int {
	db.clear()
	for _, host := range hosts {
		db[host.Id] = host
	}
	return 201
}

// clear - clear db with Hosts
func (db dbHost) clear() {
	for key := range db {
		delete(db, key)
	}
}

type listHostRequest struct {
	command string
	hosts   []Host
}

type listHostResponse struct {
	code  int
	ok    bool
	hosts []Host
}

type ListHostStorage struct {
	in    chan listHostRequest
	out   chan listHostResponse
	db    dbHost
	label string
}

func newListHostStorage(db dbHost, label string) *ListHostStorage {
	return &ListHostStorage{
		in:    make(chan listHostRequest),
		out:   make(chan listHostResponse),
		db:    db,
		label: label,
	}
}

func (lhs *ListHostStorage) run() {
	logg.I.f("start storage %s server", lhs.label)
	for {
		request := <-lhs.in
		logg.I.f("Storage %s command: %+v", lhs.label, request.command)
		switch request.command {
		case "list":
			value, ok := lhs.db.list()
			lhs.out <- listHostResponse{hosts: value, ok: ok}
		case "create":
			code := lhs.db.create(request.hosts)
			lhs.out <- listHostResponse{code: code}
		}
	}
}

func (lhs *ListHostStorage) list() ([]Host, bool) {
	request := listHostRequest{command: "list"}
	lhs.in <- request
	response := <-lhs.out
	return response.hosts, response.ok
}

func (lhs *ListHostStorage) create(hosts []Host) int {
	request := listHostRequest{command: "create", hosts: hosts}
	lhs.in <- request
	response := <-lhs.out
	return response.code
}
