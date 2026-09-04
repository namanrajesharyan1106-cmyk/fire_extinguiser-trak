/**
 * TypeScript interfaces for the Fire Safety Asset Management System.
 */

export interface User {
  id: number;
  employee_id: string;
  name: string;
  email: string;
  department?: string;
  role: string;
  status: string;
  phone?: string;
  plant?: string;
  is_first_login?: boolean;
  last_login?: string;
  created_at: string;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Plant {
  id: number;
  plant_code: string;
  plant_name: string;
  address?: string;
  contact?: string;
  status: string;
  created_at: string;
}

export interface Department {
  id: number;
  dept_code: string;
  dept_name: string;
  plant_id?: number;
  head_name?: string;
  status: string;
  created_at: string;
}

export interface Location {
  location_id: string;
  location_code?: string;
  location_name: string;
  plant?: string;
  area?: string;
  department?: string;
  building?: string;
  floor?: string;
  machine?: string;
  required_asset_type?: string;
  required_capacity?: string;
  risk_category?: string;
  qr_code?: string;
  qr_image_path?: string;
  current_asset_id?: string;
  status: string;
  inspection_frequency?: number;
  last_inspection_date?: string;
  gps_lat?: number;
  gps_lng?: number;
  created_at?: string;
}

export interface Asset {
  asset_id: string;
  serial_number: string;
  asset_type: string;
  capacity?: string;
  manufacturer?: string;
  manufacturing_date?: string;
  refill_date?: string;
  expiry_date?: string;
  inspection_frequency?: number;
  amc_due_date?: string;
  barcode?: string;
  photo?: string;
  remarks?: string;
  current_location_id?: string;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface AssetHistory {
  id: number;
  asset_id: string;
  old_location?: string;
  new_location?: string;
  movement_type?: string;
  movement_reason?: string;
  approval_by?: string;
  comments?: string;
  movement_date: string;
  changed_by?: string;
}

export interface Inspection {
  inspection_id: number;
  location_id: string;
  asset_id?: string;
  inspector?: string;
  inspection_date: string;
  pressure?: string;
  seal?: string;
  pin?: string;
  gauge?: string;
  hose?: string;
  nozzle?: string;
  visibility?: string;
  accessibility?: string;
  mounting?: string;
  safety_tag?: string;
  cylinder_damage?: string;
  overall_status?: string;
  remarks?: string;
  photo?: string;
  created_at?: string;
}

export interface Maintenance {
  maintenance_id: number;
  asset_id?: string;
  location_id?: string;
  issue?: string;
  priority: string;
  assigned_to?: string;
  technician_id?: number;
  verified_by?: string;
  status: string;
  source?: string;
  opened_date: string;
  completion_date?: string;
  closed_date?: string;
  remarks?: string;
  inspection_id?: number;
  created_at?: string;
}

export interface Notification {
  id: number;
  type: string;
  message: string;
  is_read: boolean;
  related_id?: string;
  related_type?: string;
  created_at: string;
}

export interface Attachment {
  id: number;
  related_id: string;
  related_type: string;
  file_path: string;
  file_type?: string;
  label?: string;
  created_at: string;
}

export interface DashboardStats {
  total_locations: number;
  total_assets: number;
  installed_assets: number;
  unassigned_assets: number;
  inspection_due_today: number;
  inspection_completed_today: number;
  open_maintenance: number;
  expired_assets: number;
  refill_due: number;
  compliance_percent: number;
  overdue_inspections: number;
}

export interface MonthlyTrendItem {
  month: string;
  inspections: number;
  maintenance: number;
  passed: number;
  failed: number;
}

export interface DepartmentStatsItem {
  department: string;
  total_locations: number;
  installed: number;
  compliance: number;
}

export interface RiskStatsItem {
  risk_category: string;
  count: number;
}

export interface SearchResult {
  type: string;
  id: string;
  title: string;
  subtitle?: string;
  status?: string;
  url?: string;
}

export interface AssignmentValidationError {
  message: string;
  errors: string[];
  warnings: string[];
}

export interface SystemConfig {
  id: number;
  key: string;
  value?: string;
  description?: string;
}
