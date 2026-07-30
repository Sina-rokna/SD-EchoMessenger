import { type FormEvent, useState } from "react";
import { Eye, EyeOff, MessageSquareText } from "lucide-react";

import { Button, ErrorNotice, Field } from "../../components/ui";
import { useAuth } from "./AuthContext";

type Mode = "login" | "register";

export function AuthScreen() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (mode === "register" && password !== confirmPassword) {
      setError("The two passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Your password must contain at least 8 characters.");
      return;
    }

    setSubmitting(true);
    try {
      if (mode === "login") await login(email.trim(), password);
      else await register(username.trim(), email.trim(), password);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Authentication failed.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  function switchMode(nextMode: Mode) {
    setMode(nextMode);
    setError(null);
    setPassword("");
    setConfirmPassword("");
  }

  return (
    <main className="auth-page">
      <section className="auth-intro" aria-labelledby="welcome-title">
        <div className="brand brand--large">
          <span className="brand__mark">
            <MessageSquareText size={26} />
          </span>
          <span>EchoMessenger</span>
        </div>
        <div>
          <span className="eyebrow">Clear conversations, fewer distractions</span>
          <h1 id="welcome-title">A calm place for your team to stay in sync.</h1>
          <p>
            Direct messages, focused groups, organized channels, and the details
            you need—all in one readable workspace.
          </p>
        </div>
        <div className="auth-intro__sample" aria-hidden>
          <span className="sample-avatar">NS</span>
          <div>
            <strong>Nima</strong>
            <p>The updated plan is ready in #general.</p>
          </div>
          <span className="sample-time">now</span>
        </div>
      </section>

      <section className="auth-card" aria-labelledby="auth-title">
        <div className="auth-card__mobile-brand">
          <MessageSquareText size={23} />
          EchoMessenger
        </div>
        <header>
          <span className="eyebrow">{mode === "login" ? "Welcome back" : "Join us"}</span>
          <h2 id="auth-title">
            {mode === "login" ? "Log in to continue" : "Create your account"}
          </h2>
          <p>
            {mode === "login"
              ? "Use the email connected to your account."
              : "You can update your profile after signing up."}
          </p>
        </header>

        {error ? <ErrorNotice message={error} /> : null}

        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === "register" ? (
            <Field label="Username">
              <input
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
                minLength={2}
                maxLength={50}
                autoFocus
              />
            </Field>
          ) : null}

          <Field label="Email address">
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              autoFocus={mode === "login"}
            />
          </Field>

          <Field
            label="Password"
            controlId="auth-password"
            hint={mode === "register" ? "Use at least 8 characters." : undefined}
          >
            <span className="password-input">
              <input
                id="auth-password"
                type={showPassword ? "text" : "password"}
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={8}
              />
              <button
                type="button"
                onClick={() => setShowPassword((shown) => !shown)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </span>
          </Field>

          {mode === "register" ? (
            <Field label="Confirm password">
              <input
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
                minLength={8}
              />
            </Field>
          ) : null}

          <Button type="submit" busy={submitting} className="auth-form__submit">
            {mode === "login" ? "Log in" : "Create account"}
          </Button>
        </form>

        <p className="auth-switch">
          {mode === "login" ? "New to EchoMessenger?" : "Already have an account?"}
          <button
            type="button"
            onClick={() => switchMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "Create an account" : "Log in"}
          </button>
        </p>
      </section>
    </main>
  );
}
