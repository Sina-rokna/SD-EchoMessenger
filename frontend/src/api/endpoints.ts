import { apiRequest } from "./client";
import {
  asPage,
  type InvitePolicy,
  type Message,
  type Notification,
  type Page,
  type PermissionSet,
  type Role,
  type Space,
  type SpaceMember,
  type SpaceType,
  type Topic,
  type User,
} from "./types";

export const authApi = {
  me: () => apiRequest<User>("/auth/me/"),
  login: (email: string, password: string) =>
    apiRequest<User>("/auth/login/", {
      method: "POST",
      body: { email, password },
    }),
  register: (username: string, email: string, password: string) =>
    apiRequest<User>("/auth/register/", {
      method: "POST",
      body: { username, email, password },
    }),
  logout: () => apiRequest<void>("/auth/logout/", { method: "POST" }),
};

export const usersApi = {
  get: (userId: string) => apiRequest<User>(`/users/${userId}/`),
  search: (query: string) =>
    apiRequest<Page<User> | User[]>(`/users/?search=${encodeURIComponent(query)}`).then(
      asPage,
    ),
  updateMe: (values: {
    username?: string;
    bio?: string;
    group_invite_policy?: InvitePolicy;
    avatar?: File;
  }) => {
    const body = new FormData();
    Object.entries(values).forEach(([key, value]) => {
      if (value !== undefined) body.append(key, value);
    });
    return apiRequest<User>("/users/me/", { method: "PATCH", body });
  },
};

export const spacesApi = {
  list: () => apiRequest<Page<Space> | Space[]>("/spaces/").then(asPage),
  create: (values: {
    type: Exclude<SpaceType, "DIRECT">;
    name: string;
    member_ids: string[];
  }) => apiRequest<Space>("/spaces/", { method: "POST", body: values }),
  direct: (userId: string) =>
    apiRequest<Space>("/spaces/direct/", {
      method: "POST",
      body: { user_id: userId },
    }),
  update: (spaceId: string, values: { name?: string; avatar?: File }) => {
    const body = new FormData();
    Object.entries(values).forEach(([key, value]) => {
      if (value !== undefined) body.append(key, value);
    });
    return apiRequest<Space>(`/spaces/${spaceId}/`, {
      method: "PATCH",
      body,
    });
  },
  remove: (spaceId: string) =>
    apiRequest<void>(`/spaces/${spaceId}/`, { method: "DELETE" }),
  members: (spaceId: string) =>
    apiRequest<Page<SpaceMember> | SpaceMember[]>(
      `/spaces/${spaceId}/members/`,
    ).then(asPage),
  addMembers: (spaceId: string, userIds: string[], roleId?: string) =>
    Promise.all(
      userIds.map((userId) =>
        apiRequest<SpaceMember>(`/spaces/${spaceId}/members/`, {
          method: "POST",
          body: {
            user_id: userId,
            ...(roleId ? { role_id: roleId } : {}),
          },
        }),
      ),
    ),
  updateMember: (spaceId: string, userId: string, roleId: string) =>
    apiRequest<SpaceMember>(`/spaces/${spaceId}/members/${userId}/`, {
      method: "PATCH",
      body: { role_id: roleId },
    }),
  removeMember: (spaceId: string, userId: string) =>
    apiRequest<void>(`/spaces/${spaceId}/members/${userId}/`, {
      method: "DELETE",
    }),
  leave: (spaceId: string) =>
    apiRequest<void>(`/spaces/${spaceId}/members/me/`, { method: "DELETE" }),
  topics: (spaceId: string) =>
    apiRequest<Page<Topic> | Topic[]>(`/spaces/${spaceId}/topics/`).then(asPage),
  createTopic: (spaceId: string, name: string) =>
    apiRequest<Topic>(`/spaces/${spaceId}/topics/`, {
      method: "POST",
      body: { name },
    }),
  updateTopic: (topicId: string, name: string) =>
    apiRequest<Topic>(`/topics/${topicId}/`, {
      method: "PATCH",
      body: { name },
    }),
  removeTopic: (topicId: string) =>
    apiRequest<void>(`/topics/${topicId}/`, { method: "DELETE" }),
  roles: (spaceId: string) =>
    apiRequest<Page<Role> | Role[]>(`/spaces/${spaceId}/roles/`).then(asPage),
  createRole: (spaceId: string, name: string, permissions: PermissionSet) =>
    apiRequest<Role>(`/spaces/${spaceId}/roles/`, {
      method: "POST",
      body: { name, ...permissions },
    }),
  updateRole: (
    roleId: string,
    values: { name?: string } & Partial<PermissionSet>,
  ) =>
    apiRequest<Role>(`/roles/${roleId}/`, {
      method: "PATCH",
      body: values,
    }),
  removeRole: (roleId: string) =>
    apiRequest<void>(`/roles/${roleId}/`, { method: "DELETE" }),
};

export const messagesApi = {
  list: (spaceId: string, topicId?: string | null, pageUrl?: string) => {
    const query = topicId ? `?topic=${encodeURIComponent(topicId)}` : "";
    return apiRequest<Page<Message> | Message[]>(
      pageUrl ?? `/spaces/${spaceId}/messages/${query}`,
    ).then(asPage);
  },
  create: (
    spaceId: string,
    values: {
      text: string;
      topic_id?: string | null;
      attachments?: File[];
      scheduled_for?: string;
      client_nonce?: string;
    },
  ) => {
    const body = new FormData();
    body.append("text", values.text);
    if (values.topic_id) body.append("topic_id", values.topic_id);
    if (values.scheduled_for) body.append("scheduled_for", values.scheduled_for);
    if (values.client_nonce) body.append("client_nonce", values.client_nonce);
    values.attachments?.forEach((file) => body.append("attachments", file));
    return apiRequest<Message>(`/spaces/${spaceId}/messages/`, {
      method: "POST",
      body,
    });
  },
  update: (messageId: string, text: string) =>
    apiRequest<Message>(`/messages/${messageId}/`, {
      method: "PATCH",
      body: { text },
    }),
  remove: (messageId: string) =>
    apiRequest<void>(`/messages/${messageId}/`, { method: "DELETE" }),
  search: (spaceId: string, query: string, topicId?: string | null) => {
    const params = new URLSearchParams({ q: query });
    if (topicId) params.set("topic", topicId);
    return apiRequest<Page<Message> | Message[]>(
      `/spaces/${spaceId}/messages/search/?${params}`,
    ).then(asPage);
  },
  scheduled: () =>
    apiRequest<Page<Message> | Message[]>("/scheduled-messages/").then(asPage),
  updateScheduled: (
    messageId: string,
    values: {
      text?: string;
      topic_id?: string;
      scheduled_for?: string;
    },
  ) =>
    apiRequest<Message>(`/scheduled-messages/${messageId}/`, {
      method: "PATCH",
      body: values,
    }),
  cancelScheduled: (messageId: string) =>
    apiRequest<void>(`/scheduled-messages/${messageId}/`, {
      method: "DELETE",
    }),
};

export const notificationsApi = {
  list: () =>
    apiRequest<Page<Notification> | Notification[]>("/notifications/").then(
      asPage,
    ),
  markRead: (notificationId: string) =>
    apiRequest<Notification>(`/notifications/${notificationId}/read/`, {
      method: "POST",
    }),
  readAll: () =>
    apiRequest<{ updated: number }>("/notifications/read-all/", {
      method: "POST",
    }),
};
