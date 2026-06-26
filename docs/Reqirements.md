# User Stories (System Requirements)

## Epic 1: Authentication and User Management

**User Story 1 (Sign Up and Login):** As a new user, I want to sign up in the system with an email and password and log into my account, so that I can use the messenger's features.
* **Acceptance Criteria:** Successful sign-up with a unique email and password; secure Login and Logout.

**User Story 2 (Profile Management):** As a user, I want to edit my Profile information and view others' profiles, so that I have a transparent identity in the network.
* **Acceptance Criteria:** Ability to upload a photo and bio; display of the profile Modal by clicking on people's names.

## Epic 2: Messaging Core

**User Story 3 (Send and Receive Messages):** As a user, I want to send and receive text messages and media files in chats.
* **Acceptance Criteria:** Display messages in chronological order of sending; support for common formats.

**User Story 4 (Edit and Delete Messages):** As the message sender, I want to edit or delete my message.
* **Acceptance Criteria:** Receive an "Edited" tag; only the author is allowed to edit.

**User Story 5 (Search):** As a user, I want to search within the message history of a chat.
* **Acceptance Criteria:** Filtering search results based on keywords.

## Epic 3: Spaces and Permissions Management

**User Story 6 (Create and Manage Channels):** As a user, I want to create a channel and create topics within it.
* **Acceptance Criteria:** The Owner can edit or delete the channel.

**User Story 7 (Create Groups):** As a user, I want to create private groups and set invitation restrictions.

**User Story 8 (Role Management):** As a channel admin, I want to define roles with different permission levels.
* **Acceptance Criteria:** The admin can delete other users' messages based on their role.

**User Story 9 (Media Restrictions):** As a channel admin, I want to restrict sending media for regular users.

## Epic 4: Bonus Requirements

**User Story 10 (Live Chat):** As a user, I want messages to be received in real-time (Using WebSockets).

**User Story 11 (Scheduled Messages):** As a user, I want to schedule a message to be sent automatically at a specific date and time (Using Celery/RabbitMQ).