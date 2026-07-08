import * as cdk from "aws-cdk-lib";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as iam from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";

export class CognitoStack extends cdk.Stack {
  public readonly userPoolId: string;
  public readonly appClientId: string;
  public readonly tokenEndpoint: string;
  public readonly userPoolArn: string;
  // User login resources
  public readonly userAppClientId: string;
  public readonly identityPoolId: string;
  public readonly authenticatedRoleArn: string;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Cognito User Pool for gateway JWT authentication (SECURITY-08)
    // NOTE: signInAliases cannot be changed on an existing pool
    // (CloudFormation immutable property). The pool was originally
    // created without signInAliases, so users sign in with their
    // email address used as the "username" field.
    // Self-registration is disabled — admins create users manually.
    const userPool = new cognito.UserPool(this, "GatewayUserPool", {
      userPoolName: "disruptionai-gateway-pool",
      selfSignUpEnabled: false,
      autoVerify: { email: true },
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      customAttributes: {
        plant: new cognito.StringAttribute({ mutable: true }),
      },
    });

    this.userPoolId = userPool.userPoolId;
    this.userPoolArn = userPool.userPoolArn;

    // Resource Server with custom scopes for MCP access control
    const resourceServer = new cognito.UserPoolResourceServer(
      this,
      "GatewayResourceServer",
      {
        userPool,
        identifier: "disruptionai-gateway",
        scopes: [
          new cognito.ResourceServerScope({
            scopeName: "erp-data",
            scopeDescription: "ERP data MCP access",
          }),
          new cognito.ResourceServerScope({
            scopeName: "audit",
            scopeDescription: "Audit MCP access",
          }),
        ],
      }
    );

    // App Client with client_credentials grant (SECURITY-12: secret managed by Cognito)
    const appClient = userPool.addClient("GatewayAppClient", {
      userPoolClientName: "disruptionai-gateway-client",
      generateSecret: true,
      oAuth: {
        flows: { clientCredentials: true },
        scopes: [
          cognito.OAuthScope.custom("disruptionai-gateway/erp-data"),
          cognito.OAuthScope.custom("disruptionai-gateway/audit"),
        ],
      },
    });

    // Ensure resource server is created before the app client references its scopes
    appClient.node.addDependency(resourceServer);

    this.appClientId = appClient.userPoolClientId;

    // Domain for the token endpoint
    const domain = userPool.addDomain("GatewayDomain", {
      cognitoDomain: {
        domainPrefix: `disruptionai-gateway-${cdk.Aws.ACCOUNT_ID}`,
      },
    });

    this.tokenEndpoint = `https://${domain.domainName}.auth.${cdk.Aws.REGION}.amazoncognito.com/oauth2/token`;

    // Outputs
    new cdk.CfnOutput(this, "UserPoolId", {
      value: userPool.userPoolId,
      exportName: "disruptionai-cognito-user-pool-id",
    });

    new cdk.CfnOutput(this, "AppClientId", {
      value: appClient.userPoolClientId,
      exportName: "disruptionai-cognito-app-client-id",
    });

    new cdk.CfnOutput(this, "TokenEndpoint", {
      value: this.tokenEndpoint,
      exportName: "disruptionai-cognito-token-endpoint",
    });

    new cdk.CfnOutput(this, "UserPoolArn", {
      value: userPool.userPoolArn,
      exportName: "disruptionai-cognito-user-pool-arn",
    });

    // ---------------------------------------------------------------
    // User-facing app client (SRP auth for frontend login)
    // ---------------------------------------------------------------
    const userAppClient = userPool.addClient("UserAppClient", {
      userPoolClientName: "disruptionai-user-client",
      generateSecret: false, // SPA cannot hold secrets
      authFlows: {
        userSrp: true,
        userPassword: true, // Enable USER_PASSWORD_AUTH for sign-up
      },
      preventUserExistenceErrors: true,
      enableTokenRevocation: true,
    });

    this.userAppClientId = userAppClient.userPoolClientId;

    // ---------------------------------------------------------------
    // Cognito Identity Pool — federate user pool for AWS_IAM creds
    // ---------------------------------------------------------------
    const identityPool = new cognito.CfnIdentityPool(
      this,
      "IdentityPool",
      {
        identityPoolName: "disruptionai_identity_pool",
        allowUnauthenticatedIdentities: false,
        cognitoIdentityProviders: [
          {
            clientId: userAppClient.userPoolClientId,
            providerName: userPool.userPoolProviderName,
          },
        ],
      }
    );

    this.identityPoolId = identityPool.ref;

    // Authenticated role — will be granted lambda:InvokeFunctionUrl
    const authenticatedRole = new iam.Role(this, "CognitoAuthRole", {
      roleName: "disruptionai-cognito-auth-role",
      assumedBy: new iam.FederatedPrincipal(
        "cognito-identity.amazonaws.com",
        {
          StringEquals: {
            "cognito-identity.amazonaws.com:aud": identityPool.ref,
          },
          "ForAnyValue:StringLike": {
            "cognito-identity.amazonaws.com:amr": "authenticated",
          },
        },
        "sts:AssumeRoleWithWebIdentity"
      ),
    });

    this.authenticatedRoleArn = authenticatedRole.roleArn;

    // Attach role to identity pool
    new cognito.CfnIdentityPoolRoleAttachment(
      this,
      "IdentityPoolRoles",
      {
        identityPoolId: identityPool.ref,
        roles: {
          authenticated: authenticatedRole.roleArn,
        },
      }
    );

    // Outputs for frontend config
    new cdk.CfnOutput(this, "UserAppClientId", {
      value: userAppClient.userPoolClientId,
      exportName: "disruptionai-cognito-user-client-id",
    });

    new cdk.CfnOutput(this, "IdentityPoolId", {
      value: identityPool.ref,
      exportName: "disruptionai-cognito-identity-pool-id",
    });
  }
}
