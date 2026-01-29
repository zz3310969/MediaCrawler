// 代理相关类型定义

export interface ProxyInfo {
  proxy_id: string;
  ip: string;
  port: number;
  protocol: string;
  username?: string;
  source: string;
  country: string;
  province?: string;
  city?: string;
  isp?: string;
  is_active: boolean;
  quality_score: number;
  created_at?: string;
  updated_at?: string;
  expired_at?: string;
}

export interface QualityMetrics {
  proxy_id: string;
  total_requests: number;
  success_requests: number;
  failed_requests: number;
  success_rate: number;
  avg_response_time: number;
  p95_response_time?: number;
  consecutive_failures: number;
  quality_score: number;
  last_success_at?: string;
  last_failure_at?: string;
}

export interface ProxyWithQuality extends ProxyInfo {
  quality?: QualityMetrics;
}

export interface BindingInfo {
  binding_id: string;
  account_id: string;
  platform: string;
  proxy_id: string;
  proxy_ip?: string;
  proxy_port?: number;
  is_sticky: boolean;
  status: string;
  bound_at?: string;
  last_used_at?: string;
  rebind_count: number;
}

export interface OverviewStats {
  total_proxies: number;
  active_proxies: number;
  total_bindings: number;
  active_bindings: number;
  today_requests: number;
  today_success_rate: number;
  avg_quality_score: number;
}

export interface DailyStats {
  date: string;
  total_requests: number;
  success_requests: number;
  failed_requests: number;
  success_rate: number;
  avg_response_time: number;
  total_bytes_sent: number;
  total_bytes_received: number;
}

export interface GlobalSettings {
  enable_proxy: boolean;
  proxy_pool_size: number;
  validate_on_get: boolean;
  validate_timeout: number;
  enable_binding: boolean;
  binding_sticky: boolean;
  auto_rebind: boolean;
  max_bindings_per_proxy: number;
  prefer_similar_region: boolean;
}

export interface QualitySettings {
  enabled: boolean;
  sample_window: number;
  time_window_hours: number;
  min_quality_score: number;
  min_requests_for_retire: number;
  max_consecutive_failures: number;
  auto_retire_enabled: boolean;
  check_interval_seconds: number;
}

export interface FailoverSettings {
  enabled: boolean;
  strategy: string;
  max_retries: number;
  retry_delay_seconds: number;
  cb_failure_threshold: number;
  cb_recovery_timeout: number;
}

export interface ProxySettings {
  global_settings: GlobalSettings;
  quality: QualitySettings;
  failover: FailoverSettings;
}

export interface SourceConfig {
  name: string;
  enabled: boolean;
  priority: number;
  api_url?: string;
  file_path?: string;
  auto_reload?: boolean;
  default_protocol?: string;
}

export interface ProxyListResponse {
  total: number;
  items: ProxyInfo[];
}

export interface BindingListResponse {
  total: number;
  items: BindingInfo[];
}

export interface ProxyImportItem {
  ip: string;
  port: number;
  protocol?: string;
  username?: string;
  password?: string;
  country?: string;
  province?: string;
  city?: string;
}

