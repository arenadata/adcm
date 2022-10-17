import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RbacAuditOperationsFormComponent } from './rbac-audit-operations-form.component';

describe('AuditOperationsFormComponent', () => {
  let component: RbacAuditOperationsFormComponent;
  let fixture: ComponentFixture<RbacAuditOperationsFormComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ RbacAuditOperationsFormComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(RbacAuditOperationsFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
