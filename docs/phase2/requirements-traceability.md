# Requirements Traceability

This matrix connects the course specification and Phase 1 user stories to the
final product. File paths are implementation evidence; the automated tests
exercise the same rules independently.

| ID | Requirement | Product behavior | Primary evidence |
|---|---|---|---|
| FR-01 | Sign up, login, logout | Unique email and username, hashed password, session login/logout, CSRF-protected API | `backend/apps/accounts/`, frontend auth feature |
| FR-02 | Send and receive messages | Text or attachments in direct chats, groups, and channel topics; chronological history | `backend/apps/messaging/`, chat interface |
| FR-03 | Edit and delete messages | Sender-only edit with edited timestamp; sender or authorized manager deletion | messaging services and permission tests |
| FR-04 | Create channels and topics | Channel creator becomes owner; authorized users create named topics | `backend/apps/spaces/`, space settings |
| FR-05 | Create groups | Multi-user private groups; invite policy is checked before adding a user | spaces services and profile settings |
| FR-06 | Edit/delete channels and groups | Channel owner/authorized role manages channels; every group member may edit/delete the group, exactly as specified | centralized space permissions |
| FR-07 | Send media | Up to five protected image/video/audio/general files, 10 MiB each; channel role may disable upload | attachment validation and protected download |
| FR-08 | Roles and access restrictions | Named database-backed channel roles with message, media, topic, member, role, delete, and space permissions | `Role`, membership role assignment, role UI |
| FR-09 | Search messages | Case-insensitive text search within one space and only for a member | message search endpoint and isolation tests |
| FR-10 | View/manage profiles | User edits avatar, biography, and invite policy; authenticated users can view another profile | accounts API and profile modal |
| FR-11 | Notifications | Message/member events create persistent unread notifications | notifications module and notification panel |
| B-01 | Live chat and notifications | Redis-backed WebSockets update messages and notifications without refresh | Channels consumers, realtime tests, reconnecting client |
| B-02 | Scheduled messages | Pending message is dispatched at the selected UTC time even while sender is offline; worker retries are idempotent | Celery Beat task and scheduling tests |

## Acceptance summary

- All writes are authorized on the server, even when a client constructs a
  request manually.
- All conversations support their required content type.
- The bonus features are integrated into the normal chat interface, not exposed
  as isolated demo endpoints.
- The Docker Compose runtime includes every Phase 1 infrastructure component.
- The neutral three-column interface follows the Phase 1 wireframe while adding
  the management dialogs that the wireframe did not show.

## Deliberate Phase 2 clarifications

The project statement left several details to the stakeholder/team. The final
product uses these explicit decisions:

- Group invite privacy has two options: `EVERYONE` and `NOBODY`.
- Topics are named channel subspaces, not free-form message tags.
- Message deletion removes the database row and stored attachment bytes; a
  committed `message.deleted` event tells connected clients to remove it.
- Timestamps are stored in UTC and displayed in the browser's local timezone.
- Scheduled messages may be edited or cancelled while still pending.
- SSO and voice chat are not implemented because they appeared only as generic
  wireframe placeholders and were absent from the requirements and data model.
