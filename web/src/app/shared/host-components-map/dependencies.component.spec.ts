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

import { DependenciesComponent } from './dependencies.component';

describe('DependenciesComponent', () => {
  let component: DependenciesComponent;
  let fixture: ComponentFixture<DependenciesComponent>;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      declarations: [DependenciesComponent],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(DependenciesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('data when creating a dialog', () => {
    component.model = [{ prototype_id: 1, display_name: 'display_name_test_1', name: 'test_name_1' }];
    component.ngOnInit();
    fixture.detectChanges();
    const li = fixture.nativeElement.querySelector('ul').getElementsByTagName('li');
    expect(li.length).toBe(1);
    expect(li[0].innerText).toBe('display_name_test_1');
  });

  it('data when input property [components]', () => {
    component.components = [{ prototype_id: 1, display_name: 'display_name_test_1', name: 'test_name_1' }];
    component.ngOnInit();
    fixture.detectChanges();
    const li = fixture.nativeElement.querySelector('ul').getElementsByTagName('li');
    expect(li.length).toBe(1);
    expect(li[0].innerText).toBe('display_name_test_1');
  });

  it('data as tree', () => {
    component.model = [{ prototype_id: 1, display_name: 'display_name_test_1', name: 'test_name_1', components: [{ prototype_id: 2, display_name: 'display_name_test_2', name: 'test_name_2' }] }];
    component.ngOnInit();
    fixture.detectChanges();
    const ul = fixture.nativeElement.querySelector('ul');
    const li = ul.getElementsByTagName('li');
    expect(ul.getElementsByTagName('app-dependencies').length).toBe(2);
    expect(li.length).toBe(2);
    expect(li[1].innerText).toBe('display_name_test_2');
    expect(ul.innerText).toContain('display_name_test_1');
    expect(ul.innerText).toContain('display_name_test_2');
  });
});
