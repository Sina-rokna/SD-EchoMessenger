# Security and Privacy Notes

## Authentication

- Passwords are processed only by Django's password hashers and are never
  stored or logged as plain text.
- Email and username are unique at both serializer and database levels.
- The browser uses an HttpOnly same-origin session cookie.
- Production mode enables secure cookies, HTTPS redirect, HSTS, and trusted
  origin configuration from environment variables.

## Request protection

- Unsafe REST requests require a CSRF token.
- Login, registration, and message creation have rate-limit scopes.
- Serializers expose explicit fields and reject unexpected privilege fields.
- Validation limits names, biographies, message content, future timestamps, and
  file count/size/type.

## Authorization

- Read, search, download, and WebSocket connection all require current space
  membership.
- Only the sender edits a message.
- Channel capabilities come from the owner's implicit full access or the
  member's stored role.
- A manager cannot create or assign a role containing a capability they do not
  have.
- Scheduled delivery rechecks membership and permission at dispatch time.
- Profile updates are restricted to the authenticated profile owner.

## Attachment handling

- Storage paths use generated names instead of client filenames.
- Original names are metadata only and are escaped when returned.
- The server checks count, declared type, extension category, and maximum size.
- Downloads use an authenticated endpoint and `X-Content-Type-Options: nosniff`.
- Nginx and Django both enforce upload limits.

## Frontend safety

- Message and profile text are rendered as plain React text nodes.
- The application does not use raw HTML rendering for user content.
- API errors are normalized before display; server stack traces are never shown.
- Destructive actions require a confirmation step.

## Secret management

- `.env` is ignored.
- `.env.example` contains only development-safe placeholders.
- Production secret key, hostnames, database password, broker URLs, and secure
  cookie switch are environment variables.
- Logs omit message content, passwords, cookies, authorization headers, and
  uploaded file bytes.

