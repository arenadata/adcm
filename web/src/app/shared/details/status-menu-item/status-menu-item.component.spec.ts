import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StatusMenuItemComponent } from './status-menu-item.component';

describe('StatusMenuItemComponent', () => {
  let component: StatusMenuItemComponent;
  let fixture: ComponentFixture<StatusMenuItemComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ StatusMenuItemComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(StatusMenuItemComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
