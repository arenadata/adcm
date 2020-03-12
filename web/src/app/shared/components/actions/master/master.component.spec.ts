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
import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ActionMasterComponent as MasterComponent } from './master.component';
import { ApiService } from '@app/core/api';
import { FieldService } from '@app/shared/configuration/field.service';
import { MatListModule } from '@angular/material/list';

describe('MasterComponent', () => {
  let component: MasterComponent;
  let fixture: ComponentFixture<MasterComponent>;
  let ApiServiceStub: Partial<ApiService>;
  let FieldServiceStub: Partial<FieldService>;

  beforeEach(async(() => {

    ApiServiceStub = {};
    FieldServiceStub = {};

    TestBed.configureTestingModule({
      imports: [MatListModule],
      declarations: [MasterComponent],
      providers: [
        { provide: ApiService, useValue: ApiServiceStub },
        { provide: FieldService, useValue: FieldServiceStub }
      ]
    }).compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(MasterComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
