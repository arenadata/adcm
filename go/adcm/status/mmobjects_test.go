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
	"testing"
)

// TestMMObjectsConcurrent guards MMObjects against unsynchronized access from
// concurrent HTTP handlers: postMMObjects replaces the whole data while status
// calculations call IsHostInMM/IsServiceInMM/IsComponentInMM and getMMObjects
// reads the data back. If the readers do not take the mutex, this test fails
// with -race (DATA RACE) and may even crash without it.
func TestMMObjectsConcurrent(t *testing.T) {
	InitLog("", "CRITICAL")

	mm := newMMObjects()

	const workers = 100
	const iterations = 100
	start := make(chan struct{})
	var wg sync.WaitGroup

	for i := 0; i < workers; i++ {
		wg.Go(func() {
			<-start
			for j := 0; j < iterations; j++ {
				mm.setData(MMObjectsData{Hosts: []int{i}, Services: []int{i}, Components: []int{i}})
				mm.IsHostInMM(i)
				mm.IsServiceInMM(i)
				mm.IsComponentInMM(i)
				data := mm.getData()
				if len(data.Hosts) != 1 || len(data.Services) != 1 || len(data.Components) != 1 {
					t.Errorf("torn read of maintenance mode objects: %+v", data)
					return
				}
			}
		})
	}

	close(start)
	wg.Wait()
}
