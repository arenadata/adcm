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


/**
 * Generator data for tests
 *
 * @export
 * @class Generator
 */
export class Generator {
  getExample(i: number, data = { id: 'bundle_id', bundle_edition: 'comutity' || 'enterprise', other: ['display_name', 'version'] }) {
    return [].reduce((p, c) => (p[c] = `${c}_${i}`), {});
    // { bundle_id: i, display_name: `bundle_${i}`, version: `0.0${i}`, bundle_edition: 'community' };
  }

  getArray<T>(count: number) {
    return Array(count)
      .fill(0)
      .map((_, i) => this.getExample(i));
  }
}


