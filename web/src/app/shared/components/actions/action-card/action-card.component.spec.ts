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
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogModule } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideMockStore } from '@ngrx/store/testing';

import { ClusterService } from '../../../../core/services/detail.service';
import { Entities } from '../../../../core/types/';
import { ActionsService } from '../actions.service';
import { ActionCardComponent } from './action-card.component';

describe('ActionCardComponent', () => {
  let component: ActionCardComponent;
  let fixture: ComponentFixture<ActionCardComponent>;
  const initialState = { socket: {} };

  beforeEach(async () => {
    TestBed.configureTestingModule({
      imports: [MatDialogModule, NoopAnimationsModule],
      providers: [
        { provide: ActionsService, useValue: { getActions: () => {} } },
        { provide: ClusterService, useValue: { Cluster: {}, Current: {} } },
        provideMockStore({ initialState }),
        // {
        //   provide: MatDialogRef,
        //   useValue: {
        //     close: (dialogResult: any) => {},
        //   },
        // },
      ],
      declarations: [ActionCardComponent],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ActionCardComponent);
    component = fixture.componentInstance;
    component.model = {} as Entities;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
