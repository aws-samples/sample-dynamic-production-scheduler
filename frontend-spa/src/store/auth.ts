import { create } from "zustand";
import type { AuthUser, AwsCredentials } from "@/lib/auth";
import { useStore } from "@/store";
import type { PlantId } from "@/types";
import { PLANT_DISPLAY_NAMES } from "@/types";
import {
  loadAuthConfig,
  getCurrentUser,
  getAwsCredentials,
  signIn as authSignIn,
  signUp as authSignUp,
  confirmSignUp as authConfirmSignUp,
  signOut as authSignOut,
  completeNewPassword as authCompleteNewPassword,
} from "@/lib/auth";

export type AuthView = "login" | "signup" | "confirm" | "newPassword";

interface AuthState {
  user: AuthUser | null;
  credentials: AwsCredentials | null;
  loading: boolean;
  error: string | null;
  view: AuthView;
  pendingEmail: string | null;
}

interface AuthActions {
  initialize: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  confirm: (code: string) => Promise<void>;
  forceChangePassword: (newPassword: string) => Promise<void>;
  logout: () => void;
  setView: (view: AuthView) => void;
  clearError: () => void;
  refreshCredentials: () => Promise<AwsCredentials>;
}

export const useAuthStore = create<AuthState & AuthActions>()((set, get) => ({
  user: null,
  credentials: null,
  loading: true,
  error: null,
  view: "login",
  pendingEmail: null,

  initialize: async () => {
    set({ loading: true });
    await loadAuthConfig();
    const user = await getCurrentUser();
    if (user) {
      try {
        const credentials = await getAwsCredentials();
        if (user.plant && (user.plant === "Florida" || user.plant === "Ohio")) {
          const plant = user.plant as PlantId;
          useStore.getState().setPlanner({ plant, displayName: PLANT_DISPLAY_NAMES[plant] });
        }
        set({ user, credentials, loading: false });
      } catch {
        set({ user: null, credentials: null, loading: false });
      }
    } else {
      set({ loading: false });
    }
  },

  login: async (email, password) => {
    set({ loading: true, error: null });
    try {
      const user = await authSignIn(email, password);
      const credentials = await getAwsCredentials();
      // Set planner identity from Cognito custom:plant attribute
      if (user.plant && (user.plant === "Florida" || user.plant === "Ohio")) {
        const plant = user.plant as PlantId;
        useStore.getState().setPlanner({ plant, displayName: PLANT_DISPLAY_NAMES[plant] });
      }
      set({ user, credentials, loading: false, error: null });
    } catch (err: unknown) {
      // Cognito NEW_PASSWORD_REQUIRED challenge
      if (err && typeof err === "object" && "code" in err && (err as { code: string }).code === "NewPasswordRequired") {
        set({ loading: false, error: null, view: "newPassword" });
        return;
      }
      const msg = err instanceof Error ? err.message : "Login failed";
      set({ loading: false, error: msg });
    }
  },

  signup: async (email, password) => {
    set({ loading: true, error: null });
    try {
      await authSignUp(email, password);
      set({ loading: false, view: "confirm", pendingEmail: email });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Sign up failed";
      set({ loading: false, error: msg });
    }
  },

  confirm: async (code) => {
    const { pendingEmail } = get();
    if (!pendingEmail) return;
    set({ loading: true, error: null });
    try {
      await authConfirmSignUp(pendingEmail, code);
      set({ loading: false, view: "login", error: null });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Confirmation failed";
      set({ loading: false, error: msg });
    }
  },

  forceChangePassword: async (newPassword) => {
    set({ loading: true, error: null });
    try {
      const user = await authCompleteNewPassword(newPassword);
      const credentials = await getAwsCredentials();
      if (user.plant && (user.plant === "Florida" || user.plant === "Ohio")) {
        const plant = user.plant as PlantId;
        useStore.getState().setPlanner({ plant, displayName: PLANT_DISPLAY_NAMES[plant] });
      }
      set({ user, credentials, loading: false, error: null, view: "login" });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Password change failed";
      set({ loading: false, error: msg });
    }
  },

  logout: () => {
    authSignOut();
    set({ user: null, credentials: null, view: "login" });
  },

  setView: (view) => set({ view, error: null }),

  clearError: () => set({ error: null }),

  refreshCredentials: async () => {
    const credentials = await getAwsCredentials();
    set({ credentials });
    return credentials;
  },
}));
