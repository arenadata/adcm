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
import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';

import { HolderDirective } from './holder.directive';

@Component({
  template: `<div class="main" [appHolder]="scrollEventData">
    <div><div class="wrapper" style="height: 100px;"></div></div>
    <div><div class="wrapper" style="height: 10px;"></div></div>
  </div>`,
})
class TestComponent {
  scrollEventData: { direct: 1 | -1 | 0; scrollTop: number };
}

describe('HolderDirective', () => {
  let component: TestComponent;
  let fixture: ComponentFixture<TestComponent>;
  let dir: HolderDirective;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [TestComponent, HolderDirective],
    });

    fixture = TestBed.createComponent(TestComponent);
    dir = fixture.debugElement.queryAll(By.directive(HolderDirective))[0].injector.get(HolderDirective);
    fixture.detectChanges();
    component = fixture.componentInstance;
  });

  it('should create component', () => {
    expect(component).toBeDefined();
  });

  it('can inject `HolderDirective`', () => {
    expect(dir).toBeTruthy();
  });

  it('Host component should contains two el > .wrapper', () => {
    const host = fixture.nativeElement.querySelector('.main');
    const children = host.children;
    expect(children.length).toBe(2);
    expect(children[0].querySelector('.wrapper')).toBeDefined();
    expect(children[1].querySelector('.wrapper')).toBeDefined();
  });

  it('Host component should change margin-top after scroll', () => {
    component.scrollEventData = { direct: 0, scrollTop: 10 };
    fixture.detectChanges();
    expect(dir.ps).toBeDefined();
    component.scrollEventData = { direct: 0, scrollTop: 11 };
    fixture.detectChanges();
    const debugs = fixture.debugElement.nativeElement.getElementsByClassName('wrapper');
    expect(dir.ps.short.style.cssText).toContain('margin-top: 11px');
    expect(debugs[1].style.cssText).toContain('margin-top: 11px');
  });
});
