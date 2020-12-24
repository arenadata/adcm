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
import { FormBuilder, FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MaterialModule } from '@app/shared/material.module';

import { FieldService } from '../field.service';
import { IFieldOptions, TNForm } from '../types';
import { YspecService } from '../yspec/yspec.service';
import { RootComponent } from './root.component';
import { SchemeComponent } from './scheme.component';
import { SchemeService } from './scheme.service';

describe('SchemeComponent', () => {
  let component: SchemeComponent;
  let fixture: ComponentFixture<SchemeComponent>;
  let service: SchemeService;
  let fieldService: FieldService;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [MaterialModule, FormsModule, ReactiveFormsModule],
      declarations: [SchemeComponent, RootComponent],
      providers: [YspecService, FieldService, FormBuilder, SchemeService],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(SchemeComponent);
    service = TestBed.inject(SchemeService);
    component = fixture.componentInstance;
    component.form = new FormGroup({ field: new FormControl() });
    const yspec = { root: { match: 'list' as TNForm, item: 'string' }, string: { match: 'string' as TNForm } };
    component.field = (<unknown>{ display_name: 'field_display_name', name: 'field', limits: { yspec }, required: true, value: null, default: null }) as IFieldOptions;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should has formGroup and fieldOptions.limits.yspec', () => {
    expect(component.field?.limits?.yspec).toBeTruthy();
    expect(component.form).toBeTruthy();
  });

  it('after init should be current form for children component', () => {
    expect(component.current).toBeTruthy();
  });

  it('if field is required and value of default is null should shown error notification', () => {
    const error = fixture.nativeElement.querySelector('mat-error');
    expect(error).toBeTruthy();
    expect(error.innerText).toBe('Field [field_display_name] is required!');
  });


});
