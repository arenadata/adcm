import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LogMenuItemComponent } from './log-menu-item.component';
import { AuthService } from "@app/core/auth/auth.service";
import { ApiService } from "@app/core/api";
import { HttpClient, HttpHandler } from "@angular/common/http";
import { Store, StoreModule } from "@ngrx/store";

describe('LogMenuItemComponent', () => {
  let component: LogMenuItemComponent;
  let fixture: ComponentFixture<LogMenuItemComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ LogMenuItemComponent ],
      imports: [ StoreModule.forRoot({}) ],
      providers: [ AuthService, ApiService, HttpClient, HttpHandler, Store ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(LogMenuItemComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
