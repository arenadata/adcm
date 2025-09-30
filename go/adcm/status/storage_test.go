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

import "testing"

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
