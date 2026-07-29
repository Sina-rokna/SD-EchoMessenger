# EchoMessenger Phase 2 - Shared Implementation Contract

This document is the integration contract for the Phase 2 implementation. It
extends the Phase 1 design only where the original ERD could not represent an
explicit requirement.

## Architecture

- Django 5.2 modular monolith, Django REST Framework, and Django Channels
- React + TypeScript client built with Vite
- PostgreSQL as the durable database
- Redis as the Channels layer
- RabbitMQ as the Celery broker
- Celery worker and beat for restart-safe scheduled delivery
- Nginx as the single HTTP/WebSocket entry point
- Same-origin Django session authentication and CSRF protection

## Domain rules

- `ChatSpace` has one of `DIRECT`, `GROUP`, or `CHANNEL`.
- A direct space has exactly two members and one canonical `direct_key`.
- A channel contains named topics. Channel messages must select one of that
  channel's topics.
- Groups and direct spaces carry messages without topics.
- Only the sender may edit a message.
- The sender, an authorized channel manager, or any group member may delete a
  message. Any group member may edit or delete the group, matching the literal
  course specification.
- Channel permissions are stored in editable `Role` records. Owners have every
  permission and role assignment must not enable privilege escalation.
- A user whose group-invite policy is `NOBODY` cannot be added to a group by
  another user.
- Message text is rendered as plain text. A message requires text or at least
  one attachment.
- Scheduled messages are stored as `PENDING`, dispatched in UTC, then atomically
  become `SENT`. Repeated worker execution must not duplicate them.

## REST API

All endpoints are under `/api/v1/`.

### Authentication and profiles

- `GET /auth/csrf/`
- `POST /auth/register/`
- `POST /auth/login/`
- `POST /auth/logout/`
- `GET /auth/me/`
- `PATCH /users/me/`
- `GET /users/{user_id}/`
- `GET /users/?search=...`

### Spaces, members, topics, and roles

- `GET|POST /spaces/`
- `POST /spaces/direct/`
- `GET|PATCH|DELETE /spaces/{space_id}/`
- `GET|POST /spaces/{space_id}/members/`
- `DELETE /spaces/{space_id}/members/me/`
- `PATCH|DELETE /spaces/{space_id}/members/{user_id}/`
- `GET|POST /spaces/{space_id}/topics/`
- `PATCH|DELETE /topics/{topic_id}/`
- `GET|POST /spaces/{space_id}/roles/`
- `PATCH|DELETE /roles/{role_id}/`

### Messages, scheduling, and notifications

- `GET|POST /spaces/{space_id}/messages/`
- `GET /spaces/{space_id}/messages/search/?q=...`
- `PATCH|DELETE /messages/{message_id}/`
- `GET /scheduled-messages/`
- `PATCH|DELETE /scheduled-messages/{message_id}/`
- `GET /notifications/`
- `POST /notifications/{notification_id}/read/`
- `POST /notifications/read-all/`
- `GET /attachments/{attachment_id}/download/`
- `GET /health/live/`
- `GET /health/ready/`

Unsafe requests use JSON unless attachments are present, in which case message
creation uses multipart form data. Pagination responses use
`{"results": [...], "next": "...", "previous": "..."}`.

## WebSocket API

- `/ws/spaces/{space_id}/`
- `/ws/notifications/`

The server authenticates the session cookie and verifies membership. REST
requests perform writes; WebSockets deliver committed events:

- `message.created`
- `message.updated`
- `message.deleted`
- `scheduled_message.sent`
- `notification.created`
- `space.updated`
- `member.updated`

Every event uses this envelope:

```json
{
  "type": "message.created",
  "event_id": "uuid",
  "occurred_at": "2026-07-29T12:00:00Z",
  "payload": {}
}
```

## Operational defaults

- All stored timestamps are UTC; the browser displays local time.
- Maximum upload size is 10 MiB per attachment and five attachments per
  message.
- Allowed categories are image, video, audio, and general file.
- Attachment downloads are authorized by space membership.
- Celery Beat scans due scheduled messages every five seconds.
- Demo data are created only by the explicit `seed_demo` command.

