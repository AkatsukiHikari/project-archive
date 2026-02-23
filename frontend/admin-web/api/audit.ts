import { service as http } from "@/utils/axios/service";

export interface AuditLog {
  id: string;
  tenant_id?: string;
  user_id?: string;
  action: string;
  module: string;
  ip_address?: string;
  user_agent?: string;
  status: "success" | "failure";
  details?: any;
  error_message?: string;
  create_time: string;
}

export const AuditAPI = {
  list: (params?: {
    tenant_id?: string;
    user_id?: string;
    skip?: number;
    limit?: number;
  }) => http.get<any, { data: AuditLog[] }>("/audits", { params }),
};
