import { type FormEvent, useEffect, useState } from "react";
import { Hash, MessageCircle, Users } from "lucide-react";

import { spacesApi } from "../../api/endpoints";
import type { Space, SpaceType, User } from "../../api/types";
import { Button, ErrorNotice, Field, Modal } from "../../components/ui";
import { useToast } from "../../components/ToastProvider";
import { useAuth } from "../auth/AuthContext";
import { UserSearch } from "./UserSearch";

interface CreateSpaceModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (space: Space) => void;
}

const options: Array<{
  type: SpaceType;
  title: string;
  description: string;
  icon: typeof MessageCircle;
}> = [
  {
    type: "DIRECT",
    title: "Direct message",
    description: "Start a private conversation with one person.",
    icon: MessageCircle,
  },
  {
    type: "GROUP",
    title: "Private group",
    description: "Bring a few people into one simple conversation.",
    icon: Users,
  },
  {
    type: "CHANNEL",
    title: "Channel",
    description: "Organize a larger space with topics and roles.",
    icon: Hash,
  },
];

export function CreateSpaceModal({
  open,
  onClose,
  onCreated,
}: CreateSpaceModalProps) {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [type, setType] = useState<SpaceType>("DIRECT");
  const [name, setName] = useState("");
  const [people, setPeople] = useState<User[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setType("DIRECT");
      setName("");
      setPeople([]);
      setError(null);
    }
  }, [open]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (!people.length && type !== "CHANNEL") {
      setError(
        type === "DIRECT"
          ? "Choose the person you want to message."
          : "Choose at least one person for the group.",
      );
      return;
    }

    setSubmitting(true);
    try {
      const space =
        type === "DIRECT"
          ? await spacesApi.direct(people[0].id)
          : await spacesApi.create({
              type,
              name: name.trim(),
              member_ids: people.map((person) => person.id),
            });
      onCreated(space);
      showToast(
        type === "DIRECT"
          ? "Conversation opened."
          : `${space.display_name} created.`,
        "success",
      );
      onClose();
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Could not create the space.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const selectedOption = options.find((option) => option.type === type)!;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Start a conversation"
      description="Choose the smallest space that fits the conversation."
      width="medium"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button form="create-space-form" type="submit" busy={submitting}>
            {type === "DIRECT" ? "Open message" : `Create ${type.toLowerCase()}`}
          </Button>
        </>
      }
    >
      <form
        id="create-space-form"
        className="create-space"
        onSubmit={handleSubmit}
      >
        {error ? <ErrorNotice message={error} /> : null}

        <div className="choice-grid" role="radiogroup" aria-label="Space type">
          {options.map((option) => {
            const Icon = option.icon;
            return (
              <button
                type="button"
                className={type === option.type ? "is-selected" : ""}
                role="radio"
                aria-checked={type === option.type}
                key={option.type}
                onClick={() => {
                  setType(option.type);
                  setPeople((current) =>
                    option.type === "DIRECT" ? current.slice(0, 1) : current,
                  );
                  setError(null);
                }}
              >
                <span>
                  <Icon size={19} aria-hidden />
                </span>
                <strong>{option.title}</strong>
                <small>{option.description}</small>
              </button>
            );
          })}
        </div>

        {type !== "DIRECT" ? (
          <Field
            label={`${selectedOption.title} name`}
            hint="Keep it short and recognizable."
          >
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              minLength={2}
              maxLength={100}
              placeholder={type === "CHANNEL" ? "Product team" : "Weekend plan"}
            />
          </Field>
        ) : null}

        <UserSearch
          selected={people}
          onChange={setPeople}
          excludeIds={user ? [user.id] : []}
          single={type === "DIRECT"}
          label={
            type === "DIRECT"
              ? "Who do you want to message?"
              : "Add people now (you can add more later)"
          }
        />
      </form>
    </Modal>
  );
}
