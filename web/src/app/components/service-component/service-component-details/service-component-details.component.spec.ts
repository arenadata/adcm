import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ServiceComponentDetailsComponent } from './service-component-details.component';

describe('ServiceComponentDetailsComponent', () => {
  let component: ServiceComponentDetailsComponent;
  let fixture: ComponentFixture<ServiceComponentDetailsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ServiceComponentDetailsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ServiceComponentDetailsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
