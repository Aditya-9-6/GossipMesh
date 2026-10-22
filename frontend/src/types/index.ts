export interface User {
  id: number;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
}

export interface Organization {
  id: number;
  name: string;
  role?: string;
  created_at?: string;
}

export interface Repository {
  id: number;
  name: string;
  full_name: string;
  default_branch: string;
  organization_id: number;
  is_active: boolean;
}

export interface ReviewRun {
  id: number;
  workflow_id: number;
  repository_id: number;
  pr_number: number;
  commit_sha: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  findings_count: number;
  duration_seconds?: number;
  created_at: string;
}

export interface Finding {
  id: number;
  run_id: number;
  file_path: string;
  line_number: number;
  rule_id: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  message: string;
  status: 'open' | 'accepted' | 'dismissed' | 'false_positive';
  suggested_fix?: string;
}

export interface Member {
  user_id: number;
  email: string;
  role: 'owner' | 'billing_admin' | 'organization_admin' | 'security_admin' | 'developer' | 'reviewer';
  status: 'active' | 'invited' | 'suspended';
}

export interface BillingSubscription {
  id: string;
  plan_id: string;
  status: 'active' | 'trialing' | 'past_due' | 'canceled';
  quantity: number;
  cancel_at_period_end: boolean;
}

export interface AuditEvent {
  id: number;
  action: string;
  actor_id?: number;
  organization_id?: number;
  details?: Record<string, any>;
  timestamp: string;
}
