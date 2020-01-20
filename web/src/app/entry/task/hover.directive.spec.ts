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
import { Component, DebugElement } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { SharedModule } from '@app/shared';

import { HoverDirective } from './hover.directive';

@Component({
  template: `
    <button appHoverStatusTask mat-raised-button matTooltip="Stop task">
      <mat-icon class="icon-locked running" #taskIcon>autorenew</mat-icon>
    </button>
  `
})
export class TestComponent {}

describe('HoverDirective', () => {
  let fixture: ComponentFixture<TestComponent>;
  let debs: DebugElement[];
  let den: DebugElement;

  beforeEach(() => {
    fixture = TestBed.configureTestingModule({
      imports: [SharedModule],
      declarations: [TestComponent, HoverDirective]
    }).createComponent(TestComponent);

    fixture.detectChanges();

    debs = fixture.debugElement.queryAll(By.directive(HoverDirective));
  });

  it('can inject `HoverDirective` in 1st <button>', () => {
    const dir = debs[0].injector.get(HoverDirective);
    expect(dir).toBeTruthy();
  });

  it('should have `HoverDirective` in 1st <button> providerTokens', () => {
    expect(debs[0].providerTokens).toContain(HoverDirective);
  });

  // mousehover
  it('should change icon by mouseover', () => {
    const a = debs[0];
    a.triggerEventHandler('mouseover', {});
    fixture.detectChanges();
    expect(a.nativeElement.querySelector('mat-icon').innerText).toEqual('block');
  });

  // mouseleave
  it('should change icon by mouseout', () => {
    const a = debs[0];
    a.triggerEventHandler('mouseout', {});
    fixture.detectChanges();
    expect(a.nativeElement.querySelector('mat-icon').innerText).toEqual('autorenew');
  });
});
