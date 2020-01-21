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

describe('HoverStatusTaskDirective', () => {
  let fixture: ComponentFixture<TestComponent>;
  let debs: DebugElement[];
  let a: DebugElement;

  beforeEach(() => {
    fixture = TestBed.configureTestingModule({
      imports: [SharedModule],
      declarations: [TestComponent, HoverDirective]
    }).createComponent(TestComponent);

    fixture.detectChanges();

    debs = fixture.debugElement.queryAll(By.directive(HoverDirective));
    a = debs[0];

  });

  // afterEach(() => {
  //   fixture.destroy();
  // });

  it('can inject `HoverStatusTaskDirective` in 1st <button>', () => {
    expect(a.injector.get(HoverDirective)).toBeTruthy();
  });

  it('should have `HoverStatusTaskDirective` in 1st <button> providerTokens', () => {
    expect(a.providerTokens).toContain(HoverDirective);
  });

  // mousehover
  it('should change icon `block` by mouseover', () => {    
    a.triggerEventHandler('mouseover', {});
    fixture.detectChanges();
    expect(a.nativeElement.querySelector('mat-icon').innerText).toEqual('block');
  });

  it('should remove class `icon-locked` on icon by mouseover', () => {
    a.triggerEventHandler('mouseover', {});
    fixture.detectChanges();
    const b: HTMLElement = a.nativeElement.querySelector('mat-icon');
    expect(b.classList.contains('icon-locked')).toBeFalse();
  });

  // mouseleave
  it('should return icon `autorenew` by mouseout', () => {
    a.triggerEventHandler('mouseout', {});
    fixture.detectChanges();
    expect(a.nativeElement.querySelector('mat-icon').innerText).toEqual('autorenew');
  });

  it('should return class `icon-locked` on icon by mouseout', () => {
    a.triggerEventHandler('mouseout', {});
    fixture.detectChanges();
    const b: HTMLElement = a.nativeElement.querySelector('mat-icon');
    expect(b.classList.contains('icon-locked')).toBeTrue();
  });

});
