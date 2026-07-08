import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserSession,
  CognitoUserAttribute,
} from "amazon-cognito-identity-js";
import { logger } from "@/lib/logger";

// Runtime config loaded from /config.json or build-time env vars
let USER_POOL_ID = import.meta.env.VITE_USER_POOL_ID as string | undefined;
let USER_CLIENT_ID = import.meta.env.VITE_USER_CLIENT_ID as string | undefined;
let IDENTITY_POOL_ID = import.meta.env.VITE_IDENTITY_POOL_ID as string | undefined;
let REGION = import.meta.env.VITE_AWS_REGION as string | undefined ?? "us-east-1";

let userPool: CognitoUserPool | null = null;

export interface AuthUser {
  email: string;
  sub: string;
  plant?: string;
}

export interface AwsCredentials {
  accessKeyId: string;
  secretAccessKey: string;
  sessionToken: string;
}

export async function loadAuthConfig(): Promise<void> {
  if (USER_POOL_ID && USER_CLIENT_ID && IDENTITY_POOL_ID) return;
  try {
    const resp = await fetch("/config.json");
    if (resp.ok) {
      const config = await resp.json();
      USER_POOL_ID = config.VITE_USER_POOL_ID ?? USER_POOL_ID;
      USER_CLIENT_ID = config.VITE_USER_CLIENT_ID ?? USER_CLIENT_ID;
      IDENTITY_POOL_ID = config.VITE_IDENTITY_POOL_ID ?? IDENTITY_POOL_ID;
      REGION = config.VITE_AWS_REGION ?? REGION;
    }
  } catch {
    // config.json not found — fine for local dev
  }
}

function getPool(): CognitoUserPool {
  if (!userPool) {
    if (!USER_POOL_ID || !USER_CLIENT_ID) {
      throw new Error("Cognito not configured");
    }
    userPool = new CognitoUserPool({
      UserPoolId: USER_POOL_ID,
      ClientId: USER_CLIENT_ID,
    });
  }
  return userPool;
}

/**
 * Holds the CognitoUser that triggered a NEW_PASSWORD_REQUIRED challenge.
 * Must be the same instance to preserve the internal session state.
 */
let pendingNewPasswordUser: CognitoUser | null = null;

/** Sign in with email + password. Returns the authenticated user. */
export function signIn(email: string, password: string): Promise<AuthUser> {
  return new Promise((resolve, reject) => {
    const pool = getPool();
    const cognitoUser = new CognitoUser({ Username: email, Pool: pool });
    const authDetails = new AuthenticationDetails({
      Username: email,
      Password: password,
    });

    cognitoUser.authenticateUser(authDetails, {
      onSuccess: (session: CognitoUserSession) => {
        pendingNewPasswordUser = null;
        const payload = session.getIdToken().decodePayload();
        logger.info("Auth", "Signed in successfully");
        resolve({
          email: payload["email"] as string,
          sub: payload["sub"] as string,
          plant: (payload["custom:plant"] as string) || undefined,
        });
      },
      onFailure: (err: Error) => {
        pendingNewPasswordUser = null;
        logger.error("Auth", `Sign in failed: ${err.message}`);
        reject(err);
      },
      newPasswordRequired: (_userAttributes: Record<string, string>) => {
        // Store the same CognitoUser instance so completeNewPassword can use it
        pendingNewPasswordUser = cognitoUser;
        logger.info("Auth", "New password required for user");
        reject(
          Object.assign(new Error("New password required"), {
            code: "NewPasswordRequired",
          })
        );
      },
    });
  });
}

/** Complete the NEW_PASSWORD_REQUIRED challenge with a new password. */
export function completeNewPassword(newPassword: string): Promise<AuthUser> {
  return new Promise((resolve, reject) => {
    if (!pendingNewPasswordUser) {
      reject(new Error("No pending new-password challenge"));
      return;
    }
    const cognitoUser = pendingNewPasswordUser;

    cognitoUser.completeNewPasswordChallenge(newPassword, {}, {
      onSuccess: (session: CognitoUserSession) => {
        pendingNewPasswordUser = null;
        const payload = session.getIdToken().decodePayload();
        logger.info("Auth", "Password changed and signed in successfully");
        resolve({
          email: payload["email"] as string,
          sub: payload["sub"] as string,
          plant: (payload["custom:plant"] as string) || undefined,
        });
      },
      onFailure: (err: Error) => {
        logger.error("Auth", `New password challenge failed: ${err.message}`);
        reject(err);
      },
    });
  });
}

