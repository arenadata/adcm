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
import { Subject } from 'rxjs';
import { filter } from 'rxjs/operators';

export interface IBroadcast {
  key: string;
  value: any;
}

@Injectable({
  providedIn: 'root',
})
export class ChannelService {
  private event = new Subject<IBroadcast>();

  next(key: string, value: any) {
    this.event.next({ key, value });
  }

  on(key: string) {
    return this.event.asObservable().pipe(filter(e => e.key === key));
  }
}
