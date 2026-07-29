export type SpaceType = "DIRECT" | "GROUP" | "CHANNEL";
export type InvitePolicy = "EVERYONE" | "NOBODY";
export type MessageStatus = "PENDING" | "SENT" | "CANCELLED" | "FAILED";

export interface User {
  id: string;
  username: string;
  email?: string;
  avatar_url?: string | null;
  bio?: string;
  group_invite_policy?: InvitePolicy;
  is_online?: boolean;
}

export interface PermissionSet {
  can_send_messages: boolean;
  can_send_media: boolean;
  can_manage_topics: boolean;
  can_manage_members: boolean;
  can_delete_messages: boolean;
  can_manage_roles: boolean;
  can_manage_space: boolean;
}

export const permissionKeys = [
  "can_send_messages",
  "can_send_media",
  "can_manage_topics",
  "can_manage_members",
  "can_delete_messages",
  "can_manage_roles",
  "can_manage_space",
] as const satisfies ReadonlyArray<keyof PermissionSet>;

export const noPermissions: PermissionSet = {
  can_send_messages: false,
  can_send_media: false,
  can_manage_topics: false,
  can_manage_members: false,
  can_delete_messages: false,
  can_manage_roles: false,
  can_manage_space: false,
};

export interface Space {
  id: string;
  name: string;
  display_name: string;
  type: SpaceType;
  avatar_url?: string | null;
  created_by: User;
  membership_count: number;
  my_role: Role | null;
  my_permissions: PermissionSet;
  created_at: string;
  updated_at: string;
  // Unread counts are client-side state; the current REST serializer does not
  // persist or return them.
  unread_count?: number;
}

export interface Topic {
  id: string;
  space: string;
  name: string;
  created_by: User;
  created_at: string;
  updated_at: string;
}

export interface Role extends PermissionSet {
  id: string;
  name: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface SpaceMember {
  id: string;
  user: User;
  role?: Role | null;
  joined_at: string;
}

export interface Attachment {
  id: string;
  original_name: string;
  content_type: string;
  size: number;
  category: "IMAGE" | "VIDEO" | "AUDIO" | "FILE";
  download_url: string;
  created_at: string;
}

export interface Message {
  id: string;
  space: string;
  topic_id?: string | null;
  sender: User;
  text: string;
  attachments: Attachment[];
  status: MessageStatus;
  sent_at?: string | null;
  created_at: string;
  edited_at?: string | null;
  scheduled_for?: string | null;
  is_edited: boolean;
  failure_reason: string;
  client_nonce?: string | null;
}

export interface Notification {
  id: string;
  event_type: "MESSAGE_CREATED" | "MEMBER_ADDED";
  actor?: User | null;
  space_id?: string | null;
  message_id?: string | null;
  is_read: boolean;
  created_at: string;
  read_at?: string | null;
}

export interface Page<T> {
  count?: number;
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface RealtimeEvent<T = unknown> {
  type:
    | "message.created"
    | "message.updated"
    | "message.deleted"
    | "scheduled_message.sent"
    | "notification.created"
    | "space.updated"
    | "member.updated";
  event_id: string;
  occurred_at: string;
  payload: T;
}

export function asPage<T>(value: Page<T> | T[]): Page<T> {
  return Array.isArray(value)
    ? { results: value, next: null, previous: null }
    : value;
}
