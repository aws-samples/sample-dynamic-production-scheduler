import * as cdk from "aws-cdk-lib";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as kms from "aws-cdk-lib/aws-kms";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import { Construct } from "constructs";

export interface FrontendStackProps extends cdk.StackProps {
  websocketApiUrl: string;
  restProxyUrl: string;
  dashboardApiUrl?: string;
}

export class FrontendStack extends cdk.Stack {
  public readonly distributionDomainName: string;

  constructor(scope: Construct, id: string, props: FrontendStackProps) {
    super(scope, id, props);

    // Access log bucket for CloudFront (SECURITY-02)
    // Note: CloudFront access logging requires S3_MANAGED encryption (SSE-S3).
    // KMS encryption is not supported for CloudFront log delivery.
    const logBucket = new s3.Bucket(this, "AccessLogBucket", {
      bucketName: `disruptionai-frontend-logs-${this.account}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      objectOwnership: s3.ObjectOwnership.OBJECT_WRITER,
      lifecycleRules: [{ expiration: cdk.Duration.days(90) }],
      serverAccessLogsPrefix: "access-logs/",
    });

    // KMS key for site bucket encryption
    const siteBucketKey = new kms.Key(this, "SiteBucketKey", {
      alias: "disruptionai-frontend-site",
      description: "KMS key for DisruptionAI frontend site bucket",
      enableKeyRotation: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // SPA hosting bucket (SECURITY-01, SECURITY-09)
    const siteBucket = new s3.Bucket(this, "SiteBucket", {
      bucketName: `disruptionai-frontend-${this.account}`,
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: siteBucketKey,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: true,
      serverAccessLogsBucket: logBucket,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // Response headers policy (SECURITY-04)
    const responseHeadersPolicy = new cloudfront.ResponseHeadersPolicy(
      this,
      "SecurityHeaders",
      {
        responseHeadersPolicyName: "disruptionai-security-headers",
        securityHeadersBehavior: {
          contentSecurityPolicy: {
            contentSecurityPolicy: [
              "default-src 'self'",
              `connect-src 'self' ${props.websocketApiUrl} ${props.restProxyUrl} ${props.dashboardApiUrl ?? ""} https://cognito-idp.us-east-1.amazonaws.com https://cognito-identity.us-east-1.amazonaws.com`,
              // style-src controls <style> elements and external stylesheets — locked
              // to 'self' + Google Fonts (no 'unsafe-inline'). Tailwind compiles to a
              // static stylesheet and Google Fonts loads via <link>, so neither needs inline.
              "style-src 'self' https://fonts.googleapis.com",
              // style-src-attr scopes 'unsafe-inline' to inline style ATTRIBUTES only
              // (required by Recharts, which sets dynamic style="" on chart elements).
              // Caveat: Firefox does not yet support style-src-attr and falls back to
              // style-src for inline attributes; if Recharts rendering regresses in
              // Firefox, add 'unsafe-inline' back to style-src.
              "style-src-attr 'unsafe-inline'",
              "img-src 'self' data:",
              "font-src 'self' https://fonts.gstatic.com",
            ].join("; "),
            override: true,
          },
          strictTransportSecurity: {
            accessControlMaxAge: cdk.Duration.days(365),
            includeSubdomains: true,
            override: true,
          },
          contentTypeOptions: { override: true },
          frameOptions: {
            frameOption: cloudfront.HeadersFrameOption.DENY,
            override: true,
          },
          referrerPolicy: {
            referrerPolicy:
              cloudfront.HeadersReferrerPolicy
                .STRICT_ORIGIN_WHEN_CROSS_ORIGIN,
            override: true,
          },
        },
      }
    );

    // CloudFront distribution
    const oai = new cloudfront.OriginAccessIdentity(this, "OAI");
    siteBucket.grantRead(oai);

    const distribution = new cloudfront.Distribution(this, "Distribution", {
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessIdentity(siteBucket, {
          originAccessIdentity: oai,
        }),
        viewerProtocolPolicy:
          cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        responseHeadersPolicy,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      defaultRootObject: "index.html",
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
      enableLogging: true,
      logBucket,
      errorResponses: [
        {
          httpStatus: 403,
          responseHttpStatus: 200,
          responsePagePath: "/index.html",
          ttl: cdk.Duration.seconds(0),
        },
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: "/index.html",
          ttl: cdk.Duration.seconds(0),
        },
      ],
    });

    this.distributionDomainName = distribution.distributionDomainName;

    new cdk.CfnOutput(this, "DistributionUrl", {
      value: `https://${distribution.distributionDomainName}`,
      exportName: "disruptionai-frontend-url",
    });

    new cdk.CfnOutput(this, "SiteBucketName", {
      value: siteBucket.bucketName,
      exportName: "disruptionai-frontend-bucket",
    });

    new cdk.CfnOutput(this, "DistributionId", {
      value: distribution.distributionId,
      exportName: "disruptionai-distribution-id",
    });
  }
}
