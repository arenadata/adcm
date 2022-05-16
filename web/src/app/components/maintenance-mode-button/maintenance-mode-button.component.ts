import { Component, EventEmitter, Input, Output } from '@angular/core';
import { AdwpCellComponent } from "@adwp-ui/widgets";

export enum StatusType {
  On = 'on',
  Off = 'off',
  Disabled = 'disabled'
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
  status: Status;
  maintenanceMode: string;

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
    [StatusType.Disabled]: {
      isButtonActive: false,
      isModeActive: false,
      color: 'primary',
      tooltip: 'Maintenance mode is not available'
    }
  }

  @Input() row: T;
  @Output() onClick = new EventEmitter();

  ngOnInit(): void {
    this.maintenanceMode = this.row['maintenance_mode'];
    this.status = this.statuses[this.maintenanceMode];
  }

  clickCell(event: MouseEvent, row: T): void {
    if (this.maintenanceMode !== StatusType.Disabled && this.maintenanceMode === StatusType.On) {
      this.maintenanceMode = StatusType.Off;
      this.status = this.statuses[StatusType.Off];
    } else if (this.maintenanceMode !== StatusType.Disabled && this.maintenanceMode === StatusType.Off) {
      this.maintenanceMode = StatusType.On;
      this.status = this.statuses[StatusType.On];
    }

    this.onClick.emit({ event, value: { id: this.row['id'], maintenance_mode: this.maintenanceMode } });
  }

  preventIfDisabled(event) {
    if (!this.status?.isModeActive) {
      event.stopPropagation();
      event.preventDefault();
    }
  }
}
