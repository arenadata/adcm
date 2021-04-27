import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActionsButtonComponent } from './actions-button.component';

describe('ActionsButtonComponent', () => {
  let component: ActionsButtonComponent<any>;
  let fixture: ComponentFixture<ActionsButtonComponent<any>>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ActionsButtonComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ActionsButtonComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
