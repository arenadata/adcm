import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActionsColumnComponent } from './actions-column.component';

describe('ActionsColumnComponent', () => {
  let component: ActionsColumnComponent<any>;
  let fixture: ComponentFixture<ActionsColumnComponent<any>>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ActionsColumnComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ActionsColumnComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
