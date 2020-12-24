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
import { animate, state, style, transition, trigger } from '@angular/animations';

export const openClose = trigger('openClose', [
  state('true', style({ height: '*', opacity: 1 })),
  state('false', style({ height: '0px', opacity: 0 })),
  transition('true <=> false', [animate('0.5s')]),
]);

export const notify = trigger('notify', [
  state('show', style({ opacity: 1 })),
  state('hide', style({ opacity: 0 })),
  transition('hide => show', [animate('.2s')]),
  transition('show => hide', [animate('2s')]),
]);
