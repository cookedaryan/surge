package com.power.surge.service;

import com.power.surge.domain.User;
import com.power.surge.domain.UserRole;
import com.power.surge.dto.admin.CreateUserRequest;
import com.power.surge.dto.admin.ResetPasswordRequest;
import com.power.surge.dto.admin.UpdateUserRequest;
import com.power.surge.dto.admin.UserSummaryResponse;
import com.power.surge.repository.UserRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

/**
 * Account administration for the admin panel.
 *
 * <p>Two invariants are enforced here rather than in the UI, because the UI is not the only
 * possible caller:
 *
 * <ul>
 *   <li><b>No self-lockout.</b> An administrator cannot suspend or demote their own account. Doing
 *       so would revoke their access mid-session with no way back in.</li>
 *   <li><b>Never zero administrators.</b> The last enabled administrator cannot be suspended or
 *       demoted. Recovering from that state needs direct database access, which is exactly what
 *       this panel exists to avoid.</li>
 * </ul>
 *
 * <p>Every mutation is written to the audit log against the acting administrator, not the affected
 * account, so the log answers "who did this" rather than "who did this happen to".
 */
@Service
@Transactional(readOnly = true)
public class UserAdminService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final AuditLogService auditLogService;

    public UserAdminService(
            UserRepository userRepository,
            PasswordEncoder passwordEncoder,
            AuditLogService auditLogService
    ) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.auditLogService = auditLogService;
    }

    public List<UserSummaryResponse> listUsers() {
        return userRepository.findAllByOrderByUsernameAsc().stream()
                .map(UserSummaryResponse::fromEntity)
                .toList();
    }

    @Transactional
    public UserSummaryResponse createUser(CreateUserRequest request, String actingAdmin) {
        if (userRepository.existsByUsername(request.username())) {
            throw new IllegalArgumentException("Username '" + request.username() + "' is already taken.");
        }
        if (userRepository.existsByEmail(request.email())) {
            throw new IllegalArgumentException("Email '" + request.email() + "' is already registered.");
        }

        User user = new User(
                request.username(),
                request.email(),
                passwordEncoder.encode(request.password()),
                request.role()
        );
        user = userRepository.save(user);

        auditLogService.recordAudit(actingAdmin, "USER_CREATED", "USER", user.getId().toString(),
                "Created account '" + user.getUsername() + "' with role " + user.getRole());

        return UserSummaryResponse.fromEntity(user);
    }

    @Transactional
    public UserSummaryResponse updateUser(UUID userId, UpdateUserRequest request, String actingAdmin) {
        User user = requireUser(userId);

        if (request.role() != null && request.role() != user.getRole()) {
            if (isSelf(user, actingAdmin)) {
                throw new IllegalArgumentException("You cannot change your own role.");
            }
            if (user.getRole() == UserRole.ROLE_ADMIN) {
                requireAnotherAdministratorRemains(user, "demote");
            }
            UserRole previous = user.getRole();
            user.setRole(request.role());
            auditLogService.recordAudit(actingAdmin, "USER_ROLE_CHANGED", "USER", user.getId().toString(),
                    "Role for '" + user.getUsername() + "' changed from " + previous + " to " + request.role());
        }

        if (request.enabled() != null && request.enabled() != user.isEnabled()) {
            if (isSelf(user, actingAdmin)) {
                throw new IllegalArgumentException("You cannot suspend your own account.");
            }
            if (!request.enabled() && user.getRole() == UserRole.ROLE_ADMIN) {
                requireAnotherAdministratorRemains(user, "suspend");
            }
            user.setEnabled(request.enabled());
            auditLogService.recordAudit(actingAdmin,
                    request.enabled() ? "USER_REINSTATED" : "USER_SUSPENDED",
                    "USER", user.getId().toString(),
                    (request.enabled() ? "Reinstated" : "Suspended") + " account '" + user.getUsername() + "'");
        }

        return UserSummaryResponse.fromEntity(userRepository.save(user));
    }

    @Transactional
    public void resetPassword(UUID userId, ResetPasswordRequest request, String actingAdmin) {
        User user = requireUser(userId);
        user.setPasswordHash(passwordEncoder.encode(request.newPassword()));
        userRepository.save(user);

        // The password itself is never logged, only that a reset happened and who performed it.
        auditLogService.recordAudit(actingAdmin, "USER_PASSWORD_RESET", "USER", user.getId().toString(),
                "Password reset for account '" + user.getUsername() + "'");
    }

    private User requireUser(UUID userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("No user exists with id " + userId + "."));
    }

    private boolean isSelf(User user, String actingAdmin) {
        return user.getUsername().equals(actingAdmin);
    }

    private void requireAnotherAdministratorRemains(User target, String verb) {
        long enabledAdmins = userRepository.countByRoleAndEnabledTrue(UserRole.ROLE_ADMIN);
        boolean targetCurrentlyCounts = target.isEnabled() && target.getRole() == UserRole.ROLE_ADMIN;
        if (targetCurrentlyCounts && enabledAdmins <= 1) {
            throw new IllegalArgumentException(
                    "Cannot " + verb + " the only remaining administrator. Promote another account first.");
        }
    }
}
