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

import { ActionsComponent } from './actions.component';
import { MaterialModule } from '@app/shared/material.module';

describe('ActionsComponent', () => {
  let component: ActionsComponent;
  let fixture: ComponentFixture<ActionsComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      imports: [MaterialModule],
      declarations: [ActionsComponent]
    }).compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ActionsComponent);
    component = fixture.componentInstance;
    component.source = [];
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('Func `calcWidth` when the width of the window is greater than the buttons width sum', () => {
    const arr = [40, 30, 60];
    const result = component.calcWidth(1200, arr);
    expect(result).toEqual(['130px', arr.length - 1]);
  });

  it('Func `calcWidth` when the width of the window is less than the buttons width sum', () => {
    const result = component.calcWidth(500, [140, 130, 160, 120, 80, 120]);
    expect(result).toEqual(['430px', 2]);
  });
});
