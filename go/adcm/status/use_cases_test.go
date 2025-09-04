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
	"testing"
)

// Utilities

func buildSaveHost(called map[string]string) func(int, int) {
	return func(hid, cid int) {
		called["save"] = fmt.Sprintf("host=%d-cluster=%d", hid, cid)
	}
}
func buildCheckHost(called map[string]string) func(int, int) {
	return func(hid, cid int) {
		called["check"] = fmt.Sprintf("host=%d-cluster=%d", hid, cid)
	}
}

func checkHostsNotInStorageAndHaveDefaultStatus(t *testing.T, storage *Storage, hosts []int) {
	expectedStatus := 16
	for _, hostID := range hosts {
		if status, exists := storage.get(ALL, hostID); exists || status.Status != expectedStatus {
			t.Fatalf("expected hostID=%d to be absent and have status=%d, got status=%d exists=%t", hostID, expectedStatus, status, exists)
		}
	}
}
func checkStatusOfHostsInStorage(t *testing.T, storage *Storage, expectedStatus int, hosts []int) {
	for _, hostID := range hosts {
		if status, exists := storage.get(ALL, hostID); !exists || status.Status != expectedStatus {
			t.Fatalf("expected hostID=%d to be present and have status=%d, got status=%d exists=%t", hostID, expectedStatus, status.Status, exists)
		}
	}
}

// Set UP

type Ctx struct {
	// Callables
	called    map[string]string
	saveHost  func(int, int)
	checkHost func(int, int)

	// Storages / Services
	storage       *Storage
	serviceServer *ServiceServer
	duplicates    *HostDuplicates
}

func setUpCommon(clusterHostMap map[Id][]int) Ctx {
	InitLog("", "critical") // required for correct storage work

	called := map[string]string{"save": "", "check": ""}
	saveHost := buildSaveHost(called)
	checkHost := buildCheckHost(called)

	storage := newStorage(dbMap2{}, "dummy")
	go storage.run()
	serviceServer := newServiceServer()
	go serviceServer.run()

	serviceServer.init(ServiceMaps{Host: clusterHostMap})

	return Ctx{
		called:        called,
		saveHost:      saveHost,
		checkHost:     checkHost,
		storage:       storage,
		serviceServer: serviceServer,
		duplicates:    newHostDuplicates(),
	}
}

// Cases

func TestRegisterHostStatusNoClusterFail(t *testing.T) {
	hostID := 20
	status := 0
	expectedStatus := 409

	ctx := setUpCommon(map[Id][]int{})

	res, err := RegisterHostStatus(hostID, status, ctx.saveHost, ctx.checkHost, ctx.storage, ctx.serviceServer, newHostDuplicates())
	if err == nil || res != expectedStatus {
		t.Fatalf("expected res=%d and err=%v, got res=%d and err=%v", expectedStatus, nil, res, err)
	}

	save, _ := ctx.called["save"]
	check, _ := ctx.called["check"]
	if save != "" || check != "" {
		t.Fatalf("expected save and check not called, got save=%s and check=%s", save, check)
	}
}

func TestRegisterHostStatusWithClusterSuccess(t *testing.T) {
	hostID := 21
	clusterID := 4
	status := 432
	expectedCode := 201
	expectedCalled := fmt.Sprintf("host=%d-cluster=%d", hostID, clusterID)

	ctx := setUpCommon(map[Id][]int{Id(clusterID): {hostID}})

	res, err := RegisterHostStatus(hostID, status, ctx.saveHost, ctx.checkHost, ctx.storage, ctx.serviceServer, newHostDuplicates())
	if err != nil || res != expectedCode {
		t.Fatalf("expected res=%d and nill error, got res=%d and err=%s", expectedCode, res, err)
	}

	save, _ := ctx.called["save"]
	check, _ := ctx.called["check"]
	if save != expectedCalled || check != expectedCalled {
		t.Fatalf("expected save=%s and check=%s, got save=%s and check=%s", expectedCalled, expectedCalled, save, check)
	}

	actualStatus, exists := ctx.storage.get(ALL, hostID)
	if !exists || actualStatus.Status != status {
		t.Fatalf("expected exists=%t and status=%d, got exists=%t and status=%d", true, status, exists, actualStatus.Status)
	}
}

func TestRegisterHostStatusWithDuplicate(t *testing.T) {
	// Prepare
	h1 := 21
	h1Duplicate1 := 43
	h1Duplicate2 := 541
	h2 := 33
	h2Duplicate1 := 40
	h1Status := 20
	h2Status := 99
	clusterID := 8
	expectedH1Result := 409
	expectedH2Result := 201

	ctx := setUpCommon(map[Id][]int{Id(clusterID): {h1Duplicate1, h2}})

	ctx.duplicates.Register(h1, []int{h1Duplicate1, h1Duplicate2})
	ctx.duplicates.Register(h2, []int{h2Duplicate1})

	registerHostStatusUC := func(hid, s int) (int, error) {
		return RegisterHostStatus(hid, s, ctx.saveHost, ctx.checkHost, ctx.storage, ctx.serviceServer, ctx.duplicates)
	}

	// test

	checkHostsNotInStorageAndHaveDefaultStatus(t, ctx.storage, []int{h1, h1Duplicate1, h1Duplicate2, h2, h2Duplicate1})

	res, err := registerHostStatusUC(h1, h1Status)
	if err == nil || res != expectedH1Result {
		t.Fatalf("expected res=%d err=%v, got res=%d err=%q", expectedH1Result, nil, res, err)
	}

	checkStatusOfHostsInStorage(t, ctx.storage, h1Status, []int{h1, h1Duplicate1, h1Duplicate2})
	checkHostsNotInStorageAndHaveDefaultStatus(t, ctx.storage, []int{h2, h2Duplicate1})

	res, err = registerHostStatusUC(h2, h2Status)
	if err != nil || res != expectedH2Result {
		t.Fatalf("expected res=%d err=%v, got res=%d err=%q", expectedH2Result, nil, res, err)
	}

	checkStatusOfHostsInStorage(t, ctx.storage, h1Status, []int{h1, h1Duplicate1, h1Duplicate2})
	checkStatusOfHostsInStorage(t, ctx.storage, h2Status, []int{h2, h2Duplicate1})
}

func TestRegisterHostDuplicatesStatusPropagation(t *testing.T) {
	// const
	original := 42
	duplicate1 := 44
	duplicate2 := 399
	status := 0

	// arrange
	ctx := setUpCommon(map[Id][]int{})
	registerDuplicatesUC := func(o int, d []int) error {
		return RegisterHostDuplicates(o, d, ctx.saveHost, ctx.checkHost, ctx.storage, ctx.serviceServer, ctx.duplicates)
	}

	ctx.storage.set(ALL, original, status, func() {})

	checkStatusOfHostsInStorage(t, ctx.storage, status, []int{original})
	checkHostsNotInStorageAndHaveDefaultStatus(t, ctx.storage, []int{duplicate1, duplicate2})

	// act
	err := registerDuplicatesUC(original, []int{duplicate1, duplicate2})

	// assert
	if err != nil {
		t.Fatalf("error in UC %v", err)
	}
	checkStatusOfHostsInStorage(t, ctx.storage, status, []int{original, duplicate1, duplicate2})
}
