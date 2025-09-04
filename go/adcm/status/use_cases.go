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

import "errors"

func doNotClear() {}

// CASE: Register Host Status

// Get HostID and "alive" status integer, returns "HTTP Response Status Code"
func RegisterHostStatus(
	hostID int,
	status int,
	// functions too difficult to decouple for now
	saveHost func(int, int),
	checkHost func(int, int),
	// storages
	hostStatusStorage *Storage,
	serviceServer *ServiceServer,
	hostDuplicates *HostDuplicates,
) (int, error) {

	register := func(hid int) (int, error) {
		return registerHostStatus(
			hid,
			status,
			saveHost,
			checkHost,
			hostStatusStorage,
			serviceServer,
		)
	}

	// Return result as if this host was original and no duplicates exist
	res, err := register(hostID)

	for _, duplicateID := range hostDuplicates.GetForID(hostID) {
		register(duplicateID)
	}

	return res, err
}

func registerHostStatus(
	hostID int,
	status int,
	saveHost func(int, int),
	checkHost func(int, int),
	hostStatusStorage *Storage,
	serviceServer *ServiceServer,
) (int, error) {
	clearFunc := doNotClear
	clusterId, isHostBoundToCluster := serviceServer.getHostCluster(hostID)
	if isHostBoundToCluster {
		saveHost(hostID, clusterId)
		clearFunc = func() { checkHost(hostID, clusterId) }
	}

	res := hostStatusStorage.set(ALL, hostID, status, clearFunc)
	clearFunc()

	if isHostBoundToCluster {
		return res, nil
	}

	return 409, errors.New("host is not bound to cluster")
}

// CASE: Register Host Duplicates

func RegisterHostDuplicates(
	original int,
	duplicates []int,
	// functions too difficult to decouple for now
	saveHost func(int, int),
	checkHost func(int, int),
	// storages
	hostStatusStorage *Storage,
	serviceServer *ServiceServer,
	hostDuplicates *HostDuplicates,
) error {
	hostDuplicates.Register(original, duplicates)

	if originalStatus, exists := hostStatusStorage.get(ALL, original); exists {
		for _, hostID := range duplicates {
			clearFunc := doNotClear

			clusterId, isHostBoundToCluster := serviceServer.getHostCluster(hostID)
			if isHostBoundToCluster {
				clearFunc = func() { checkHost(hostID, clusterId) }
			}

			hostStatusStorage.set(ALL, hostID, originalStatus.Status, clearFunc)
		}
	}

	return nil
}
