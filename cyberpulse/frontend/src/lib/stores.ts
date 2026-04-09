import { writable } from 'svelte/store';

export const currentRoute = writable<string>('/');

export const engineStatus = writable<'checking' | 'online' | 'offline'>('checking');

export interface ScanEvent {
  type: string;
  module?: string;
  name?: string;
  index?: number;
  total?: number;
  findings_count?: number;
  duration?: number;
  error?: string;
  message?: string;
  scan_id?: string;
  url?: string;
}

export interface Finding {
  type: string;
  severity: string;
  detail?: string;
  description?: string;
  module_id?: string;
  port?: number;
  service?: string;
}

export const activeScanId = writable<string | null>(null);
export const scanEvents = writable<ScanEvent[]>([]);
export const scanFindings = writable<Finding[]>([]);
