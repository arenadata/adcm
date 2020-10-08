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
import { MaterialModule } from '@app/shared/material.module';

import { ActionsComponent } from './actions.component';

describe('ActionsComponent', () => {
  let component: ActionsComponent;
  let fixture: ComponentFixture<ActionsComponent>;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [MaterialModule],
      declarations: [ActionsComponent]
    }).compileComponents();
  });

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
    expect(result).toEqual([arr.length, 130, false]);
  });

  it('Func `calcWidth` when the width of the window is less than the buttons width sum', () => {
    const result = component.calcWidth(1189, [132, 157, 292, 101, 169, 123, 133, 124, 76, 146, 74]);
    expect(result).toEqual([7, 1107, true]);

    const result2 = component.calcWidth(1240, [132, 157, 292, 101, 169, 123, 133, 124, 76, 146, 74]);
    expect(result2).toEqual([8, 1231, true]);

    const result3 = component.calcWidth(1305, [132, 157, 292, 101, 169, 123, 133, 124, 76, 146, 74]);
    expect(result3).toEqual([8, 1231, true]);

    const result4 = component.calcWidth(1310, [132, 157, 292, 101, 169, 123, 133, 124, 76, 146, 74]);
    expect(result4).toEqual([9, 1307, true]);

    //  1307 + 76
    const result5 = component.calcWidth(1390, [132, 157, 292, 101, 169, 123, 133, 124, 76, 146, 74]);
    expect(result5).toEqual([9, 1307, true]);
  });
});
