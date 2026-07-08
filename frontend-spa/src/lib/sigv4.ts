import { AwsClient } from "aws4fetch";
import type { AwsCredentials } from "@/lib/auth";
import { getRegion } from "@/lib/auth";

/**
 * Sign a fetch request with SigV4 for AWS_IAM-authenticated Lambda Function URLs.
 *
 * Uses aws4fetch's AwsClient.fetch() which handles body hashing
 * (x-amz-content-sha256), session tokens, and all SigV4 requirements
 * correctly in the browser via the native SubtleCrypto API.
 */
export async function signedFetch(
  url: string,
  init: RequestInit,
  credentials: AwsCredentials
): Promise<Response> {
  const region = getRegion();

  const client = new AwsClient({
    accessKeyId: credentials.accessKeyId,
    secretAccessKey: credentials.secretAccessKey,
    sessionToken: credentials.sessionToken,
    service: "lambda",
    region,
    retries: 0,
  });

  // Use client.fetch() directly — it signs AND sends in one step,
  // ensuring x-amz-content-sha256 and all SigV4 headers are included.
  return client.fetch(url, {
    method: init.method ?? "POST",
    headers: { "content-type": "application/json" },
    body: init.body,
    signal: init.signal,
  });
}
