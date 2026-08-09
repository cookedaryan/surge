# Authentication and Authorization Architecture

> [!warning] Implementation status: Planned
> The repository does not currently include Spring Security, JWT handling, password storage, user entities, or role checks. All application endpoints are presently unauthenticated.

## Concepts

**Authentication** proves who a caller is. **Authorization** decides what that authenticated caller may do. A valid token is not sufficient authorization by itself; every protected operation must also check access to the requested project or administrative action.

**JWT (JSON Web Token)** is a signed token containing identity claims. The server verifies the signature and expiry rather than storing an HTTP session. JWT does not encrypt its contents, so secrets and sensitive personal data must not be placed in claims.

**RBAC (role-based access control)** grants permissions through roles. The proposed initial roles are:

- `ADMIN`: manage users and all projects.
- `PLANNING_ENGINEER`: create and modify authorized projects, assets, jobs, and reports.
- `VIEWER`: read authorized projects and results without mutation rights.

## Proposed Request Flow

1. A user authenticates with the Java backend.
2. The backend verifies the stored BCrypt password hash and issues a short-lived signed access token.
3. The browser sends the token in the `Authorization: Bearer` header.
4. A Spring Security filter validates signature, issuer, audience, and expiry.
5. Controller/service authorization checks both role and project membership.
6. Java calls Python as an internal service. Python trusts only the authenticated Java service boundary, not browser-provided authorization claims.

## Why Security Belongs in Java

Java already owns project persistence and public APIs, so it has the information required to enforce project-level permissions. Keeping identity out of the Python optimization engine preserves its stateless numerical role and avoids duplicating security policy across services.

## Required Work Before This Is Implemented

- Add user, role, and project-membership persistence.
- Add Spring Security and a reviewed JWT library/configuration.
- Define login, refresh, logout/revocation, and password-reset behavior.
- Add service-level authorization tests, not only controller authentication tests.
- Restrict CORS origins and protect the Java-to-Python network boundary.
- Document token lifetimes, signing-key rotation, and secret management.

## Related Notes

- [[Backend]]
- [[System Overview]]
