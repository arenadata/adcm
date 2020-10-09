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
import { FormControl, FormGroup } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { IFieldOptions } from '../configuration/types';
import { SharedModule } from '../shared.module';
import { VariantComponent } from './variant.component';

describe('VariantComponent', () => {
  let component: VariantComponent;
  let fixture: ComponentFixture<VariantComponent>;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [SharedModule, NoopAnimationsModule],
      declarations: [VariantComponent],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(VariantComponent);
    component = fixture.componentInstance;
    component.form = new FormGroup({ name: new FormControl() });
    component.field = { name: 'name', limits: {} } as IFieldOptions;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
