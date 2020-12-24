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
import { Injectable } from '@angular/core';
import { ApiService } from '@app/core/api';

// export const fruit = {
//   display_name: 'Fruit',
//   desctiption: 'fruit description',
//   children: [
//     { display_name: 'Apple', description: 'description or some description about this action description or some description about this action' },
//     { display_name: 'Banana', description: 'description or some description about this action bannana' },
//     { display_name: 'Fruit loops', description: '' },
//   ],
// };

// export const vegetable = {
//   display_name: 'Vegetables',
//   desctiption: 'description or some description about this action some description about this action Vegetables',
//   children: [
//     {
//       display_name: 'Green',
//       description: 'description or some description about this action description or some description about this action',
//       children: [
//         { display_name: 'Broccoli', description: 'description or some description about this action description or some description about this action' },
//         { display_name: 'Brussels sprouts', description: 'description or some description about this action bannana' },
//       ],
//     },
//     {
//       display_name: 'Orange',
//       description: 'description or some description about this action bannana',
//       children: [
//         { display_name: 'Pumpkins', description: 'description or some description about this action description or some description about this action' },
//         { display_name: 'Carrots', description: 'description or some description about this action bannana' },
//       ],
//     },
//   ],
// };

@Injectable({
  providedIn: 'root',
})
export class ActionsService {
  constructor(private api: ApiService) {}

  getActions(url: string) {
    return this.api.get<any[]>(url); //.pipe(map((a) => [fruit, vegetable, ...a]));
  }
}