/** Sign up a new user with email + password. */
export function signUp(email: string, password: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const pool = getPool();
    const attrs = [
      new CognitoUserAttribute({ Name: "email", Value: email }),
    ];
    pool.signUp(email, password, attrs, [], (err) => {
      if (err) {
        logger.error("Auth", `Sign up failed: ${err.message}`);
        reject(err);
        return;
      }
      resolve();
    });
  });
}

/** Confirm sign up with verification code. */
export function confirmSignUp(email: string, code: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const pool = getPool();
    const cognitoUser = new CognitoUser({ Username: email, Pool: pool });
    cognitoUser.confirmRegistration(code, true, (err) => {
      if (err) {
        logger.error("Auth", `Confirm failed: ${err.message}`);
        reject(err);
        return;
      }
      resolve();
    });
  });
}

/** Get the current session (if user is already logged in via stored tokens). */
export function getCurrentSession(): Promise<CognitoUserSession | null> {
  return new Promise((resolve) => {
    try {
      const pool = getPool();
      const user = pool.getCurrentUser();
      if (!user) {
        resolve(null);
        return;
      }
      user.getSession((err: Error | null, session: CognitoUserSession | null) => {
        if (err || !session || !session.isValid()) {
          resolve(null);
          return;
        }
        resolve(session);
      });
    } catch {
      resolve(null);
    }
  });
}

/** Get the current authenticated user, or null. */
export async function getCurrentUser(): Promise<AuthUser | null> {
  const session = await getCurrentSession();
  if (!session) return null;
  const payload = session.getIdToken().decodePayload();
  return {
    email: payload["email"] as string,
    sub: payload["sub"] as string,
    plant: (payload["custom:plant"] as string) || undefined,
  };
}

/** Sign out the current user. */
export function signOut(): void {
  try {
    const pool = getPool();
    const user = pool.getCurrentUser();
    if (user) user.signOut();
    logger.info("Auth", "Signed out");
  } catch {
    // ignore
  }
}

/**
 * Get temporary AWS credentials via Cognito Identity Pool.
 * These credentials can be used for SigV4 signing.
 */
export async function getAwsCredentials(): Promise<AwsCredentials> {
  const session = await getCurrentSession();
  if (!session) throw new Error("Not authenticated");

  if (!IDENTITY_POOL_ID) throw new Error("Identity Pool not configured");

  const idToken = session.getIdToken().getJwtToken();
  const providerName = `cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}`;

  // Get Identity ID
  const getIdResp = await fetch(
    `https://cognito-identity.${REGION}.amazonaws.com/`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": "AWSCognitoIdentityService.GetId",
      },
      body: JSON.stringify({
        IdentityPoolId: IDENTITY_POOL_ID,
        Logins: { [providerName]: idToken },
      }),
    }
  );
  const getIdBody = await getIdResp.json();
  const { IdentityId } = getIdBody;

  // Get credentials for identity
  const getCredsResp = await fetch(
    `https://cognito-identity.${REGION}.amazonaws.com/`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target":
          "AWSCognitoIdentityService.GetCredentialsForIdentity",
      },
      body: JSON.stringify({
        IdentityId,
        Logins: { [providerName]: idToken },
      }),
    }
  );
  const getCredsBody = await getCredsResp.json();
  const { Credentials } = getCredsBody;

  return {
    accessKeyId: Credentials.AccessKeyId,
    secretAccessKey: Credentials.SecretKey,
    sessionToken: Credentials.SessionToken,
  };
}

/** Get the AWS region. */
export function getRegion(): string {
  return REGION ?? "us-east-1";
}
