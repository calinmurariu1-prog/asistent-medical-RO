import { MetricDetail } from "@/components/metric-detail";

// Static export needs the set of metric slugs known at build time.
const METRICS = [
  "steps",
  "heart_rate",
  "resting_heart_rate",
  "blood_pressure_systolic",
  "blood_pressure_diastolic",
  "blood_glucose",
  "oxygen_saturation",
  "body_weight",
  "height",
  "body_fat",
  "body_temperature",
  "respiratory_rate",
  "sleep",
  "active_energy",
  "distance",
  "vo2max",
];

export function generateStaticParams() {
  return METRICS.map((metric) => ({ metric }));
}

export default function MetricPage({ params }: { params: { metric: string } }) {
  return <MetricDetail metric={params.metric} />;
}
