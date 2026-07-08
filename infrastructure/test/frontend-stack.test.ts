import * as cdk from "aws-cdk-lib";
import { Template, Match } from "aws-cdk-lib/assertions";
import { FrontendStack } from "../lib/frontend-stack";

describe("FrontendStack", () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const stack = new FrontendStack(app, "TestFrontend", {
      websocketApiUrl: "wss://test.execute-api.us-east-1.amazonaws.com/prod",
      restProxyUrl: "https://test-rest-proxy.lambda-url.us-east-1.on.aws/",
    });
    template = Template.fromStack(stack);
  });

  test("creates S3 site bucket with versioning", () => {
    template.hasResourceProperties("AWS::S3::Bucket", {
      VersioningConfiguration: { Status: "Enabled" },
    });
  });

  test("S3 bucket blocks public access", () => {
    template.hasResourceProperties("AWS::S3::Bucket", {
      PublicAccessBlockConfiguration: {
        BlockPublicAcls: true,
        BlockPublicPolicy: true,
        IgnorePublicAcls: true,
        RestrictPublicBuckets: true,
      },
    });
  });

  test("creates CloudFront distribution", () => {
    template.resourceCountIs("AWS::CloudFront::Distribution", 1);
  });

  test("CloudFront has HTTPS redirect", () => {
    template.hasResourceProperties("AWS::CloudFront::Distribution", {
      DistributionConfig: {
        DefaultCacheBehavior: {
          ViewerProtocolPolicy: "redirect-to-https",
        },
      },
    });
  });

  test("creates response headers policy with security headers", () => {
    template.hasResourceProperties(
      "AWS::CloudFront::ResponseHeadersPolicy",
      {
        ResponseHeadersPolicyConfig: {
          SecurityHeadersConfig: {
            StrictTransportSecurity: {
              AccessControlMaxAgeSec: 31536000,
              IncludeSubdomains: true,
              Override: true,
            },
            ContentTypeOptions: { Override: true },
            FrameOptions: {
              FrameOption: "DENY",
              Override: true,
            },
            ReferrerPolicy: {
              ReferrerPolicy: "strict-origin-when-cross-origin",
              Override: true,
            },
          },
        },
      }
    );
  });

  test("CloudFront has SPA error responses", () => {
    template.hasResourceProperties("AWS::CloudFront::Distribution", {
      DistributionConfig: {
        CustomErrorResponses: Match.arrayWith([
          Match.objectLike({
            ErrorCode: 403,
            ResponseCode: 200,
            ResponsePagePath: "/index.html",
          }),
          Match.objectLike({
            ErrorCode: 404,
            ResponseCode: 200,
            ResponsePagePath: "/index.html",
          }),
        ]),
      },
    });
  });

  test("creates access log bucket with lifecycle", () => {
    template.hasResourceProperties("AWS::S3::Bucket", {
      LifecycleConfiguration: {
        Rules: Match.arrayWith([
          Match.objectLike({
            ExpirationInDays: 90,
            Status: "Enabled",
          }),
        ]),
      },
    });
  });

  test("exports distribution URL and bucket name", () => {
    template.hasOutput("DistributionUrl", {});
    template.hasOutput("SiteBucketName", {});
    template.hasOutput("DistributionId", {});
  });
});
