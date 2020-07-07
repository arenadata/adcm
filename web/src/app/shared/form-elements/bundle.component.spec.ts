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
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormGroup } from '@angular/forms';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { PreloaderService } from '@app/core';
import { of } from 'rxjs';

import { AddService } from '../add-component/add.service';
import { BundlesComponent } from './bundles.component';

describe('Form control :: bundle component', () => {
  let component: BundlesComponent;
  let fixture: ComponentFixture<BundlesComponent>;
  let aService = jasmine.createSpyObj('AddService', ['getPrototype']);
  //   {
  //     getPrototype: (n: string, param: { offset: number }) =>
  //       of(
  //         Array(param.offset)
  //           .fill(0)
  //           .map((_, i) => ({ bundle_id: i, display_name: `bundle_${i}`, version: `0.0${i}`, bundle_edition: 'community' }))
  //       ),
  //   };

  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [MatSelectModule, NoopAnimationsModule, MatTooltipModule],
      providers: [{ provide: AddService, useValue: aService }],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(BundlesComponent);
    component = fixture.componentInstance;
    component.form = new FormGroup({});
    component.limit = 10;
    fixture.detectChanges();
  });

  it('Bundle component should created', () => {
    expect(component).toBeTruthy();
  });

  it('List bundle with one element', async () => {
    // component.bundles = [
    //   { id: 0, display_name: 'bundle_1', version: '0.01', bundle_edition: 'community', name: '', url: '', description: '', edition: '', bundle_id: 0, license: 'absent' },
    // ];
    // component.selectOne(component.bundles, 'display_name');
    const bundles = aService.getPrototype.and.returnValue(of([
      { id: 0, display_name: 'bundle_1', version: '0.01', bundle_edition: 'community', name: '', url: '', description: '', edition: '', bundle_id: 0, license: 'absent' },
    ]));
    
    fixture.detectChanges();
    await fixture.whenStable().then((_) => {
      fixture.detectChanges();
      const displayNameSelect = fixture.debugElement.nativeElement.querySelector('mat-select[formcontrolname=display_name]');
      const firstDisplyaName = component.bundles[0].display_name;
      expect(displayNameSelect.querySelector('div>div>span>span').innerText).toBe(firstDisplyaName);
    });
  });

  xit('check paging', async () => {
    await fixture.whenStable().then((_) => {
      component.getNextPage();
      fixture.detectChanges();
      expect(component.bundles.length).toBe(component.page * component.limit);
    });
  });
});
