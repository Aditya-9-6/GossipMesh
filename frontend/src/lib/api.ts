import {
  AuditEvent,
  BillingSubscription,
  Finding,
  Member,
  Organization,
  Repository,
  ReviewRun,
  User,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('gossipmesh_token', token);
    }
  }

  getToken(): string | null {
    if (!this.token && typeof window !== 'undefined') {
      this.token = localStorage.getItem('gossipmesh_token');
    }
    return this.token;
  }

  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('gossipmesh_token');
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Network error' }));
      throw new Error(errorData.detail || `Request failed with status ${response.status}`);
    }

    return response.json();
  }

  // Auth
  async login(formData: URLSearchParams): Promise<{ access_token: string; token_type: string }> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
    });
    if (!res.ok) throw new Error('Login failed');
    const data = await res.json();
    this.setToken(data.access_token);
    return data;
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>('/users/me');
  }

  // Organizations
  async getOrganizations(): Promise<Organization[]> {
    return this.request<Organization[]>('/organizations');
  }

  async createOrganization(name: string): Promise<Organization> {
    return this.request<Organization>('/organizations', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  // Repositories
  async getRepositories(orgId: number): Promise<Repository[]> {
    return this.request<Repository[]>(`/repositories?organization_id=${orgId}`);
  }

  // Runs
  async getReviewRuns(orgId: number): Promise<ReviewRun[]> {
    return this.request<ReviewRun[]>(`/runs?organization_id=${orgId}`);
  }

  // Findings
  async getFindings(orgId: number, runId?: number): Promise<Finding[]> {
    const url = runId ? `/findings?run_id=${runId}` : `/findings?organization_id=${orgId}`;
    return this.request<Finding[]>(url);
  }

  // Members
  async getMembers(orgId: number): Promise<Member[]> {
    return this.request<Member[]>(`/organizations/${orgId}/members`);
  }

  // Billing
  async getSubscription(orgId: number): Promise<{ status: string; subscription: BillingSubscription | null }> {
    return this.request(`/billing/subscription?organization_id=${orgId}`);
  }

  async createCheckoutSession(orgId: number, planId: string): Promise<{ url: string }> {
    return this.request('/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ organization_id: orgId, plan_id: planId, price_id: `price_${planId}` }),
    });
  }

  async createPortalSession(orgId: number): Promise<{ url: string }> {
    return this.request('/billing/portal', {
      method: 'POST',
      body: JSON.stringify({ organization_id: orgId }),
    });
  }

  // Audit Logs
  async getAuditLogs(orgId: number): Promise<AuditEvent[]> {
    return this.request<AuditEvent[]>(`/enterprise/audit-logs?organization_id=${orgId}`);
  }
}

export const api = new ApiClient();
