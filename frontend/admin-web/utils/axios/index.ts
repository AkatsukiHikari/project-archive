import { service } from "./service";
import { config } from "./config";
import type { RequestOption } from "./types";

const { default_headers } = config;

type RequestOptionWithoutMethod = Omit<RequestOption, "method">;

const request = (option: RequestOption) => {
  const { headersType, headers, ...otherOption } = option;
  return service({
    ...otherOption,
    headers: {
      "Content-Type": headersType || default_headers,
      ...headers,
    },
  });
};

export default {
  get: async <T = unknown>(option: RequestOptionWithoutMethod) => {
    const res = await request({ method: "GET", ...option });
    // res 已经是 { code, data, message }，取 .data 作为业务数据
    return (res as unknown as { data: T }).data;
  },
  post: async <T = unknown>(option: RequestOptionWithoutMethod) => {
    const res = await request({ method: "POST", ...option });
    return (res as unknown as { data: T }).data;
  },
  postOriginal: async (option: RequestOptionWithoutMethod) => {
    return await request({ method: "POST", ...option });
  },
  delete: async <T = unknown>(option: RequestOptionWithoutMethod) => {
    const res = await request({ method: "DELETE", ...option });
    return (res as unknown as { data: T }).data;
  },
  put: async <T = unknown>(option: RequestOptionWithoutMethod) => {
    const res = await request({ method: "PUT", ...option });
    return (res as unknown as { data: T }).data;
  },
  download: async <T = unknown>(option: RequestOptionWithoutMethod) => {
    const res = await request({
      method: "GET",
      responseType: "blob",
      ...option,
    });
    return res as unknown as Promise<T>;
  },
  upload: async <T = unknown>(option: RequestOptionWithoutMethod) => {
    option.headersType = "multipart/form-data";
    const res = await request({ method: "POST", ...option });
    return res as unknown as Promise<T>;
  },
};
