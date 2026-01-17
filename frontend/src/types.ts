/**
 * Type definitions for Abode Security frontend.
 */

export interface AbodePanel {
  mode: {
    area_1: 'standby' | 'home' | 'away';
    area_1_label: string;
  };
  online: string;
  battery: string;
}

export interface AbodeDevice {
  id: string;
  name: string;
  type: string;
  type_tag: string;
  status: string;
}

// Add more types as needed when expanding functionality
