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

func TestHostDuplicates(t *testing.T) {
	// Data

	// original ids
	o1 := 100
	o2 := 50
	notExist := 1000

	// duplicate ids
	d1 := 200
	d2 := 300
	d3 := 400

	// Test

	hd := newHostDuplicates()

	actual := hd.GetForID(o1)
	if len(actual) != 0 {
		t.Error("initialized host duplicates storage expected empty for any ID")
	}

	hd.Register(o1, []int{d1, d2})

	actual = hd.GetForID(o1)
	if len(actual) != 2 {
		t.Errorf("expected %d items, got %d: %d", 2, len(actual), actual)
	}

	hd.Register(o2, []int{d3})

	actual = hd.GetForID(o2)
	if len(actual) != 1 {
		t.Errorf("expected %d items, got %d: %d", 1, len(actual), actual)
	}

	hd.Register(o1, []int{d1, d3})

	actual = hd.GetForID(o1)
	if len(actual) != 3 {
		t.Errorf("expected %d items, got %d: %d", 3, len(actual), actual)
	}

	actual = hd.GetForID(o2)
	if len(actual) != 1 {
		t.Errorf("expected %d items, got %d: %d", 1, len(actual), actual)
	}

	actual = hd.GetForID(notExist)
	if len(actual) != 0 {
		t.Errorf("expected empty for not existing id, got: %d", actual)
	}
}

// TestHostDuplicatesConcurrent guards against unsynchronized access to the duplicates map.
// Register and GetForID are called from concurrent HTTP handlers
// (POST /host-duplicates/ and POST /host/:hostid/ respectively),
// so GetForID must take the same mutex as Register.
// Without that the test crashes with "concurrent map read and map write"
// or, with -race, reports a DATA RACE on every run.
func TestHostDuplicatesConcurrent(t *testing.T) {
	hd := newHostDuplicates()

	const (
		workers    = 100
		iterations = 100
		// Every worker also hammers this key, so readers and writers
		// constantly collide on the same inner map, not only on the outer one.
		sharedID = 100000
	)
	start := make(chan struct{})
	var wg sync.WaitGroup

	for i := 0; i < workers; i++ {
		wg.Go(func() {
			<-start
			for j := 0; j < iterations; j++ {
				hd.Register(i, []int{i + 1, i + 2})
				hd.GetForID(i)
				hd.Register(sharedID, []int{i})
				hd.GetForID(sharedID)
			}
		})
	}

	close(start)
	wg.Wait()

	for i := 0; i < workers; i++ {
		if got := hd.GetForID(i); len(got) != 2 {
			t.Errorf("expected 2 duplicates for id %d, got %d: %d", i, len(got), got)
		}
	}
	if got := hd.GetForID(sharedID); len(got) != workers {
		t.Errorf("expected %d duplicates for shared id, got %d", workers, len(got))
	}
}
