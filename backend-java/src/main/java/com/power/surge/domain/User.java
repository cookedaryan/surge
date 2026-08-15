package com.power.surge.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    private UUID id;

    @Column(name = "username", nullable = false, unique = true, length = 64)
    private String username;

    @Column(name = "email", nullable = false, unique = true, length = 128)
    private String email;

    @Column(name = "password_hash", nullable = false, length = 255)
    private String passwordHash;

    @Enumerated(EnumType.STRING)
    @Column(name = "role", nullable = false, length = 32)
    private UserRole role;

    /**
     * A suspended account keeps its history and its name resolvable in the audit log, but cannot
     * sign in. Preferred over deletion for exactly that reason.
     */
    @Column(name = "enabled", nullable = false)
    private boolean enabled = true;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    /**
     * When this account's credentials or privileges last changed.
     *
     * <p>Tokens are stateless and last a day, so without this a password reset, a demotion or a
     * disabled account changed nothing for anyone already holding one. The authentication filter
     * rejects tokens issued before this instant, which is what actually makes the admin panel take
     * effect. Bumped by the setters below rather than by their callers, so it cannot be forgotten.
     */
    @Column(name = "credentials_updated_at", nullable = false)
    private Instant credentialsUpdatedAt;

    protected User() {
    }

    public User(String username, String email, String passwordHash, UserRole role) {
        this.username = username;
        this.email = email;
        this.passwordHash = passwordHash;
        this.role = role != null ? role : UserRole.ROLE_ENGINEER;
        this.enabled = true;
        this.createdAt = Instant.now();
        this.credentialsUpdatedAt = this.createdAt;
    }

    public UUID getId() {
        return id;
    }

    public String getUsername() {
        return username;
    }

    public String getEmail() {
        return email;
    }

    public String getPasswordHash() {
        return passwordHash;
    }

    public void setPasswordHash(String passwordHash) {
        this.passwordHash = passwordHash;
        credentialsChanged();
    }

    public UserRole getRole() {
        return role;
    }

    public void setRole(UserRole role) {
        UserRole newRole = Objects.requireNonNull(role, "Role is required.");
        if (newRole != this.role) {
            this.role = newRole;
            credentialsChanged();
        }
    }

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        if (enabled != this.enabled) {
            this.enabled = enabled;
            credentialsChanged();
        }
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getCredentialsUpdatedAt() {
        return credentialsUpdatedAt;
    }

    /**
     * Invalidates every token issued before now. Re-enabling an account bumps this too: whoever
     * held a token while it was disabled should have to log in again rather than resume silently.
     */
    private void credentialsChanged() {
        this.credentialsUpdatedAt = Instant.now();
    }
}
