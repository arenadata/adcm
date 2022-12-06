import { Component, EventEmitter, Input, Output } from '@angular/core';
import { AdwpCellComponent } from "@adwp-ui/widgets";

export enum StatusType {
  On = 'ON',
  Off = 'OFF',
  Changing = 'CHANGING'
}

export interface Status {
  isButtonActive: boolean;
  isModeActive: boolean;
  color: string;
  tooltip: string;
}

@Component({
  selector: 'app-maintenance-mode-button',
  templateUrl: './maintenance-mode-button.component.html',
  styleUrls: ['./maintenance-mode-button.component.scss']
})
export class MaintenanceModeButtonComponent<T> implements AdwpCellComponent<T> {
  mminaTooltip = 'Maintenance mode is not available';
  statuses: { [key in StatusType]: Status; } = {
    [StatusType.On]: {
      isButtonActive: true,
      isModeActive: true,
      color: 'on',
      tooltip: 'Turn maintenance mode OFF'
    },
    [StatusType.Off]: {
      isButtonActive: false,
      isModeActive: true,
      color: 'primary',
      tooltip:'Turn maintenance mode ON'
    },
    [StatusType.Changing]: {
      isButtonActive: false,
      isModeActive: false,
      color: 'primary',
      tooltip: 'Maintenance mode is not available'
    }
  }

  get maintenanceModeStatus(): string {
   return this?.row?.maintenance_mode;
  }

  get status(): Status {
    return this.statuses[this.maintenanceModeStatus];
  }

  get isMaintenanceModeAvailable(): boolean {
    return this?.row?.is_maintenance_mode_available;
  }

  @Input() row: any;
  @Input() type: string;
  @Output() onClick = new EventEmitter();

  ngOnInit(): void {}

  clickCell(event: MouseEvent, row: T): void {
    if (this.maintenanceModeStatus !== StatusType.Changing && this.maintenanceModeStatus === StatusType.On) {
      this.row.maintenance_mode = StatusType.Off;
    } else if (this.maintenanceModeStatus !== StatusType.Changing && this.maintenanceModeStatus === StatusType.Off) {
      this.row.maintenance_mode = StatusType.On;
    }

    this.onClick.emit({ event, value: { id: this.row['id'], maintenance_mode: this.row.maintenance_mode, type: this.type } });
  }

  preventIfDisabled(event) {
    if (this.isMaintenanceModeAvailable && this.status?.isModeActive) return;

    event.stopPropagation();
    event.preventDefault();
  }
}
