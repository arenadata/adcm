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
import { ComponentFixture, fakeAsync, TestBed, tick } from '@angular/core/testing';
import { FormGroup, FormControl } from '@angular/forms';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Bundle } from '@app/core/types';
import { of } from 'rxjs';

import { AddService } from '../add-component/add.service';
import { BundlesComponent } from './bundles.component';

let COUNT_DATA = 1;
const uploadBundle: Partial<Bundle> = { id: 9, display_name: 'bundle_9', version: '0.09', bundle_edition: 'community' };
const getProto = () =>
  Array(COUNT_DATA)
    .fill(0)
    .map((_, i) => ({ bundle_id: i, display_name: `bundle_${i}`, version: `0.0${i}`, bundle_edition: 'community' }));

describe('Form control :: bundle component', () => {
  let component: BundlesComponent;
  let fixture: ComponentFixture<BundlesComponent>;
  let aService = {
    getPrototype: () => of(getProto()),
    upload: () => of([uploadBundle]),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MatSelectModule, NoopAnimationsModule, MatTooltipModule],
      providers: [{ provide: AddService, useValue: aService }],
    }).compileComponents();
  });

  beforeEach(async () => {
    fixture = await TestBed.createComponent(BundlesComponent);
    component = fixture.componentInstance;
    component.form = new FormGroup({ prototype_id: new FormControl() });
    component.limit = 10;
  });

  it('Bundle component should created', () => {
    expect(component).toBeTruthy();
  });

  it('list bundle with one element should contains first display_name', async () => {
    COUNT_DATA = 1;
    fixture.detectChanges();
    await fixture.whenStable().then((_) => {
      fixture.detectChanges();
      const displayNameSelect = fixture.debugElement.nativeElement.querySelector('mat-select[formcontrolname=display_name]');
      const firstDisplyaName = component.bundles[0].display_name;
      expect(displayNameSelect.querySelector('div>div>span>span').innerText).toBe(firstDisplyaName);
    });
  });

  it('check paging', fakeAsync(() => {
    COUNT_DATA = 10;
    fixture.detectChanges();
    fixture.whenStable().then((_) => {
      fixture.detectChanges();
      expect(component.bundles.length).toBe(component.page * component.limit);
      expect(component.bundles.length).toBe(10);

      COUNT_DATA = 20;
      component.getNextPage();
      fixture.detectChanges();
      expect(component.bundles.length).toBe(component.page * component.limit);
      expect(component.bundles.length).toBe(20);

      const displayNameSelect = fixture.debugElement.nativeElement.querySelector('mat-select[formcontrolname=display_name]');
      const select_id = displayNameSelect.getAttribute('id');

      displayNameSelect.click();
      tick();
      fixture.detectChanges();

      const options = document.querySelector(`div#${select_id}-panel`).getElementsByTagName('mat-option');
      expect(options.length).toBe(21);
    });
  }));

  it('when loading a new package, display_name should be displayed in the drop-down list', async () => {
    COUNT_DATA = 10;
    fixture.detectChanges();
    // upload bundle #9 for example
    component.upload([]);
    fixture.detectChanges();

    await fixture.whenStable().then((_) => {
      fixture.detectChanges();
      const displayNameSelect = fixture.debugElement.nativeElement.querySelector('mat-select[formcontrolname=display_name]');
      expect(displayNameSelect.querySelector('div>div>span>span').innerText).toBe(uploadBundle.display_name);

      const versionSelect = fixture.debugElement.nativeElement.querySelector('mat-select[formcontrolname=bundle_id]');
      expect(versionSelect.querySelector('div>div>span>span').innerText).toBe(`${uploadBundle.version} ${uploadBundle.bundle_edition}`);
    });
  });
});
