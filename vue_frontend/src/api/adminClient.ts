/** Axios-клиент для админских API-эндпоинтов. */
import axios from "axios";
import { installJwtInterceptors } from "./jwtAuth";

export const adminApiClient = axios.create({
  baseURL: "/api",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json"
  }
});

installJwtInterceptors(adminApiClient);
