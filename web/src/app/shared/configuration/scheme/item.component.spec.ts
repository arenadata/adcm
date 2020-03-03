import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ItemComponent } from './item.component';

describe('ItemComponent', () => {
  let component: ItemComponent;
  let fixture: ComponentFixture<ItemComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ItemComponent]
    }).compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ItemComponent);
    component = fixture.componentInstance;
    component.item = { name: 'test', rules: { name: '', type: 'string', validator: {}, controlType: 'textbox', path: [] }, parent: 'dict', value: {} };
    fixture.detectChanges();
  });

  it('should create', () => {    
    expect(component).toBeTruthy();
  });
});
