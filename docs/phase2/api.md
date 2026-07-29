# EchoMessenger API Guide

The browser and API share one origin. All routes are prefixed with
`/api/v1/`, all timestamps use ISO 8601 UTC, and protected routes use the
Django session cookie.

## CSRF and authentication

Before the first unsafe request, call:

```http
GET /api/v1/auth/csrf/
```

Keep the returned cookie and send its `csrftoken` value in the
`X-CSRFToken` header on `POST`, `PATCH`, and `DELETE`.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/auth/register/` | Create and immediately sign in a user |
| `POST` | `/auth/login/` | Sign in with email and password |
| `POST` | `/auth/logout/` | End the current session |
| `GET` | `/auth/me/` | Return the signed-in private profile |
| `PATCH` | `/users/me/` | Update username, email, avatar, bio, or group invite policy |
| `GET` | `/users/{id}/` | View a public profile |
| `GET` | `/users/?search=term` | Find active users without exposing email |

Registration body:

```json
{
  "username": "sina",
  "email": "sina@example.test",
  "password": "A-strong-demo-password"
}
```

## Spaces

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/spaces/` | List spaces joined by the current user |
| `POST` | `/spaces/` | Create a `GROUP` or `CHANNEL` |
| `POST` | `/spaces/direct/` | Get or create the unique direct chat with a user |
| `GET` | `/spaces/{id}/` | Read one joined space |
| `PATCH` | `/spaces/{id}/` | Edit an authorized group/channel |
| `DELETE` | `/spaces/{id}/` | Delete an authorized group/channel |

Create a channel:

```json
{
  "type": "CHANNEL",
  "name": "Course Project",
  "member_ids": ["8d39b600-12c7-45bd-965c-a36c51953e9b"]
}
```

The response includes the caller's role and effective permission map so the
client can explain available actions. The server independently checks every
action.

## Members, topics, and roles

| Method | Path | Purpose |
|---|---|---|
| `GET`, `POST` | `/spaces/{id}/members/` | List or add members |
| `DELETE` | `/spaces/{id}/members/me/` | Leave a group/channel |
| `PATCH` | `/spaces/{id}/members/{user_id}/` | Assign a channel role |
| `DELETE` | `/spaces/{id}/members/{user_id}/` | Remove a member |
| `GET`, `POST` | `/spaces/{id}/topics/` | List or create channel topics |
| `PATCH`, `DELETE` | `/topics/{topic_id}/` | Rename or delete a topic |
| `GET`, `POST` | `/spaces/{id}/roles/` | List or create data-backed roles |
| `PATCH`, `DELETE` | `/roles/{role_id}/` | Update or delete a non-default role |

Role permissions:

```json
{
  "name": "Moderator",
  "can_send_messages": true,
  "can_send_media": true,
  "can_manage_topics": true,
  "can_manage_members": false,
  "can_delete_messages": true,
  "can_manage_roles": false,
  "can_manage_space": false
}
```

## Messages and attachments

| Method | Path | Purpose |
|---|---|---|
| `GET`, `POST` | `/spaces/{id}/messages/` | History or message creation |
| `GET` | `/spaces/{id}/messages/search/?q=term` | Search text inside one joined chat |
| `PATCH`, `DELETE` | `/messages/{id}/` | Edit own text or delete with permission |
| `GET` | `/attachments/{id}/download/` | Authorized attachment download |

For a text-only message, send JSON:

```json
{
  "text": "The Phase 2 build is ready.",
  "topic_id": "47cc70e7-2773-4eb9-813f-04ed3b8a017d",
  "client_nonce": "1db3022e-cbb7-445a-a3aa-c77bb326dc06"
}
```

For files, use `multipart/form-data`. Repeat the `attachments` field for up to
five files. `topic_id` is required for a channel and omitted for a direct chat
or group.

History and search use page-number pagination. For message history, page 1
contains the newest batch; clients may sort each returned batch
chronologically for display while following `next` to load earlier messages:

```json
{
  "count": 42,
  "next": null,
  "previous": null,
  "results": []
}
```

## Scheduled messages

Supplying a future `scheduled_for` during normal message creation stores a
`PENDING` message instead of sending it:

```json
{
  "text": "Reminder: presentation at 10:00.",
  "scheduled_for": "2026-07-30T06:30:00Z"
}
```

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/scheduled-messages/` | List the current user's pending messages |
| `PATCH` | `/scheduled-messages/{id}/` | Change pending text, topic, or time |
| `DELETE` | `/scheduled-messages/{id}/` | Cancel a pending message |

When due, Celery changes the status to `SENT`, persists notifications, and
emits `scheduled_message.sent`. The user's browser does not need to be open.

## Notifications

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/notifications/` | Paginated persistent notifications |
| `GET` | `/notifications/?unread=true` | Unread notifications only |
| `POST` | `/notifications/{id}/read/` | Mark one as read |
| `POST` | `/notifications/read-all/` | Mark all current-user items as read |

## WebSockets

Connect using the existing session cookie:

- `/ws/spaces/{space_id}/`
- `/ws/notifications/`

The space socket rejects non-members and rechecks membership before every
event. Both sockets are read-only event streams; REST remains the single
validated write path.

Event envelope:

```json
{
  "type": "message.created",
  "event_id": "a4bf5d5f-1ae3-4f45-90ca-8093d80f6860",
  "occurred_at": "2026-07-29T12:00:00Z",
  "payload": {}
}
```

Supported application events are `message.created`, `message.updated`,
`message.deleted`, `scheduled_message.sent`, `notification.created`,
`space.updated`, and `member.updated`. Clients may send `{"type":"ping"}` and
receive `{"type":"pong"}`.

## Health checks

- `GET /api/v1/health/live/` verifies the process.
- `GET /api/v1/health/ready/` verifies database access and reports service
  readiness.
