import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ComponentFactory,
  ComponentFactoryResolver,
  ComponentRef,
  ContentChild,
  Input,
  TemplateRef,
  ViewChild,
  ViewContainerRef
} from '@angular/core';
import { ConfigFieldMarker } from '@app/shared/configuration/attributes/config-field.directive';
import { AttributeService, AttributeWrapper } from '@app/shared/configuration/attributes/attribute.service';
import { FormGroup } from '@angular/forms';
import { IFieldOptions } from '@app/shared/configuration/types';

@Component({
  selector: 'app-config-field-attribute-provider',
  template: `
    <ng-container *ngIf="!attributesSrv?.attributes">
      <ng-container *ngTemplateOutlet="template"></ng-container>
    </ng-container>

    <ng-container #container></ng-container>
  `,
  styles: [
    ':host {display: flex; width: 100%; margin-bottom: 20px}',
    ':host:last-child {margin-bottom: 0}',
    `:host:nth-child(odd) {
      background-color: #4e4e4e;
    }`
  ],
})
export class ConfigFieldAttributeProviderComponent implements AfterViewInit {

  template: TemplateRef<any>;

  containerRef: ComponentRef<AttributeWrapper>;

  @Input('form')
  parametersForm: FormGroup;

  @Input()
  options: IFieldOptions;

  @ViewChild('container', { read: ViewContainerRef })
  container: ViewContainerRef;

  @ContentChild(ConfigFieldMarker)
  field: ConfigFieldMarker;

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
        }
      });

    } else {
      this.template = this.field.template;
    }
  }
}
