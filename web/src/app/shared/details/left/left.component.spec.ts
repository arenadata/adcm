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
import { RouterTestingModule } from '@angular/router/testing';
import { MaterialModule } from '@app/shared/material.module';
import { StuffModule } from '@app/shared/stuff.module';
 
import { NavigationService } from '../navigation.service';
import { LeftComponent } from './left.component';

/**
 * проверка показа правильных иконок у элементов меню
 * проверка кнопки с action 
 */

describe('LeftComponent', () => {
  let component: LeftComponent;
  let fixture: ComponentFixture<LeftComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      imports: [MaterialModule, StuffModule, RouterTestingModule],
      declarations: [LeftComponent],
      providers: [NavigationService]
    }).compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(LeftComponent);
    component = fixture.componentInstance;

    component.current = { typeName: 'cluster' };

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize menu', () => {
    const el: HTMLElement = fixture.debugElement.nativeElement;
    const list = el.querySelectorAll('a');
    expect(list.length).toBeGreaterThan(0);
  });
});
