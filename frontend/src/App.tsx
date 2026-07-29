import { MessageSquareText } from "lucide-react";

import { ErrorNotice, LoadingState } from "./components/ui";
import { ToastProvider } from "./components/ToastProvider";
import { AuthScreen } from "./features/auth/AuthScreen";
import { useAuth } from "./features/auth/AuthContext";
import { MessengerPage } from "./features/shell/MessengerPage";

export function App() {
  const { user, loading, error, retry } = useAuth();

  if (loading) {
    return (
      <main className="splash">
        <span className="brand__mark brand__mark--pulse">
          <MessageSquareText size={28} />
        </span>
        <LoadingState label="Opening EchoMessenger" />
      </main>
    );
  }

  if (error && !user) {
    return (
      <main className="splash">
        <span className="brand brand--large">
          <span className="brand__mark">
            <MessageSquareText size={25} />
          </span>
          EchoMessenger
        </span>
        <ErrorNotice message={error} onRetry={retry} />
      </main>
    );
  }

  return (
    <ToastProvider>{user ? <MessengerPage /> : <AuthScreen />}</ToastProvider>
  );
}
