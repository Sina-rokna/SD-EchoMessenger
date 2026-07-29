import { type FormEvent, useEffect, useMemo, useState } from "react";
import {
  Hash,
  Pencil,
  Plus,
  Settings,
  Shield,
  Trash2,
  UserMinus,
  Users,
} from "lucide-react";

import { spacesApi } from "../../api/endpoints";
import {
  noPermissions,
  permissionKeys,
  type PermissionSet,
  type Role,
  type Space,
  type SpaceMember,
  type Topic,
  type User,
} from "../../api/types";
import {
  Avatar,
  Button,
  EmptyState,
  ErrorNotice,
  Field,
  IconButton,
  Modal,
} from "../../components/ui";
import { useToast } from "../../components/ToastProvider";
import { UserSearch } from "./UserSearch";

type SettingsTab = "general" | "members" | "topics" | "roles";

interface SpaceSettingsModalProps {
  space: Space | null;
  currentUserId: string;
  members: SpaceMember[];
  topics: Topic[];
  onClose: () => void;
  onUpdated: (space: Space) => void;
  onDeleted: (spaceId: string) => void;
  onDetailsChanged: () => void;
}

const permissionLabels: Array<{
  key: keyof PermissionSet;
  title: string;
  description: string;
}> = [
  {
    key: "can_send_messages",
    title: "Send messages",
    description: "Write messages in channel topics.",
  },
  {
    key: "can_send_media",
    title: "Send media",
    description: "Attach images, audio, video, and files.",
  },
  {
    key: "can_manage_topics",
    title: "Manage topics",
    description: "Create, rename, and remove channel topics.",
  },
  {
    key: "can_manage_members",
    title: "Manage members",
    description: "Invite, remove, and assign roles to members.",
  },
  {
    key: "can_delete_messages",
    title: "Moderate messages",
    description: "Delete messages written by other members.",
  },
  {
    key: "can_manage_roles",
    title: "Manage roles",
    description: "Create and update roles within permitted bounds.",
  },
  {
    key: "can_manage_space",
    title: "Manage channel",
    description: "Edit or delete the channel itself.",
  },
];

