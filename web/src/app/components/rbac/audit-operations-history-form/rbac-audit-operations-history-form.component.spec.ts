import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RbacAuditOperationsHistoryFormComponent } from './rbac-audit-operations-history-form.component';

describe('AuditOperationsFormComponent', () => {
  let component: RbacAuditOperationsHistoryFormComponent;
  let fixture: ComponentFixture<RbacAuditOperationsHistoryFormComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ RbacAuditOperationsHistoryFormComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(RbacAuditOperationsHistoryFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
