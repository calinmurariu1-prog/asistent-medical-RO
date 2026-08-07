export interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: "patient" | "doctor" | "admin";
  is_active: boolean;
  is_email_verified: boolean;
  mfa_enabled: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface PatientProfile {
  id: number;
  first_name: string | null;
  last_name: string | null;
  birth_date: string | null;
  sex: string | null;
  weight_kg: number | null;
  height_cm: number | null;
  blood_type: string | null;
  phone: string | null;
  bmi: number | null;
}

export type LabFlag =
  | "normal"
  | "high"
  | "low"
  | "critical_high"
  | "critical_low";

export interface LabResult {
  id: number;
  document_id: number | null;
  analyte: string;
  value: number | null;
  value_text: string | null;
  unit: string | null;
  ref_low: number | null;
  ref_high: number | null;
  flag: LabFlag;
  measured_on: string | null;
  ai_explanation: string | null;
}

export interface DocumentItem {
  id: number;
  category: string;
  original_filename: string;
  content_type: string | null;
  size_bytes: number | null;
  document_date: string | null;
  status: "pending" | "processing" | "done" | "failed";
  ai_summary: string | null;
  processed_at: string | null;
  created_at: string;
}

export interface Medication {
  id: number;
  name: string;
  active_substance: string | null;
  dose: string | null;
  frequency: string | null;
  interval: string | null;
  start_date: string | null;
  end_date: string | null;
  is_active: boolean;
  notes: string | null;
}

export interface Appointment {
  id: number;
  type: string;
  title: string;
  location: string | null;
  doctor_id: number | null;
  starts_at: string;
  ends_at: string | null;
  status: string;
  notes: string | null;
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  sources: Array<Record<string, unknown>>;
  created_at: string;
}

export interface Chat {
  id: number;
  title: string | null;
  created_at: string;
  messages?: ChatMessage[];
}

export interface SpecialtySuggestion {
  specialty: string;
  reasons: string[];
}

export interface ProviderResult {
  name: string;
  specialty: string;
  address: string | null;
  lat: number;
  lng: number;
  distance_km: number | null;
  rating: number | null;
  ratings_total: number | null;
  place_id: string | null;
  phone: string | null;
  maps_url: string | null;
  score: number | null;
  score_label: string | null;
}

export interface NearbyProviders {
  specialty: string;
  center: { lat: number; lng: number };
  radius_m: number;
  provider_source: string;
  results: ProviderResult[];
  disclaimer: string;
}

export interface AiSkill {
  name: string;
  title: string;
  description: string;
  inputs: string[];
}

export type HealthSourceId =
  | "apple_health"
  | "google_health"
  | "huawei_health"
  | "manual";

export interface HealthSourceInfo {
  source: HealthSourceId;
  label: string;
  connected: boolean;
  sample_count: number;
  how_to: string;
  accepts: string;
}

export interface HealthMetricSummary {
  metric_type: string;
  label: string;
  unit: string;
  count: number;
  min: number | null;
  max: number | null;
  avg: number | null;
  latest_value: number | null;
  latest_at: string | null;
}

export interface HealthSummary {
  total_samples: number;
  connected_sources: string[];
  metrics: HealthMetricSummary[];
}

export interface HealthImportResult {
  source: HealthSourceId;
  imported: number;
  duplicates: number;
  skipped: number;
  metrics: Record<string, number>;
  message: string;
}

export interface Dashboard {
  lab_summary: {
    total_analytes: number;
    abnormal_count: number;
    critical_count: number;
  };
  recent_documents: DocumentItem[];
  active_medications: { id: number; name: string; dose: string | null }[];
  upcoming_appointments: { id: number; title: string; starts_at: string }[];
  alerts: string[];
  recommendations_preview: string[];
  unread_notifications: number;
}