export function SpaceSettingsModal({
  space,
  currentUserId,
  members,
  topics,
  onClose,
  onUpdated,
  onDeleted,
  onDetailsChanged,
}: SpaceSettingsModalProps) {
  const { showToast } = useToast();
  const [tab, setTab] = useState<SettingsTab>("general");
  const [name, setName] = useState("");
  const [avatar, setAvatar] = useState<File | undefined>();
  const [roles, setRoles] = useState<Role[]>([]);
  const [invitees, setInvitees] = useState<User[]>([]);
  const [topicName, setTopicName] = useState("");
  const [editingTopic, setEditingTopic] = useState<Topic | null>(null);
  const [roleEditor, setRoleEditor] = useState<Role | "new" | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const permissions = useMemo(
    () => ({
      ...noPermissions,
      ...(space?.my_permissions ?? {}),
    }),
    [space],
  ) as PermissionSet;

  const canManageMembers = permissions.can_manage_members;
  const canManageSpace = permissions.can_manage_space;
  const isOwner = space?.created_by.id === currentUserId;
  const canLeave =
    space?.type === "GROUP" ||
    (space?.type === "CHANNEL" && !isOwner);

  useEffect(() => {
    if (!space) return;
    setName(space.name);
    setAvatar(undefined);
    setTab("general");
    setError(null);
    setInvitees([]);
    setTopicName("");

    if (space.type === "CHANNEL") {
      spacesApi
        .roles(space.id)
        .then((page) => setRoles(page.results))
        .catch((reason) =>
          setError(reason instanceof Error ? reason.message : "Could not load roles."),
        );
    } else {
      setRoles([]);
    }
  }, [space]);

  if (!space) return null;
  const activeSpace = space;

  const tabs: Array<{
    id: SettingsTab;
    label: string;
    icon: typeof Settings;
    show: boolean;
  }> = [
    { id: "general", label: "General", icon: Settings, show: true },
    { id: "members", label: "Members", icon: Users, show: true },
    {
      id: "topics",
      label: "Topics",
      icon: Hash,
      show: activeSpace.type === "CHANNEL",
    },
    {
      id: "roles",
      label: "Roles",
      icon: Shield,
      show: activeSpace.type === "CHANNEL",
    },
  ];

  async function saveGeneral(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const updated = await spacesApi.update(activeSpace.id, {
        name: name.trim(),
        avatar,
      });
      onUpdated(updated);
      showToast("Space settings saved.", "success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save.");
    } finally {
      setBusy(false);
    }
  }

  async function deleteSpace() {
    const label = activeSpace.type.toLowerCase();
    if (
      !window.confirm(
        `Delete this ${label} and all of its messages? This cannot be undone.`,
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await spacesApi.remove(activeSpace.id);
      onDeleted(activeSpace.id);
      showToast(`${activeSpace.display_name} deleted.`, "success");
      onClose();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not delete.");
    } finally {
      setBusy(false);
    }
  }

  async function leaveSpace() {
    if (!window.confirm(`Leave ${activeSpace.display_name}?`)) return;
    setBusy(true);
    try {
      await spacesApi.leave(activeSpace.id);
      onDeleted(activeSpace.id);
      onClose();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not leave.");
    } finally {
      setBusy(false);
    }
  }

  async function addMembers() {
    if (!invitees.length) return;
    setBusy(true);
    setError(null);
    try {
      await spacesApi.addMembers(
        activeSpace.id,
        invitees.map((user) => user.id),
      );
      setInvitees([]);
      onDetailsChanged();
      showToast("Members added.", "success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not add members.");
    } finally {
      setBusy(false);
    }
  }

  async function removeMember(member: SpaceMember) {
    if (
      !window.confirm(
        `Remove ${member.user.username} from ${activeSpace.display_name}?`,
      )
    ) {
      return;
    }
    try {
      await spacesApi.removeMember(activeSpace.id, member.user.id);
      onDetailsChanged();
      showToast("Member removed.", "success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not remove member.");
    }
  }

  async function assignRole(member: SpaceMember, roleId: string) {
    try {
      await spacesApi.updateMember(activeSpace.id, member.user.id, roleId);
      onDetailsChanged();
      showToast("Member role updated.", "success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not assign role.");
    }
  }

  async function createTopic(event: FormEvent) {
    event.preventDefault();
    if (!topicName.trim()) return;
    setBusy(true);
    try {
      await spacesApi.createTopic(activeSpace.id, topicName.trim());
      setTopicName("");
      onDetailsChanged();
      showToast("Topic created.", "success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create topic.");
    } finally {
      setBusy(false);
    }
  }

  async function updateTopic(event: FormEvent) {
    event.preventDefault();
    if (!editingTopic || !topicName.trim()) return;
    setBusy(true);
    try {
      await spacesApi.updateTopic(editingTopic.id, topicName.trim());
      setEditingTopic(null);
      setTopicName("");
      onDetailsChanged();
      showToast("Topic renamed.", "success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not rename topic.");
    } finally {
      setBusy(false);
    }
  }

  async function removeTopic(topic: Topic) {
    if (!window.confirm(`Delete #${topic.name}?`)) return;
    try {
      await spacesApi.removeTopic(topic.id);
      onDetailsChanged();
      showToast("Topic deleted.", "success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not delete topic.");
    }
  }

  async function removeRole(role: Role) {
    if (!window.confirm(`Delete the ${role.name} role?`)) return;
    try {
      await spacesApi.removeRole(role.id);
      setRoles((current) => current.filter((item) => item.id !== role.id));
      onDetailsChanged();
      showToast("Role deleted.", "success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not delete role.");
    }
  }

  return (
    <>
      <Modal
        open
        onClose={onClose}
        title={`${activeSpace.display_name} settings`}
        description={
          activeSpace.type === "GROUP"
            ? "Every group member may update or delete this group."
            : undefined
        }
        width="large"
      >
        <div className="settings-layout">
          <nav className="settings-tabs" aria-label="Space settings sections">
            {tabs
              .filter((item) => item.show)
              .map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    className={tab === item.id ? "is-active" : ""}
                    onClick={() => {
                      setTab(item.id);
                      setError(null);
                    }}
                  >
                    <Icon size={17} aria-hidden />
                    {item.label}
                  </button>
                );
              })}
          </nav>

          <section className="settings-content">
            {error ? <ErrorNotice message={error} /> : null}

            {tab === "general" ? (
              <form className="stack" onSubmit={saveGeneral}>
                <div>
                  <span className="eyebrow">Overview</span>
                  <h3>General settings</h3>
                </div>
                <Field label="Name">
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    required
                    maxLength={100}
                    disabled={!canManageSpace}
                  />
                </Field>
                {activeSpace.type !== "DIRECT" ? (
                  <Field
                    label="Space picture"
                    hint="Optional image, up to 5 MiB."
                  >
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(event) => setAvatar(event.target.files?.[0])}
                      disabled={!canManageSpace}
                    />
                  </Field>
                ) : null}
                {canManageSpace ? (
                  <div className="form-actions">
                    <Button type="submit" busy={busy}>
                      Save changes
                    </Button>
                  </div>
                ) : null}
                {canLeave || canManageSpace ? (
                  <div className="danger-zone">
                    {canLeave ? (
                      <>
                        <div>
                          <strong>
                            Leave this {activeSpace.type.toLowerCase()}
                          </strong>
                          <p>You will lose access to its messages.</p>
                        </div>
                        <Button
                          variant="secondary"
                          onClick={leaveSpace}
                          type="button"
                        >
                          Leave
                        </Button>
                      </>
                    ) : null}
                  {canManageSpace ? (
                    <>
                      <div>
                        <strong>Delete permanently</strong>
                        <p>Messages and attachments will be removed.</p>
                      </div>
                      <Button
                        variant="danger"
                        onClick={deleteSpace}
                        type="button"
                        busy={busy}
                      >
                        Delete {activeSpace.type.toLowerCase()}
                      </Button>
                    </>
                  ) : null}
                  </div>
                ) : null}
              </form>
            ) : null}

            {tab === "members" ? (
              <div className="stack">
                <div>
                  <span className="eyebrow">{members.length} people</span>
                  <h3>Members</h3>
                </div>
                {canManageMembers ? (
                  <div className="member-invite">
                    <UserSearch
                      selected={invitees}
                      onChange={setInvitees}
                      excludeIds={members.map((member) => member.user.id)}
                      label="Invite people"
                    />
                    <Button
                      onClick={addMembers}
                      disabled={!invitees.length}
                      busy={busy}
                    >
                      <Plus size={16} aria-hidden /> Add
                    </Button>
                  </div>
                ) : null}
                <ul className="management-list">
                  {members.map((member) => {
                    const isOwner =
                      member.user.id === activeSpace.created_by.id;
                    return (
                      <li key={member.user.id}>
                        <Avatar user={member.user} size="small" />
                        <span>
                          <strong>{member.user.username}</strong>
                          <small>
                            {isOwner ? "Owner" : member.role?.name ?? "Member"}
                          </small>
                        </span>
                        {activeSpace.type === "CHANNEL" &&
                        permissions.can_manage_roles &&
                        !isOwner &&
                        member.role ? (
                          <select
                            aria-label={`Role for ${member.user.username}`}
                            value={member.role.id}
                            onChange={(event) =>
                              assignRole(member, event.target.value)
                            }
                          >
                            {roles.map((role) => (
                              <option value={role.id} key={role.id}>
                                {role.name}
                              </option>
                            ))}
                          </select>
                        ) : null}
                        {canManageMembers &&
                        !isOwner &&
                        member.user.id !== currentUserId ? (
                          <IconButton
                            label={`Remove ${member.user.username}`}
                            className="icon-button--danger"
                            onClick={() => removeMember(member)}
                          >
                            <UserMinus size={16} />
                          </IconButton>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : null}

            {tab === "topics" ? (
              <div className="stack">
                <div>
                  <span className="eyebrow">Channel structure</span>
                  <h3>Topics</h3>
                </div>
                {permissions.can_manage_topics ? (
                  <form
                    className="inline-form"
                    onSubmit={editingTopic ? updateTopic : createTopic}
                  >
                    <Field label={editingTopic ? "Rename topic" : "New topic"}>
                      <input
                        value={topicName}
                        onChange={(event) => setTopicName(event.target.value)}
                        placeholder="Topic name"
                        required
                      />
                    </Field>
                    <Button type="submit" busy={busy}>
                      {editingTopic ? "Save" : "Create"}
                    </Button>
                    {editingTopic ? (
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={() => {
                          setEditingTopic(null);
                          setTopicName("");
                        }}
                      >
                        Cancel
                      </Button>
                    ) : null}
                  </form>
                ) : null}
                {!topics.length ? (
                  <EmptyState
                    title="No topics yet"
                    description="Create a topic before posting channel messages."
                  />
                ) : (
                  <ul className="management-list">
                    {topics.map((topic) => (
                      <li key={topic.id}>
                        <span className="management-list__icon">
                          <Hash size={17} />
                        </span>
                        <strong>{topic.name}</strong>
                        {permissions.can_manage_topics ? (
                          <>
                            <IconButton
                              label={`Rename ${topic.name}`}
                              onClick={() => {
                                setEditingTopic(topic);
                                setTopicName(topic.name);
                              }}
                            >
                              <Pencil size={15} />
                            </IconButton>
                            <IconButton
                              label={`Delete ${topic.name}`}
                              className="icon-button--danger"
                              onClick={() => removeTopic(topic)}
                            >
                              <Trash2 size={15} />
                            </IconButton>
                          </>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : null}

            {tab === "roles" ? (
              <div className="stack">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">Channel access</span>
                    <h3>Roles and permissions</h3>
                  </div>
                  {permissions.can_manage_roles ? (
                    <Button onClick={() => setRoleEditor("new")}>
                      <Plus size={16} aria-hidden /> New role
                    </Button>
                  ) : null}
                </div>
                {!roles.length ? (
                  <EmptyState
                    title="No custom roles"
                    description="The owner still has full access. Create roles to delegate specific tasks."
                  />
                ) : (
                  <ul className="role-list">
                    {roles.map((role) => (
                      <li key={role.id}>
                        <span className="role-list__mark">
                          <Shield size={18} />
                        </span>
                        <span>
                          <strong>{role.name}</strong>
                          <small>
                            {
                              permissionKeys.filter((key) => role[key]).length
                            }{" "}
                            permissions
                          </small>
                        </span>
                        {permissions.can_manage_roles ? (
                          <>
                            <IconButton
                              label={`Edit ${role.name}`}
                              onClick={() => setRoleEditor(role)}
                            >
                              <Pencil size={15} />
                            </IconButton>
                            {!role.is_default ? (
                              <IconButton
                                label={`Delete ${role.name}`}
                                className="icon-button--danger"
                                onClick={() => removeRole(role)}
                              >
                                <Trash2 size={15} />
                              </IconButton>
                            ) : null}
                          </>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : null}
          </section>
        </div>
      </Modal>

      <RoleEditorModal
        editor={roleEditor}
        spaceId={activeSpace.id}
        maximumPermissions={permissions}
        onClose={() => setRoleEditor(null)}
        onSaved={(role) => {
          setRoles((current) => {
            const exists = current.some((item) => item.id === role.id);
            return exists
              ? current.map((item) => (item.id === role.id ? role : item))
              : [...current, role];
          });
          setRoleEditor(null);
          onDetailsChanged();
          showToast("Role saved.", "success");
        }}
      />
    </>
  );
}

function RoleEditorModal({
  editor,
  spaceId,
  maximumPermissions,
  onClose,
  onSaved,
}: {
  editor: Role | "new" | null;
  spaceId: string;
  maximumPermissions: PermissionSet;
  onClose: () => void;
  onSaved: (role: Role) => void;
}) {
  const [name, setName] = useState("");
  const [permissions, setPermissions] = useState<PermissionSet>(noPermissions);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!editor) return;
    setName(editor === "new" ? "" : editor.name);
    setPermissions(
      editor === "new"
        ? noPermissions
        : Object.fromEntries(
            permissionKeys.map((key) => [key, editor[key]]),
          ) as unknown as PermissionSet,
    );
    setError(null);
  }, [editor]);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!editor) return;
    setBusy(true);
    setError(null);
    try {
      const role =
        editor === "new"
          ? await spacesApi.createRole(spaceId, name.trim(), permissions)
          : await spacesApi.updateRole(editor.id, {
              name: name.trim(),
              ...permissions,
            });
      onSaved(role);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save role.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={Boolean(editor)}
      onClose={onClose}
      title={editor === "new" ? "Create a role" : "Edit role"}
      description="A role cannot grant permissions that you do not have."
      width="medium"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="role-editor" busy={busy}>
            Save role
          </Button>
        </>
      }
    >
      <form id="role-editor" className="stack" onSubmit={save}>
        {error ? <ErrorNotice message={error} /> : null}
        <Field label="Role name">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            maxLength={50}
            placeholder="Moderator"
          />
        </Field>
        <fieldset className="permission-list">
          <legend>Permissions</legend>
          {permissionLabels.map((permission) => {
            const available = maximumPermissions[permission.key];
            return (
              <label key={permission.key}>
                <span>
                  <strong>{permission.title}</strong>
                  <small>{permission.description}</small>
                </span>
                <input
                  type="checkbox"
                  checked={permissions[permission.key]}
                  disabled={!available}
                  onChange={(event) =>
                    setPermissions((current) => ({
                      ...current,
                      [permission.key]: event.target.checked,
                    }))
                  }
                />
              </label>
            );
          })}
        </fieldset>
      </form>
    </Modal>
  );
}
