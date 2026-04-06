import { service as http } from "@/utils/axios/service";

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

export interface ScheduleParticipant {
  user_id: string;
  status: string;
}

export interface ScheduleEvent {
  id: string;
  title: string;
  description?: string;
  start_time: string;
  end_time: string;
  is_all_day: boolean;
  location?: string;
  event_type: string;
  creator_id: string;
  participants: ScheduleParticipant[];
}

export interface ScheduleEventCreate {
  title: string;
  description?: string;
  start_time: string;
  end_time: string;
  is_all_day?: boolean;
  location?: string;
  event_type?: string;
  participant_ids?: string[];
}

export const ScheduleAPI = {
  list: (startTime?: string, endTime?: string) =>
    http.get<ApiResponse<ScheduleEvent[]>, ApiResponse<ScheduleEvent[]>>(
      "/schedules",
      { params: { start_time: startTime, end_time: endTime } },
    ),
  create: (data: ScheduleEventCreate) =>
    http.post<ApiResponse<ScheduleEvent>, ApiResponse<ScheduleEvent>>(
      "/schedules",
      data,
    ),
  get: (id: string) =>
    http.get<ApiResponse<ScheduleEvent>, ApiResponse<ScheduleEvent>>(
      `/schedules/${id}`,
    ),
  update: (id: string, data: Partial<ScheduleEventCreate>) =>
    http.put<ApiResponse<ScheduleEvent>, ApiResponse<ScheduleEvent>>(
      `/schedules/${id}`,
      data,
    ),
  delete: (id: string) => http.delete(`/schedules/${id}`),
};
