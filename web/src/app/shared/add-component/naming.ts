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
import { randomInteger } from '@app/core/types/func';

const rivers: string[] = [
  'Amur',
  'Anadyr',
  'Angara',
  'Colorado',
  'Congo',
  'Desna',
  'Dnieper',
  'Don',
  'Irtysh',
  'Kama',
  'Limpopo',
  'Mekong',
  'Mississippi',
  'Nile',
  'Ob',
  'Oka',
  'Pechora',
  'Rhine',
  'Ural',
  'Volga',
  'Yangtze',
  'Yenisei',
  'Yukon',
  'Zambezi',
];

const adjectives: string[] = [
  'Ancient',
  'Beautiful',
  'Big',
  'Blue',
  'Broad',
  'Clear',
  'Cold',
  'Dark',
  'Deep',
  'Distant',
  'Down',
  'Dry',
  'Famous',
  'Fear',
  'Flowing',
  'Frozen',
  'Great',
  'Holy',
  'Huge',
  'Icy',
  'Large',
  'Latter',
  'Longest',
  'Lovely',
  'Lower',
  'Mad',
  'Magnificent',
  'Majestic',
  'Middle',
  'Mighty',
  'Muddy',
  'Narrow',
  'Noble',
  'North',
  'Placid',
  'Polluted',
  'Quiet',
  'Rapid',
  'Sacred',
  'Shallow',
  'Slow',
  'Sluggish',
  'Small',
  'Swift',
  'Tidal',
  'Tributary',
  'Turbulent',
  'Wide',
  'Wild',
];

export class GenName {
  public static do(prefix: string = '') {
    return `${adjectives[randomInteger(adjectives.length - 1)]} ${rivers[randomInteger(rivers.length - 1)]}${prefix}`;
  }
}
