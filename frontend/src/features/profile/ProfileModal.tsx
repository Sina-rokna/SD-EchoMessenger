import { type FormEvent, useEffect, useMemo, useState } from "react";
import { Camera, Mail, ShieldCheck } from "lucide-react";

import { usersApi } from "../../api/endpoints";
import type { InvitePolicy, User } from "../../api/types";
import {
  Avatar,
  Button,
  ErrorNotice,
  Field,
  LoadingState,
  Modal,
} from "../../components/ui";
import { useToast } from "../../components/ToastProvider";
import { useAuth } from "../auth/AuthContext";

interface ProfileModalProps {
  userId: string | null;
  onClose: () => void;
}

export function ProfileModal({ userId, onClose }: ProfileModalProps) {
  const { user: currentUser, updateUser } = useAuth();
  const { showToast } = useToast();
  const [profile, setProfile] = useState<User | null>(null);
  const [username, setUsername] = useState("");
  const [bio, setBio] = useState("");
  const [invitePolicy, setInvitePolicy] =
    useState<InvitePolicy>("EVERYONE");
  const [avatar, setAvatar] = useState<File | undefined>();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isOwnProfile = userId === currentUser?.id;
  const previewUrl = useMemo(
    () => (avatar ? URL.createObjectURL(avatar) : null),
    [avatar],
  );

  useEffect(
    () => () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    },
    [previewUrl],
  );

  useEffect(() => {
    if (!userId) return;
    let active = true;
    setLoading(true);
    setError(null);

    const request =
      userId === currentUser?.id && currentUser
        ? Promise.resolve(currentUser)
        : usersApi.get(userId);

    request
      .then((nextProfile) => {
        if (!active) return;
        setProfile(nextProfile);
        setUsername(nextProfile.username);
        setBio(nextProfile.bio ?? "");
        setInvitePolicy(nextProfile.group_invite_policy ?? "EVERYONE");
        setAvatar(undefined);
      })
      .catch((reason) => {
        if (active) {
          setError(
            reason instanceof Error ? reason.message : "Could not load profile.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [currentUser, userId]);

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    if (!isOwnProfile) return;
    setSaving(true);
    setError(null);

    try {
      const updated = await usersApi.updateMe({
        username: username.trim(),
        bio: bio.trim(),
        group_invite_policy: invitePolicy,
        avatar,
      });
      setProfile(updated);
      updateUser(updated);
      showToast("Profile updated.", "success");
      onClose();
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Could not update profile.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={Boolean(userId)}
      onClose={onClose}
      title={isOwnProfile ? "Your profile" : "Member profile"}
      description={
        isOwnProfile
          ? "Choose what other EchoMessenger members can see."
          : undefined
      }
      width="small"
      footer={
        isOwnProfile ? (
          <>
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button form="profile-form" type="submit" busy={saving}>
              Save changes
            </Button>
          </>
        ) : (
          <Button onClick={onClose}>Done</Button>
        )
      }
    >
      {loading ? <LoadingState label="Loading profile" /> : null}
      {error ? <ErrorNotice message={error} /> : null}

      {!loading && profile ? (
        <form id="profile-form" className="profile" onSubmit={handleSave}>
          <div className="profile__identity">
            <div className="profile__avatar">
              <Avatar
                name={profile.username}
                src={previewUrl ?? profile.avatar_url}
                size="hero"
              />
              {isOwnProfile ? (
                <label className="profile__avatar-button">
                  <Camera size={16} aria-hidden />
                  <span className="sr-only">Choose a new avatar</span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(event) => setAvatar(event.target.files?.[0])}
                  />
                </label>
              ) : null}
            </div>
            {!isOwnProfile ? (
              <div>
                <h3>{profile.username}</h3>
                {profile.email ? (
                  <p>
                    <Mail size={15} aria-hidden /> {profile.email}
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>

          {isOwnProfile ? (
            <>
              <Field label="Username">
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  maxLength={50}
                  required
                />
              </Field>
              <Field
                label="Biography"
                hint={`${bio.length}/280 characters`}
              >
                <textarea
                  rows={4}
                  value={bio}
                  onChange={(event) => setBio(event.target.value)}
                  maxLength={280}
                  placeholder="A little about you..."
                />
              </Field>
              <Field
                label="Group invitations"
                hint="This is checked whenever someone tries to add you to a group."
              >
                <select
                  value={invitePolicy}
                  onChange={(event) =>
                    setInvitePolicy(event.target.value as InvitePolicy)
                  }
                >
                  <option value="EVERYONE">Allow group invitations</option>
                  <option value="NOBODY">Do not allow group invitations</option>
                </select>
              </Field>
            </>
          ) : (
            <div className="profile__about">
              <span className="eyebrow">About</span>
              <p>{profile.bio?.trim() || "This member has not added a bio yet."}</p>
              <span className="profile__privacy">
                <ShieldCheck size={15} aria-hidden /> Profile information
              </span>
            </div>
          )}
        </form>
      ) : null}
    </Modal>
  );
}
