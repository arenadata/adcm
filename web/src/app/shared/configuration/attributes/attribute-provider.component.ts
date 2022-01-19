import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ComponentFactory,
  ComponentFactoryResolver,
  ComponentRef,
  ContentChild,
  ContentChildren,
  HostBinding,
  Input,
  QueryList,
  TemplateRef,
  ViewChild,
  ViewContainerRef
} from '@angular/core';
import { ConfigFieldMarker } from '@app/shared/configuration/attributes/config-field.directive';
import { AttributeService, AttributeWrapper } from '@app/shared/configuration/attributes/attribute.service';
import { FormGroup } from '@angular/forms';
import { IFieldOptions } from '@app/shared/configuration/types';
import { CONFIG_FIELD, FieldComponent } from '@app/shared/configuration/field/field.component';

@Component({
  selector: 'app-config-field-attribute-provider',
  template: `
    <ng-container *ngIf="!attributesSrv?.attributes">
      <ng-container *ngTemplateOutlet="template"></ng-container>
    </ng-container>

    <ng-container #container></ng-container>
  `,
  styleUrls: ['./attribute-provider.component.scss'],
})
export class ConfigFieldAttributeProviderComponent implements AfterViewInit {

  template: TemplateRef<any>;

  containerRef: ComponentRef<AttributeWrapper>;

  @Input('form')
  parametersForm: FormGroup;

  @Input()
  options: IFieldOptions;

  @HostBinding('class.read-only') get readOnly() {
    return this.options.read_only;
  }

  @ViewChild('container', { read: ViewContainerRef })
  container: ViewContainerRef;

  @ContentChild(ConfigFieldMarker)
  field: ConfigFieldMarker;

  @ContentChildren(CONFIG_FIELD, { descendants: true })
  fieldComponent: QueryList<FieldComponent>;

  constructor(private componentFactoryResolver: ComponentFactoryResolver,
              public attributesSrv: AttributeService,
              private _cdr: ChangeDetectorRef) {}

  ngAfterViewInit(): void {
    this.container.clear();
    if (this.attributesSrv.attributes) {
      this.attributesSrv.attributes.forEach((attribute) => {
        if (attribute.wrapper) {
          const factory: ComponentFactory<AttributeWrapper> = this.componentFactoryResolver.resolveComponentFactory(attribute.wrapper);
          this.containerRef = this.container.createComponent(factory);
          this.containerRef.instance.fieldTemplate = this.field.template;
          this.containerRef.instance.wrapperOptions = attribute.options;
          this.containerRef.instance.fieldOptions = this.options;
          this.containerRef.instance.attributeForm = attribute.form;
          this.containerRef.instance.parametersForm = this.parametersForm;
          Promise.resolve().then(() => this.containerRef.instance.field = this.fieldComponent.first);
        }
      });
    } else {
      this.template = this.field.template;
    }
  }
}
